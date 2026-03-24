#!/usr/bin/env python3
"""
MCP Server for Odoo Community Integration
Provides draft-only operations for invoices, payments, and bank transaction synchronization.
All operations require human approval before posting to Odoo.
"""

import argparse
import asyncio
import json
import logging
from typing import Dict, Any, Optional
import odoorpc
from aiohttp import web, hdrs
import os
import pickle
from datetime import datetime
import frontmatter
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from urllib.parse import urlparse

# Import the new utilities
from retry_utils import retry_with_exponential_backoff
from audit_logger import audit_logger

# Import secrets manager
from secrets_manager import SecretsManager


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OdooMCP:
    def __init__(self, vault_path: str = None):
        """
        Initialize the Odoo MCP server.

        Args:
            vault_path: (Deprecated - kept for compatibility)
        """
        self.vault_path = "deprecated"  # No longer used since we use encrypted secrets
        self.odoo: Optional[odoorpc.ODOO] = None
        self.uid: Optional[int] = None
        self.approval_queue_file = "approval_queue.pkl"

        # Initialize secrets manager to get Odoo connection details
        self.secrets_manager = SecretsManager()

        # Load Odoo connection details from encrypted secrets
        try:
            odoo_url = self.secrets_manager.get_secret('odoo_url', 'http://localhost:8069')
            # Extract host and port from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(odoo_url)
            self.odoo_host = parsed_url.hostname or 'localhost'
            self.odoo_port = parsed_url.port or int(self.secrets_manager.get_secret('odoo_port', 8069))
            self.odoo_db = self.secrets_manager.get_secret('odoo_db_name', 'ai_employee_db')
            self.odoo_username = self.secrets_manager.get_secret('odoo_api_key', 'admin')  # Usually API key or username
            self.odoo_password = self.secrets_manager.get_secret('odoo_password', 'admin')  # Usually admin password or API key
        except Exception as e:
            logger.error(f"Failed to load encrypted vault data: {e}")
            raise

        # Load existing approval queue or create a new one
        self.approval_queue = self.load_approval_queue()

    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_factor=2.0,
        exceptions=(Exception,)
    )
    def connect(self):
        """Establish connection to Odoo instance"""
        audit_logger.log_action(
            action_type="odoo_connect_attempt",
            status="attempting",
            details={
                "host": self.odoo_host,
                "port": self.odoo_port,
                "database": self.odoo_db
            }
        )

        try:
            self.odoo = odoorpc.ODOO(self.odoo_host, port=self.odoo_port)
            self.uid = self.odoo.login(self.odoo_db, self.odoo_username, self.odoo_password)
            logger.info(f"Successfully connected to Odoo at {self.odoo_host}:{self.odoo_port}")

            # Log success to audit log
            audit_logger.log_success(
                action_type="odoo_connected",
                details={
                    "host": self.odoo_host,
                    "port": self.odoo_port,
                    "database": self.odoo_db,
                    "user_id": self.uid
                }
            )
            return True
        except Exception as e:
            error_msg = f"Failed to connect to Odoo: {e}"
            logger.error(error_msg)

            # Log connection failure to both error log and audit log
            self.log_error({"error": str(e), "operation": "connect", "timestamp": datetime.now().isoformat()})

            audit_logger.log_error(
                action_type="odoo_connect_failed",
                error=error_msg,
                details={
                    "host": self.odoo_host,
                    "port": self.odoo_port,
                    "database": self.odoo_db
                }
            )

            # Re-raise the exception to trigger retry
            raise e

    def log_error(self, error_details: Dict[str, Any]):
        """
        Log errors to vault/Logs/errors.json

        Args:
            error_details: Details about the error
        """
        try:
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join("vault", 'Logs')
            os.makedirs(logs_dir, exist_ok=True)

            error_log_file = os.path.join(logs_dir, 'errors.json')

            # Create error log entry
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "error_details": error_details
            }

            # Read existing error logs or create new list
            if os.path.exists(error_log_file):
                with open(error_log_file, 'r') as f:
                    errors = json.load(f)
            else:
                errors = []

            # Append new error entry
            errors.append(error_entry)

            # Write back to file
            with open(error_log_file, 'w') as f:
                json.dump(errors, f, indent=2)

            # Also log to comprehensive audit log
            operation = error_details.get('operation', 'unknown')
            error_msg = error_details.get('error', str(error_details))

            audit_logger.log_error(
                action_type=f"odoo_{operation}_failed" if operation != 'unknown' else "odoo_error",
                error=error_msg,
                details=error_details
            )

        except Exception as e:
            logger.error(f"Failed to log error: {e}")
            # Try to log the logging failure to the audit logger
            try:
                audit_logger.log_error(
                    action_type="log_failure",
                    error=f"Failed to log error: {e}",
                    details={"original_error": error_details}
                )
            except:
                pass  # If we can't log the logging failure, just continue

    def execute_with_retry(self, operation_func, *args, **kwargs):
        """
        Execute an operation with retry logic (max 3 attempts)

        Args:
            operation_func: The function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Result of the operation or an error response
        """
        max_retries = 3
        retry_count = 0

        # Log the initial attempt
        operation_name = getattr(operation_func, '__name__', str(operation_func))
        audit_logger.log_action(
            action_type=f"odoo_{operation_name}_attempt",
            status="attempting",
            details={
                "max_retries": max_retries,
                "retry_count": retry_count,
                "args": str(args)[:200],  # Truncate long arguments
                "kwargs": str(kwargs)[:200]  # Truncate long arguments
            }
        )

        while retry_count < max_retries:
            try:
                # Ensure we're connected to Odoo
                if not self.odoo or not self.uid:
                    if not self.connect():
                        # Add to error queue for later retry
                        error_details = {
                            "error": "Could not connect to Odoo",
                            "operation": operation_name,
                            "retry_count": retry_count,
                            "args": str(args)[:200],
                            "kwargs": str(kwargs)[:200]
                        }

                        # Log the error to both local and audit logs
                        self.log_error(error_details)

                        retry_count += 1
                        if retry_count >= max_retries:
                            audit_logger.log_error(
                                action_type=f"odoo_{operation_name}_failed",
                                error="Max retry attempts reached. Could not connect to Odoo.",
                                details=error_details
                            )
                            return {"error": "Max retry attempts reached. Could not connect to Odoo."}
                        continue  # Try again

                # Execute the operation
                result = operation_func(*args, **kwargs)

                # Log success if the operation succeeded
                audit_logger.log_success(
                    action_type=f"odoo_{operation_name}_success",
                    details={
                        "retry_count": retry_count,
                        "result": str(result)[:500]  # Truncate long results
                    }
                )
                return result

            except Exception as e:
                error_msg = str(e)
                retry_count += 1
                logger.warning(f"Operation {operation_name} failed (attempt {retry_count}/{max_retries}): {e}")

                if retry_count >= max_retries:
                    # Log the final failure to both local and audit logs
                    error_details = {
                        "error": error_msg,
                        "operation": operation_name,
                        "retry_count": retry_count,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                        "last_attempt": True
                    }

                    self.log_error(error_details)

                    audit_logger.log_error(
                        action_type=f"odoo_{operation_name}_failed",
                        error=f"Max retry attempts reached. Last error: {error_msg}",
                        details=error_details
                    )
                    return {"error": f"Max retry attempts reached. Last error: {error_msg}"}

                # Log the retry attempt to audit log
                audit_logger.log_retry(
                    action_type=f"odoo_{operation_name}_retry",
                    attempt=retry_count,
                    max_attempts=max_retries,
                    error=error_msg,
                    details={
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200]
                    }
                )

                # Wait before retrying (with exponential backoff)
                import time
                time.sleep(2 ** retry_count)  # 2s, 4s, 8s

                # Try to reconnect before next attempt
                self.disconnect()

        # This should not be reached, but just in case
        error_msg = "Max retry attempts reached."
        audit_logger.log_error(
            action_type=f"odoo_{operation_name}_failed",
            error=error_msg,
            details={
                "operation": operation_name,
                "max_retries": max_retries
            }
        )
        return {"error": error_msg}

    def disconnect(self):
        """Close connection to Odoo instance"""
        if self.odoo:
            try:
                self.odoo.logout()
                logger.info("Disconnected from Odoo")
                audit_logger.log_success(
                    action_type="odoo_disconnected",
                    details={"reason": "normal_disconnect"}
                )
            except Exception as e:
                # Even if logout fails, clear the connection
                error_msg = f"Error during logout: {e}"
                logger.warning(error_msg)
                audit_logger.log_error(
                    action_type="odoo_disconnect_failed",
                    error=error_msg,
                    details={"reason": "logout_error"}
                )
        else:
            audit_logger.log_action(
                action_type="odoo_disconnect_skipped",
                status="skipped",
                details={"reason": "no_connection"}
            )

        self.odoo = None
        self.uid = None

    def draft_invoice(self, partner_id: int, product_ids: list, quantities: list,
                      prices: list, description: str = "", journal_id: int = 1) -> Dict[str, Any]:
        """
        Create a draft invoice in Odoo.

        Args:
            partner_id: ID of the customer/supplier
            product_ids: List of product IDs
            quantities: List of quantities for each product
            prices: List of prices for each product
            description: Invoice description
            journal_id: Journal ID (default 1 for sales journal)

        Returns:
            Dict containing operation status and draft invoice ID
        """
        if not self.odoo or not self.uid:
            return {"error": "Not connected to Odoo"}

        if len(product_ids) != len(quantities) or len(product_ids) != len(prices):
            return {"error": "Product IDs, quantities, and prices must have the same length"}

        try:
            # Create the invoice
            invoice_vals = {
                'partner_id': partner_id,
                'move_type': 'out_invoice',  # Sales invoice
                'state': 'draft',
                'journal_id': journal_id,
                'invoice_line_ids': []
            }

            # Add invoice lines
            for i, (product_id, qty, price) in enumerate(zip(product_ids, quantities, prices)):
                line_vals = {
                    'product_id': product_id,
                    'quantity': qty,
                    'price_unit': price,
                    'name': description if i == 0 else f"Line {i+1}",
                }
                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

            # Create the invoice
            invoice_id = self.odoo.execute('account.move', 'create', invoice_vals)

            logger.info(f"Draft invoice created with ID: {invoice_id}")
            return {
                "status": "success",
                "draft_id": invoice_id,
                "message": f"Draft invoice {invoice_id} created successfully. Requires human approval before posting."
            }
        except Exception as e:
            logger.error(f"Failed to create draft invoice: {e}")
            return {"error": f"Failed to create draft invoice: {str(e)}"}

    def draft_payment(self, partner_id: int, amount: float, payment_type: str = "inbound",
                      journal_id: int = 1, partner_type: str = "customer") -> Dict[str, Any]:
        """
        Create a draft payment in Odoo.

        Args:
            partner_id: ID of the customer/supplier
            amount: Payment amount
            payment_type: 'inbound' for incoming payments, 'outbound' for outgoing payments
            journal_id: Journal ID for the payment
            partner_type: 'customer' or 'supplier'

        Returns:
            Dict containing operation status and draft payment ID
        """
        if not self.odoo or not self.uid:
            return {"error": "Not connected to Odoo"}

        try:
            # Prepare payment values
            payment_vals = {
                'partner_id': partner_id,
                'amount': amount,
                'payment_type': 'inbound' if payment_type == 'inbound' else 'outbound',
                'partner_type': partner_type,
                'journal_id': journal_id,
                'state': 'draft',  # Keep as draft
            }

            # Create the payment
            payment_id = self.odoo.execute('account.payment', 'create', payment_vals)

            logger.info(f"Draft payment created with ID: {payment_id}")
            return {
                "status": "success",
                "draft_id": payment_id,
                "message": f"Draft payment {payment_id} created successfully. Requires human approval before posting."
            }
        except Exception as e:
            logger.error(f"Failed to create draft payment: {e}")
            return {"error": f"Failed to create draft payment: {str(e)}"}

    def sync_bank_transactions(self, bank_account_id: int, transactions: list) -> Dict[str, Any]:
        """
        Sync bank transactions (draft mode) with Odoo.

        Args:
            bank_account_id: ID of the bank account in Odoo
            transactions: List of transaction dictionaries containing date, description, amount

        Returns:
            Dict containing operation status and sync results
        """
        if not self.odoo or not self.uid:
            return {"error": "Not connected to Odoo"}

        try:
            processed_count = 0
            transaction_ids = []

            for transaction in transactions:
                if 'date' not in transaction or 'description' not in transaction or 'amount' not in transaction:
                    logger.warning(f"Skipping invalid transaction: {transaction}")
                    continue

                # Create bank statement line (in draft mode)
                statement_line_vals = {
                    'date': transaction['date'],
                    'name': transaction['description'],
                    'amount': transaction['amount'],
                    'partner_id': transaction.get('partner_id', False),  # Optional partner ID
                    'account_id': bank_account_id,
                }

                # Create the transaction record
                line_id = self.odoo.execute('account.bank.statement.line', 'create', statement_line_vals)
                transaction_ids.append(line_id)
                processed_count += 1

            logger.info(f"Synced {processed_count} bank transactions")
            return {
                "status": "success",
                "transaction_count": processed_count,
                "transaction_ids": transaction_ids,
                "message": f"{processed_count} bank transactions synced in draft mode. Requires human approval before posting."
            }
        except Exception as e:
            logger.error(f"Failed to sync bank transactions: {e}")
            return {"error": f"Failed to sync bank transactions: {str(e)}"}

    def load_approval_queue(self) -> Dict:
        """Load the approval queue from file, or create a new one if it doesn't exist"""
        if os.path.exists(self.approval_queue_file):
            try:
                with open(self.approval_queue_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Could not load approval queue: {e}. Creating new queue.")
                return {}
        return {}

    def save_approval_queue(self):
        """Save the approval queue to file"""
        try:
            with open(self.approval_queue_file, 'wb') as f:
                pickle.dump(self.approval_queue, f)
        except Exception as e:
            logger.error(f"Could not save approval queue: {e}")

    def queue_for_approval(self, operation_type: str, draft_id: int, details: Dict[str, Any]) -> str:
        """
        Queue a draft operation for human approval.

        Args:
            operation_type: Type of operation ('invoice', 'payment', 'bank_transaction')
            draft_id: ID of the draft in Odoo
            details: Additional details about the operation

        Returns:
            approval_id: Unique ID for the approval request
        """
        approval_id = f"{operation_type}_{draft_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        operation_id = f"op_{operation_type}_{draft_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        self.approval_queue[approval_id] = {
            'operation_type': operation_type,
            'draft_id': draft_id,
            'details': details,
            'status': 'pending',
            'created_at': datetime.now(),
            'approved_at': None,
            'operation_id': operation_id
        }

        self.save_approval_queue()

        # Log the operation to vault/Logs/odoo_operations.json
        self.log_operation(
            operation_id=operation_id,
            user="system",
            action="queue_for_approval",
            status="pending",
            details={
                "approval_id": approval_id,
                "draft_id": draft_id,
                "operation_type": operation_type,
                "message": f"Operation {operation_id} queued for approval"
            }
        )

        logger.info(f"Queued {operation_type} {draft_id} for approval with ID: {approval_id}, Operation ID: {operation_id}")
        return approval_id

    def log_operation(self, operation_id: str, user: str, action: str, status: str, details: Dict[str, Any]):
        """
        Log an operation to vault/Logs/odoo_operations.json

        Args:
            operation_id: Unique operation identifier
            user: User performing the action
            action: Action being performed
            status: Status of the operation
            details: Additional details about the operation
        """
        try:
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join("vault", 'Logs')
            os.makedirs(logs_dir, exist_ok=True)

            log_file = os.path.join(logs_dir, 'odoo_operations.json')

            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user": user,
                "action": action,
                "status": status,
                "operation_id": operation_id,
                "details": details
            }

            # Read existing logs or create new list
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []

            # Append new log entry
            logs.append(log_entry)

            # Write back to file
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)

            # Also log to comprehensive audit log
            audit_logger.log_action(
                action_type=f"odoo_{action}",
                status=status,
                details={
                    "operation_id": operation_id,
                    "user": user,
                    "action": action,
                    "status": status,
                    **details
                },
                user_id=user
            )

        except Exception as e:
            logger.error(f"Failed to log operation {operation_id}: {e}")
            # Try to log the logging failure to the audit logger
            try:
                audit_logger.log_error(
                    action_type="log_failure",
                    error=f"Failed to log operation: {e}",
                    details={
                        "operation_id": operation_id,
                        "user": user,
                        "action": action,
                        "status": status,
                        "original_details": details
                    }
                )
            except:
                pass  # If we can't log the logging failure, just continue

    def approve_operation(self, approval_id: str) -> Dict[str, Any]:
        """
        Approve a queued operation and post it to Odoo.

        Args:
            approval_id: ID of the approval request

        Returns:
            Dict containing operation status
        """
        if approval_id not in self.approval_queue:
            return {"error": f"Approval ID {approval_id} not found"}

        approval_request = self.approval_queue[approval_id]
        operation_id = approval_request.get('operation_id', approval_id)

        if approval_request['status'] == 'approved':
            # Log the operation attempt
            self.log_operation(
                operation_id=operation_id,
                user="system",
                action="approve_operation",
                status="error",
                details={
                    "approval_id": approval_id,
                    "message": f"Operation {approval_id} already approved"
                }
            )
            return {"error": f"Operation {approval_id} already approved"}

        try:
            if approval_request['operation_type'] == 'invoice':
                # Confirm the invoice (change state from draft to posted)
                self.odoo.execute('account.move', 'action_post', [approval_request['draft_id']])
            elif approval_request['operation_type'] == 'payment':
                # Confirm the payment (change state from draft to posted)
                self.odoo.execute('account.payment', 'action_post', [approval_request['draft_id']])
            elif approval_request['operation_type'] == 'bank_transaction':
                # For bank transactions, we might need to confirm the statement
                # This is a placeholder - actual implementation depends on Odoo configuration
                logger.info(f"Bank transaction {approval_request['draft_id']} marked as approved")
            else:
                return {"error": f"Unknown operation type: {approval_request['operation_type']}"}

            # Update the approval status
            approval_request['status'] = 'approved'
            approval_request['approved_at'] = datetime.now()
            self.save_approval_queue()

            logger.info(f"Operation {approval_id} approved and posted to Odoo")

            # Log the successful approval
            self.log_operation(
                operation_id=operation_id,
                user="system",
                action="approve_operation",
                status="success",
                details={
                    "approval_id": approval_id,
                    "draft_id": approval_request['draft_id'],
                    "message": f"Operation {approval_id} approved and posted to Odoo"
                }
            )

            return {
                "status": "success",
                "message": f"Operation {approval_id} approved and posted to Odoo",
                "draft_id": approval_request['draft_id'],
                "operation_id": operation_id
            }
        except Exception as e:
            logger.error(f"Failed to approve operation {approval_id}: {e}")
            # Log the failed approval
            self.log_operation(
                operation_id=operation_id,
                user="system",
                action="approve_operation",
                status="error",
                details={
                    "approval_id": approval_id,
                    "error": str(e),
                    "message": f"Failed to approve operation {approval_id}: {str(e)}"
                }
            )
            return {"error": f"Failed to approve operation: {str(e)}"}

    def get_draft_status(self, operation_id: str) -> Dict[str, Any]:
        """
        Check if a draft operation was posted after approval.

        Args:
            operation_id: The unique operation ID to check

        Returns:
            Dict containing operation status and details
        """
        try:
            # Check if operation exists in approval queue
            for approval_id, approval_data in self.approval_queue.items():
                if operation_id in approval_id or approval_data.get('operation_id') == operation_id:
                    # Connect to Odoo to check the current status of the draft
                    if not self.odoo or not self.uid:
                        if not self.connect():
                            return {"error": "Could not connect to Odoo"}

                    # Determine the model based on operation type
                    model = None
                    draft_id = approval_data['draft_id']

                    if approval_data['operation_type'] == 'invoice':
                        model = 'account.move'
                    elif approval_data['operation_type'] == 'payment':
                        model = 'account.payment'
                    elif approval_data['operation_type'] == 'bank_transaction':
                        model = 'account.bank.statement.line'

                    if model:
                        try:
                            # Check the current state of the record in Odoo
                            record = self.odoo.execute(model, 'read', [draft_id], ['state', 'name'])
                            if record:
                                current_state = record[0].get('state', 'unknown')
                                record_name = record[0].get('name', f"Unknown {approval_data['operation_type']}")

                                return {
                                    "status": "success",
                                    "operation_id": operation_id,
                                    "approval_id": approval_id,
                                    "draft_id": draft_id,
                                    "current_state": current_state,
                                    "operation_type": approval_data['operation_type'],
                                    "message": f"Operation {operation_id} current state: {current_state}",
                                    "record_name": record_name
                                }
                        except Exception as e:
                            logger.warning(f"Could not read record {draft_id} from Odoo: {e}")

                    return {
                        "status": "success",
                        "operation_id": operation_id,
                        "approval_id": approval_id,
                        "draft_id": draft_id,
                        "current_state": approval_data['status'],
                        "operation_type": approval_data['operation_type'],
                        "message": f"Operation {operation_id} status: {approval_data['status']}",
                        "record_name": f"Unknown {approval_data['operation_type']}"
                    }

            return {"error": f"Operation ID {operation_id} not found"}
        except Exception as e:
            logger.error(f"Failed to get draft status for {operation_id}: {e}")
            return {"error": f"Failed to get draft status: {str(e)}"}

    def reject_operation(self, operation_id: str) -> Dict[str, Any]:
        """
        Cancel a draft operation if rejected.

        Args:
            operation_id: The unique operation ID to reject

        Returns:
            Dict containing operation status
        """
        try:
            # Find the operation in the approval queue
            for approval_id, approval_data in self.approval_queue.items():
                if operation_id in approval_id or approval_data.get('operation_id') == operation_id:
                    # If the operation has not been approved yet, we'll just mark it as rejected
                    if approval_data['status'] == 'pending':
                        approval_data['status'] = 'rejected'
                        approval_data['rejected_at'] = datetime.now()
                        self.save_approval_queue()

                        # Log the operation
                        self.log_operation(
                            operation_id=operation_id,
                            user="system",
                            action="reject_operation",
                            status="success",
                            details={
                                "approval_id": approval_id,
                                "draft_id": approval_data['draft_id'],
                                "operation_type": approval_data['operation_type'],
                                "message": f"Operation {operation_id} rejected before approval"
                            }
                        )

                        return {
                            "status": "success",
                            "message": f"Operation {operation_id} rejected and will not be posted",
                            "operation_id": operation_id
                        }
                    elif approval_data['status'] == 'approved':
                        # If already approved, we may need to cancel the actual record in Odoo
                        if not self.odoo or not self.uid:
                            if not self.connect():
                                return {"error": "Could not connect to Odoo"}

                        draft_id = approval_data['draft_id']
                        model = None

                        if approval_data['operation_type'] == 'invoice':
                            model = 'account.move'
                        elif approval_data['operation_type'] == 'payment':
                            model = 'account.payment'
                        elif approval_data['operation_type'] == 'bank_transaction':
                            model = 'account.bank.statement.line'

                        if model:
                            try:
                                # If the record exists and is posted, we may need to reverse/cancel it
                                record = self.odoo.execute(model, 'read', [draft_id], ['state'])
                                if record and record[0].get('state') in ['posted', 'posted_with_commit']:
                                    # For invoices, we might need to reverse them
                                    if approval_data['operation_type'] == 'invoice':
                                        # This is a simplified approach - real cancellation may be more complex
                                        self.odoo.execute(model, 'button_draft', [draft_id])  # Change back to draft
                                        # In real implementation, you might want to reverse the journal entry
                                    logger.info(f"Operation {operation_id} record {draft_id} has been reset to draft")

                                # Update status in queue
                                approval_data['status'] = 'rejected_after_approval'
                                approval_data['rejected_at'] = datetime.now()
                                self.save_approval_queue()

                                # Log the operation
                                self.log_operation(
                                    operation_id=operation_id,
                                    user="system",
                                    action="reject_operation",
                                    status="success",
                                    details={
                                        "approval_id": approval_id,
                                        "draft_id": draft_id,
                                        "operation_type": approval_data['operation_type'],
                                        "message": f"Operation {operation_id} rejected after approval and reset to draft"
                                    }
                                )

                                return {
                                    "status": "success",
                                    "message": f"Operation {operation_id} rejected and reset to draft",
                                    "operation_id": operation_id
                                }
                            except Exception as e:
                                logger.error(f"Failed to reject approved operation {operation_id}: {e}")
                                return {"error": f"Failed to reject approved operation: {str(e)}"}
                        else:
                            return {"error": f"Unknown operation type: {approval_data['operation_type']}"}
                    else:
                        return {
                            "error": f"Operation {operation_id} already has status: {approval_data['status']}",
                            "status": approval_data['status']
                        }

            return {"error": f"Operation ID {operation_id} not found"}
        except Exception as e:
            logger.error(f"Failed to reject operation {operation_id}: {e}")
            return {"error": f"Failed to reject operation: {str(e)}"}

    def get_approval_queue_status(self) -> Dict[str, Any]:
        """
        Get the status of all pending approvals.

        Returns:
            Dict containing approval queue status
        """
        pending_approvals = {
            k: v for k, v in self.approval_queue.items()
            if v['status'] == 'pending'
        }

        return {
            "total_pending": len(pending_approvals),
            "approvals": pending_approvals
        }

    def process_approval_file(self, approval_file_path: str):
        """
        Process an approval file from the Approved folder.
        Simplified flow: extract draft_id and directly post to Odoo.

        Args:
            approval_file_path: Path to the approval file
        """
        try:
            # Read the approval file
            with open(approval_file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                metadata = post.metadata

            # Only require draft_id now, not approval_id
            draft_id = metadata.get('draft_id')
            client_name = metadata.get('client_name', 'Unknown')
            invoice_number = metadata.get('invoice_number', 'Unknown')
            amount = metadata.get('amount', 0.0)
            description = metadata.get('description', 'No description')

            # Use draft_id from the file to directly post to Odoo
            if not draft_id:
                logger.error(f"No draft_id found in {approval_file_path}")
                # Move to Rejected folder if draft_id not found
                rejected_path = Path("vault/Rejected") / Path(approval_file_path).name
                Path(approval_file_path).rename(rejected_path)
                logger.error(f"File without draft_id moved to Rejected: {rejected_path}")
                return

            logger.info(f"Processing approval file with draft_id: {draft_id}")

            # Connect to Odoo if not already connected
            if not self.odoo or not self.uid:
                if not self.connect():
                    logger.error("Could not connect to Odoo")
                    # Move to Rejected folder if connection fails
                    rejected_path = Path("vault/Rejected") / Path(approval_file_path).name
                    Path(approval_file_path).rename(rejected_path)
                    logger.error(f"Connection failed file moved to Rejected: {rejected_path}")
                    return

            # Directly post the invoice to Odoo by changing its state from draft to posted
            try:
                # Update the invoice state to 'posted'
                self.odoo.execute('account.move', 'write', draft_id, {'state': 'posted'})

                logger.info(f"Invoice {draft_id} successfully posted to Odoo")

                # Log the operation
                operation_id = f"post_invoice_{draft_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.log_operation(
                    operation_id=operation_id,
                    user="system",
                    action="invoice_posted",
                    status="success",
                    details={
                        "draft_id": draft_id,
                        "client_name": client_name,
                        "amount": amount,
                        "message": f"Invoice {draft_id} successfully posted to Odoo"
                    }
                )

                # Update Dashboard.md
                dashboard_path = Path("vault/Dashboard.md")
                if dashboard_path.exists():
                    with open(dashboard_path, 'r', encoding='utf-8') as f:
                        dashboard_content = f.read()

                    # Update with the success message
                    success_msg = f"Odoo invoice {draft_id} posted successfully for amount {amount}"
                    updated_content = dashboard_content + f"\n- {success_msg} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

                    with open(dashboard_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)

                # Move the file to Done folder
                done_path = Path("vault/Done") / Path(approval_file_path).name
                Path(approval_file_path).rename(done_path)
                logger.info(f"Approval file moved to Done: {done_path}")

            except Exception as e:
                logger.error(f"Failed to post invoice {draft_id} to Odoo: {e}")

                # Log the failure
                self.log_operation(
                    operation_id=f"post_invoice_error_{draft_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    user="system",
                    action="invoice_posted",
                    status="error",
                    details={
                        "draft_id": draft_id,
                        "client_name": client_name,
                        "amount": amount,
                        "error": str(e),
                        "message": f"Failed to post invoice {draft_id} to Odoo"
                    }
                )

                # Move to Rejected folder if posting fails
                rejected_path = Path("vault/Rejected") / Path(approval_file_path).name
                Path(approval_file_path).rename(rejected_path)
                logger.error(f"Failed invoice posting file moved to Rejected: {rejected_path}")

        except Exception as e:
            logger.error(f"Error processing approval file {approval_file_path}: {e}")
            # Move to Rejected folder if processing fails
            try:
                rejected_path = Path("vault/Rejected") / Path(approval_file_path).name
                Path(approval_file_path).rename(rejected_path)
                logger.error(f"Error processing file moved to Rejected: {rejected_path}")
            except:
                logger.error(f"Could not move {approval_file_path} to Rejected folder")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming MCP requests.

        Args:
            request: Dictionary containing the request method and parameters

        Returns:
            Dictionary with response
        """
        method = request.get('method')
        params = request.get('params', {})

        # Connect to Odoo if not already connected
        if not self.odoo or not self.uid:
            if not self.connect():
                return {"error": "Could not connect to Odoo"}

        logger.info(f"Processing request: {method}")

        if method == 'draft_invoice':
            result = self.draft_invoice(
                partner_id=params.get('partner_id'),
                product_ids=params.get('product_ids', []),
                quantities=params.get('quantities', []),
                prices=params.get('prices', []),
                description=params.get('description', ''),
                journal_id=params.get('journal_id', 1)
            )

            if result.get('status') == 'success':
                # Queue the invoice for approval
                approval_id = self.queue_for_approval(
                    'invoice',
                    result['draft_id'],
                    {
                        'partner_id': params.get('partner_id'),
                        'amount': sum(q * p for q, p in zip(params.get('quantities', []), params.get('prices', []))),
                        'description': params.get('description', '')
                    }
                )

                # Get the operation_id from the approval queue
                operation_id = self.approval_queue[approval_id].get('operation_id', approval_id)

                result['approval_id'] = approval_id
                result['operation_id'] = operation_id
                result['message'] += f" Approval ID: {approval_id}. Operation ID: {operation_id}."

                # Log the operation
                self.log_operation(
                    operation_id=operation_id,
                    user="system",
                    action="draft_invoice",
                    status="success",
                    details={
                        "approval_id": approval_id,
                        "draft_id": result['draft_id'],
                        "message": "Draft invoice created and queued for approval"
                    }
                )

            return result
        elif method == 'draft_payment':
            result = self.draft_payment(
                partner_id=params.get('partner_id'),
                amount=params.get('amount', 0.0),
                payment_type=params.get('payment_type', 'inbound'),
                journal_id=params.get('journal_id', 1),
                partner_type=params.get('partner_type', 'customer')
            )

            if result.get('status') == 'success':
                # Queue the payment for approval
                approval_id = self.queue_for_approval(
                    'payment',
                    result['draft_id'],
                    {
                        'partner_id': params.get('partner_id'),
                        'amount': params.get('amount', 0.0),
                        'payment_type': params.get('payment_type', 'inbound')
                    }
                )

                # Get the operation_id from the approval queue
                operation_id = self.approval_queue[approval_id].get('operation_id', approval_id)

                result['approval_id'] = approval_id
                result['operation_id'] = operation_id
                result['message'] += f" Approval ID: {approval_id}. Operation ID: {operation_id}."

                # Log the operation
                self.log_operation(
                    operation_id=operation_id,
                    user="system",
                    action="draft_payment",
                    status="success",
                    details={
                        "approval_id": approval_id,
                        "draft_id": result['draft_id'],
                        "message": "Draft payment created and queued for approval"
                    }
                )

            return result
        elif method == 'sync_bank_transactions':
            result = self.sync_bank_transactions(
                bank_account_id=params.get('bank_account_id'),
                transactions=params.get('transactions', [])
            )

            if result.get('status') == 'success':
                # Queue the bank transactions for approval
                approval_id = self.queue_for_approval(
                    'bank_transaction',
                    result.get('transaction_ids', []),
                    {
                        'bank_account_id': params.get('bank_account_id'),
                        'transaction_count': result.get('transaction_count', 0)
                    }
                )

                # Get the operation_id from the approval queue
                operation_id = self.approval_queue[approval_id].get('operation_id', approval_id)

                result['approval_id'] = approval_id
                result['operation_id'] = operation_id
                result['message'] += f" Approval ID: {approval_id}. Operation ID: {operation_id}."

                # Log the operation
                self.log_operation(
                    operation_id=operation_id,
                    user="system",
                    action="sync_bank_transactions",
                    status="success",
                    details={
                        "approval_id": approval_id,
                        "transaction_ids": result.get('transaction_ids'),
                        "message": "Bank transactions synced and queued for approval"
                    }
                )

            return result
        elif method == 'approve_operation':
            return self.approve_operation(approval_id=params.get('approval_id', ''))
        elif method == 'get_approval_queue_status':
            return self.get_approval_queue_status()
        elif method == 'get_draft_status':
            return self.get_draft_status(operation_id=params.get('operation_id', ''))
        elif method == 'reject_operation':
            return self.reject_operation(operation_id=params.get('operation_id', ''))
        else:
            error_msg = f"Unknown method: {method}"
            logger.error(error_msg)
            return {"error": error_msg}


class ApprovalWatcher(FileSystemEventHandler):
    """
    Watcher for the Approved folder to process approval files automatically.
    """
    def __init__(self, odoo_mcp_instance):
        self.odoo_mcp = odoo_mcp_instance

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        if Path(file_path).suffix == '.md':
            logger.info(f"New approval file detected: {Path(file_path).name}")
            time.sleep(1)  # Small delay to ensure file is fully written
            self.odoo_mcp.process_approval_file(file_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        # For files moved into the Approved directory
        dest_path = event.dest_path
        if Path(dest_path).suffix == '.md':
            logger.info(f"Approval file moved to Approved: {Path(dest_path).name}")
            time.sleep(1)  # Small delay to ensure file is fully written
            self.odoo_mcp.process_approval_file(dest_path)


class ApprovalWatcher(FileSystemEventHandler):
    """
    Watcher for the Approved folder to process approval files automatically.
    """
    def __init__(self, odoo_mcp_instance):
        self.odoo_mcp = odoo_mcp_instance

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        if Path(file_path).suffix == '.md':
            logger.info(f"New approval file detected: {Path(file_path).name}")
            time.sleep(1)  # Small delay to ensure file is fully written
            self.odoo_mcp.process_approval_file(file_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        # For files moved into the Approved directory
        dest_path = event.dest_path
        if Path(dest_path).suffix == '.md':
            logger.info(f"Approval file moved to Approved: {Path(dest_path).name}")
            time.sleep(1)  # Small delay to ensure file is fully written
            self.odoo_mcp.process_approval_file(dest_path)


def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle incoming MCP requests.

    Args:
        request: Dictionary containing the request method and parameters

    Returns:
        Dictionary with response
    """
    method = request.get('method')
    params = request.get('params', {})

    # Connect to Odoo if not already connected
    if not self.odoo or not self.uid:
        if not self.connect():
            return {"error": "Could not connect to Odoo"}

    logger.info(f"Processing request: {method}")

    if method == 'draft_invoice':
        result = self.draft_invoice(
            partner_id=params.get('partner_id'),
            product_ids=params.get('product_ids', []),
            quantities=params.get('quantities', []),
            prices=params.get('prices', []),
            description=params.get('description', ''),
            journal_id=params.get('journal_id', 1)
        )

        if result.get('status') == 'success':
            # Queue the invoice for approval
            approval_id = self.queue_for_approval(
                'invoice',
                result['draft_id'],
                {
                    'partner_id': params.get('partner_id'),
                    'amount': sum(q * p for q, p in zip(params.get('quantities', []), params.get('prices', []))),
                    'description': params.get('description', '')
                }
            )

            # Get the operation_id from the approval queue
            operation_id = self.approval_queue[approval_id].get('operation_id', approval_id)

            result['approval_id'] = approval_id
            result['operation_id'] = operation_id
            result['message'] += f" Approval ID: {approval_id}. Operation ID: {operation_id}."

            # Log the operation
            self.log_operation(
                operation_id=operation_id,
                user="system",
                action="draft_invoice",
                status="success",
                details={
                    "approval_id": approval_id,
                    "draft_id": result['draft_id'],
                    "message": "Draft invoice created and queued for approval"
                }
            )

        return result
    elif method == 'draft_payment':
        result = self.draft_payment(
            partner_id=params.get('partner_id'),
            amount=params.get('amount', 0.0),
            payment_type=params.get('payment_type', 'inbound'),
            journal_id=params.get('journal_id', 1),
            partner_type=params.get('partner_type', 'customer')
        )

        if result.get('status') == 'success':
            # Queue the payment for approval
            approval_id = self.queue_for_approval(
                'payment',
                result['draft_id'],
                {
                    'partner_id': params.get('partner_id'),
                    'amount': params.get('amount', 0.0),
                    'payment_type': params.get('payment_type', 'inbound')
                }
            )

            # Get the operation_id from the approval queue
            operation_id = self.approval_queue[approval_id].get('operation_id', approval_id)

            result['approval_id'] = approval_id
            result['operation_id'] = operation_id
            result['message'] += f" Approval ID: {approval_id}. Operation ID: {operation_id}."

            # Log the operation
            self.log_operation(
                operation_id=operation_id,
                user="system",
                action="draft_payment",
                status="success",
                details={
                    "approval_id": approval_id,
                    "draft_id": result['draft_id'],
                    "message": "Draft payment created and queued for approval"
                }
            )

        return result
    elif method == 'sync_bank_transactions':
        result = self.sync_bank_transactions(
            bank_account_id=params.get('bank_account_id'),
            transactions=params.get('transactions', [])
        )

        if result.get('status') == 'success':
            # Queue the bank transactions for approval
            approval_id = self.queue_for_approval(
                'bank_transaction',
                result.get('transaction_ids', []),
                {
                    'bank_account_id': params.get('bank_account_id'),
                    'transaction_count': result.get('transaction_count', 0)
                }
            )

            # Get the operation_id from the approval queue
            operation_id = self.approval_queue[approval_id].get('operation_id', approval_id)

            result['approval_id'] = approval_id
            result['operation_id'] = operation_id
            result['message'] += f" Approval ID: {approval_id}. Operation ID: {operation_id}."

            # Log the operation
            self.log_operation(
                operation_id=operation_id,
                user="system",
                action="sync_bank_transactions",
                status="success",
                details={
                    "approval_id": approval_id,
                    "transaction_ids": result.get('transaction_ids'),
                    "message": "Bank transactions synced and queued for approval"
                }
            )

        return result
    elif method == 'approve_operation':
        return self.approve_operation(approval_id=params.get('approval_id', ''))
    elif method == 'get_approval_queue_status':
        return self.get_approval_queue_status()
    elif method == 'get_draft_status':
        return self.get_draft_status(operation_id=params.get('operation_id', ''))
    elif method == 'reject_operation':
        return self.reject_operation(operation_id=params.get('operation_id', ''))
    else:
        error_msg = f"Unknown method: {method}"
        logger.error(error_msg)
        return {"error": error_msg}


# Global OdooMCP instance
odoo_mcp_instance = None


async def handle_post_request(request):
    """Handle POST requests to the MCP endpoint"""
    try:
        # Parse the incoming JSON data
        data = await request.json()

        # Process the request
        result = odoo_mcp_instance.handle_request(data)

        # Return the result
        return web.json_response(result)
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON in request"}, status=400)
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return web.json_response({"error": f"Error processing request: {str(e)}"}, status=500)


async def handle_get_capabilities(request):
    """Return the server capabilities"""
    capabilities = {
        "name": "Odoo MCP Server",
        "version": "1.0.0",
        "description": "Draft-only operations for Odoo ERP including invoices, payments, and bank transactions. All operations require human approval before posting.",
        "capabilities": [
            {
                "name": "draft_invoice",
                "description": "Create a draft invoice in Odoo. All invoices created are draft-only and require human approval before posting. Returns a unique operation_id for tracking.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "partner_id": {"type": "integer", "description": "Customer/supplier ID"},
                        "product_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of product IDs"},
                        "quantities": {"type": "array", "items": {"type": "number"}, "description": "List of quantities"},
                        "prices": {"type": "array", "items": {"type": "number"}, "description": "List of prices"},
                        "description": {"type": "string", "description": "Invoice description"},
                        "journal_id": {"type": "integer", "description": "Journal ID (default 1)"}
                    },
                    "required": ["partner_id", "product_ids", "quantities", "prices"]
                }
            },
            {
                "name": "draft_payment",
                "description": "Create a draft payment in Odoo. All payments created are draft-only and require human approval before posting. Returns a unique operation_id for tracking.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "partner_id": {"type": "integer", "description": "Customer/supplier ID"},
                        "amount": {"type": "number", "description": "Payment amount"},
                        "payment_type": {"type": "string", "enum": ["inbound", "outbound"], "description": "Payment type"},
                        "journal_id": {"type": "integer", "description": "Journal ID (default 1)"},
                        "partner_type": {"type": "string", "enum": ["customer", "supplier"], "description": "Partner type"}
                    },
                    "required": ["partner_id", "amount"]
                }
            },
            {
                "name": "sync_bank_transactions",
                "description": "Sync bank transactions in draft mode with Odoo. All transactions are draft-only and require human approval before posting. Returns a unique operation_id for tracking.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "bank_account_id": {"type": "integer", "description": "Bank account ID in Odoo"},
                        "transactions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string", "format": "date", "description": "Transaction date"},
                                    "description": {"type": "string", "description": "Transaction description"},
                                    "amount": {"type": "number", "description": "Transaction amount"},
                                    "partner_id": {"type": "integer", "description": "Optional partner ID"}
                                },
                                "required": ["date", "description", "amount"]
                            },
                            "description": "List of transactions to sync"
                        }
                    },
                    "required": ["bank_account_id", "transactions"]
                }
            },
            {
                "name": "approve_operation",
                "description": "Approve a draft operation and post it to Odoo. This is part of the human-in-the-loop approval process.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "approval_id": {"type": "string", "description": "The unique ID of the approval request"}
                    },
                    "required": ["approval_id"]
                }
            },
            {
                "name": "get_approval_queue_status",
                "description": "Get the status of all pending approval requests in the queue.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_draft_status",
                "description": "Check if a draft operation was posted after approval. Requires the operation_id.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "operation_id": {"type": "string", "description": "The unique operation ID to check"}
                    },
                    "required": ["operation_id"]
                }
            },
            {
                "name": "reject_operation",
                "description": "Cancel a draft operation if rejected. Can cancel operations before or after approval.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "operation_id": {"type": "string", "description": "The unique operation ID to reject"}
                    },
                    "required": ["operation_id"]
                }
            }
        ]
    }
    return web.json_response(capabilities)


def create_app():
    """Create the aiohttp web application"""
    app = web.Application()

    # Add routes
    app.router.add_get('/', handle_get_capabilities)
    app.router.add_post('/', handle_post_request)

    return app


def main():
    parser = argparse.ArgumentParser(description='MCP Server for Odoo Integration')
    parser.add_argument('--vault-path', default=None, help='DEPRECATED - Path to the vault file containing Odoo credentials (not used anymore, using encrypted secrets)')
    parser.add_argument('--host', default='localhost', help='Host to bind the MCP server')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind the MCP server')

    args = parser.parse_args()

    global odoo_mcp_instance
    odoo_mcp_instance = OdooMCP()  # No longer need vault_path since we use encrypted secrets

    # Try connecting to Odoo to verify configuration
    if not odoo_mcp_instance.connect():
        logger.error("Failed to connect to Odoo. Please check your configuration.")
        exit(1)

    logger.info(f"Successfully connected to Odoo. Starting MCP server on {args.host}:{args.port}")

    # Set up the approval folder watcher
    approved_dir = Path("vault/Approved")
    approved_dir.mkdir(exist_ok=True)

    event_handler = ApprovalWatcher(odoo_mcp_instance)
    observer = Observer()
    observer.schedule(event_handler, str(approved_dir), recursive=False)
    observer.start()

    # Process any existing files in the Approved folder
    for approval_file in approved_dir.glob("*.md"):
        logger.info(f"Processing existing approval file: {approval_file.name}")
        odoo_mcp_instance.process_approval_file(str(approval_file))

    # Create and run the web application
    app = create_app()

    try:
        web.run_app(app, host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Shutting down MCP server...")
    finally:
        observer.stop()
        observer.join()
        odoo_mcp_instance.disconnect()


if __name__ == "__main__":
    main()