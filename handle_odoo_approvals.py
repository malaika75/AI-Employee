#!/usr/bin/env python3
"""
Handle Odoo invoice approvals by monitoring the Approved folder for invoice approval files
and calling the approve_operation method on the Odoo MCP server.
"""
import json
import os
import frontmatter
from pathlib import Path
import sys
import time
from datetime import datetime
import logging

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Add the current directory to the path so we can import odoo_mcp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from odoo_mcp import OdooMCP


def log_odoo_operation(operation_id, action, status, details):
    """Log the operation to vault/Logs/odoo_operations.json"""
    logs_dir = Path("vault/Logs")
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "odoo_operations.json"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user": "system",
        "action": action,
        "status": status,
        "operation_id": operation_id,
        "details": details
    }

    # Read existing logs or create new list
    if log_file.exists():
        with open(log_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = []

    # Append new log entry
    logs.append(log_entry)

    # Write back to file
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

    print(f"Operation logged to: {log_file}")


def process_approved_invoice(approval_file_path, odoo_mcp):
    """
    Process an approved invoice by calling approve_operation with the approval_id.

    Args:
        approval_file_path: Path to the approval file in the Approved folder
        odoo_mcp: OdooMCP instance to call the approve_operation method

    Returns:
        dict: Result of the approval operation
    """
    print(f"Processing approved invoice: {approval_file_path}")

    # Extract approval_id from the file metadata
    with open(approval_file_path, 'r') as f:
        post = frontmatter.load(f)
        metadata = post.metadata

    approval_id = metadata.get('approval_id')
    operation_id = metadata.get('operation_id')
    client_name = metadata.get('client_name')
    invoice_number = metadata.get('invoice_number')

    if not approval_id:
        error_msg = f"No approval_id found in {approval_file_path}"
        print(error_msg)

        log_odoo_operation(
            operation_id=f"op_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            action='process_approved_invoice',
            status='error',
            details={
                'approval_file': str(approval_file_path),
                'error': error_msg
            }
        )

        return {'status': 'error', 'error': error_msg}

    print(f"Found approval_id: {approval_id}")

    # Call the approve_operation method with the approval_id
    result = odoo_mcp.handle_request({
        "method": "approve_operation",
        "params": {
            "approval_id": approval_id
        }
    })

    print(f"Approve operation result: {result}")

    if result.get('status') == 'success':
        # Log successful approval
        log_odoo_operation(
            operation_id=operation_id or f"op_approve_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            action='approve_operation',
            status='success',
            details={
                'approval_file': str(approval_file_path),
                'approval_id': approval_id,
                'client_name': client_name,
                'invoice_number': invoice_number,
                'message': result.get('message', 'Invoice approved and posted to Odoo')
            }
        )

        # Move the file to the Archive folder after successful approval
        archive_dir = Path("vault/Archive")
        archive_dir.mkdir(exist_ok=True)

        archived_file_path = archive_dir / approval_file_path.name
        approval_file_path.rename(archived_file_path)
        print(f"Approval file moved to archive: {archived_file_path}")

        return {
            'status': 'success',
            'message': f"Invoice with approval_id {approval_id} approved successfully and posted to Odoo",
            'result': result
        }
    else:
        # Log failed approval
        log_odoo_operation(
            operation_id=operation_id or f"op_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            action='approve_operation',
            status='error',
            details={
                'approval_file': str(approval_file_path),
                'approval_id': approval_id,
                'error': result.get('error', 'Unknown error'),
                'client_name': client_name,
                'invoice_number': invoice_number
            }
        )

        # Move to Rejected folder if approval failed
        rejected_dir = Path("vault/Rejected")
        rejected_dir.mkdir(exist_ok=True)

        rejected_file_path = rejected_dir / approval_file_path.name
        approval_file_path.rename(rejected_file_path)
        print(f"Failed approval file moved to rejected: {rejected_file_path}")

        return {
            'status': 'error',
            'error': result.get('error', 'Unknown error'),
            'message': f"Failed to approve invoice with approval_id {approval_id}"
        }


class OdooApprovalWatcher(FileSystemEventHandler):
    """
    Event handler for monitoring Odoo invoice approval files in the Approved folder.
    """

    def __init__(self, odoo_mcp):
        """
        Initialize the event handler with the OdooMCP instance.

        Args:
            odoo_mcp: OdooMCP instance to call approve_operation method
        """
        self.odoo_mcp = odoo_mcp
        self.logger = logging.getLogger(__name__)

    def on_created(self, event):
        """
        Handle file creation events in the Approved folder.

        Args:
            event: The file system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if it's an Odoo invoice approval file
        if "ODOO_INVOICE_APPROVAL" in file_path.name and file_path.suffix == '.md':
            print(f"New Odoo invoice approval file detected: {file_path.name}")
            self.process_approval_file(file_path)

    def on_moved(self, event):
        """
        Handle file move events to the Approved folder.

        Args:
            event: The file system event
        """
        if event.is_directory:
            return

        # Use dest_path for moved files
        file_path = Path(event.dest_path)

        # Check if it's an Odoo invoice approval file
        if "ODOO_INVOICE_APPROVAL" in file_path.name and file_path.suffix == '.md':
            print(f"Odoo invoice approval file moved to Approved: {file_path.name}")
            self.process_approval_file(file_path)

    def process_approval_file(self, approval_file_path):
        """
        Process an Odoo invoice approval file by calling approve_operation.

        Args:
            approval_file_path: Path to the approval file in the Approved folder
        """
        print(f"Processing approval file: {approval_file_path}")

        try:
            # Extract approval_id from the file metadata
            with open(approval_file_path, 'r') as f:
                post = frontmatter.load(f)
                metadata = post.metadata

            approval_id = metadata.get('approval_id')
            operation_id = metadata.get('operation_id')
            client_name = metadata.get('client_name')
            invoice_number = metadata.get('invoice_number')

            if not approval_id:
                error_msg = f"No approval_id found in {approval_file_path}"
                print(error_msg)

                log_odoo_operation(
                    operation_id=f"op_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    action='process_approval_file',
                    status='error',
                    details={
                        'approval_file': str(approval_file_path),
                        'error': error_msg
                    }
                )
                return

            print(f"Found approval_id: {approval_id}")

            # Call the approve_operation method with the approval_id
            result = self.odoo_mcp.handle_request({
                "method": "approve_operation",
                "params": {
                    "approval_id": approval_id
                }
            })

            print(f"Approve operation result: {result}")

            if result.get('status') == 'success':
                # Log successful approval
                log_odoo_operation(
                    operation_id=operation_id or f"op_approve_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    action='approve_operation',
                    status='success',
                    details={
                        'approval_file': str(approval_file_path),
                        'approval_id': approval_id,
                        'client_name': client_name,
                        'invoice_number': invoice_number,
                        'message': result.get('message', 'Invoice approved and posted to Odoo')
                    }
                )

                # Move the file to the Archive folder after successful approval
                archive_dir = Path("vault/Archive")
                archive_dir.mkdir(exist_ok=True)

                archived_file_path = archive_dir / approval_file_path.name
                approval_file_path.rename(archived_file_path)
                print(f"Approval file moved to archive: {archived_file_path}")

                print(f"Successfully processed and approved: {approval_file_path.name}")
            else:
                # Log failed approval
                error_msg = result.get('error', 'Unknown error')
                print(f"Failed to approve invoice: {error_msg}")

                log_odoo_operation(
                    operation_id=operation_id or f"op_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    action='approve_operation',
                    status='error',
                    details={
                        'approval_file': str(approval_file_path),
                        'approval_id': approval_id,
                        'error': error_msg,
                        'client_name': client_name,
                        'invoice_number': invoice_number
                    }
                )

                # Move to Rejected folder if approval failed
                rejected_dir = Path("vault/Rejected")
                rejected_dir.mkdir(exist_ok=True)

                rejected_file_path = rejected_dir / approval_file_path.name
                approval_file_path.rename(rejected_file_path)
                print(f"Failed approval file moved to rejected: {rejected_file_path}")

        except Exception as e:
            error_msg = f"Error processing approval file {approval_file_path.name}: {str(e)}"
            print(error_msg)

            log_odoo_operation(
                operation_id=f"op_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                action='process_approval_file',
                status='error',
                details={
                    'approval_file': str(approval_file_path),
                    'error': str(e)
                }
            )


def scan_approved_folder(odoo_mcp):
    """
    Scan the Approved folder for invoice approval files and process them.

    Args:
        odoo_mcp: OdooMCP instance to call approve_operation method
    """
    approved_dir = Path("vault/Approved")

    if not approved_dir.exists():
        print(f"Approved directory does not exist: {approved_dir}")
        return

    # Look for invoice approval files in the Approved folder
    invoice_approval_files = list(approved_dir.glob("ODOO_INVOICE_APPROVAL_*.md"))

    if not invoice_approval_files:
        print("No invoice approval files found in Approved folder")
        return

    print(f"Found {len(invoice_approval_files)} invoice approval files to process")

    for approval_file in invoice_approval_files:
        print(f"Processing: {approval_file.name}")

        # Check if this is an Odoo invoice approval file by reading its metadata
        try:
            with open(approval_file, 'r') as f:
                post = frontmatter.load(f)
                metadata = post.metadata

            # Check if it's an odoo invoice approval
            if metadata.get('type') == 'odoo_invoice_approval':
                print(f"Found Odoo invoice approval file: {approval_file.name}")
                result = process_approved_invoice(approval_file, odoo_mcp)

                if result['status'] == 'success':
                    print(f"Successfully processed: {approval_file.name}")
                else:
                    print(f"Failed to process: {approval_file.name} - {result['error']}")
            else:
                print(f"File {approval_file.name} is not an Odoo invoice approval, skipping")

        except Exception as e:
            print(f"Error processing file {approval_file.name}: {str(e)}")

            # Log the error
            log_odoo_operation(
                operation_id=f"op_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                action='scan_approved_folder',
                status='error',
                details={
                    'approval_file': str(approval_file),
                    'error': str(e)
                }
            )


def main():
    """Main function to run the Odoo approval handler."""
    print("Starting Odoo invoice approval handler...")

    # Vault file path for Odoo connection
    vault_path = "odoo_vault.json"

    # Check if vault file exists
    if not os.path.exists(vault_path):
        print(f"Error: Vault file not found: {vault_path}")
        print("Please create an odoo_vault.json file with your Odoo connection details.")
        return

    # Create OdooMCP instance
    try:
        odoo_mcp = OdooMCP(vault_path=vault_path)
    except Exception as e:
        print(f"Error initializing OdooMCP: {e}")
        return

    # Test the connection to Odoo
    print("Testing connection to Odoo...")
    if not odoo_mcp.connect():
        print("Error: Could not connect to Odoo. Please check your configuration in odoo_vault.json")
        return

    print("Successfully connected to Odoo!")

    # Define the Approved folder path
    approved_dir = Path("vault/Approved")

    if not approved_dir.exists():
        print(f"Approved directory does not exist: {approved_dir}")
        print("Creating directory...")
        approved_dir.mkdir(parents=True, exist_ok=True)

    # Create event handler
    event_handler = OdooApprovalWatcher(odoo_mcp)

    # Create observer
    observer = Observer()

    # Watch the Approved directory for changes
    observer.schedule(event_handler, str(approved_dir), recursive=False)

    # Start the observer
    observer.start()
    print(f"Odoo Invoice Approval Watcher started - monitoring {approved_dir} for Odoo invoice approval files...")
    print("When an ODOO_INVOICE_APPROVAL_*.md file is added to the Approved folder, it will be processed automatically.")
    print("Press Ctrl+C to stop.")

    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Handle graceful shutdown
        print("\nStopping Odoo Invoice Approval Watcher...")
        observer.stop()

    # Wait for observer to finish
    observer.join()
    print("Odoo Invoice Approval Watcher stopped.")

    # Disconnect from Odoo
    odoo_mcp.disconnect()


def run_once():
    """Process any existing files in the Approved folder and then exit."""
    print("Processing existing Odoo invoice approvals...")

    # Vault file path for Odoo connection
    vault_path = "odoo_vault.json"

    # Check if vault file exists
    if not os.path.exists(vault_path):
        print(f"Error: Vault file not found: {vault_path}")
        print("Please create an odoo_vault.json file with your Odoo connection details.")
        return

    # Create OdooMCP instance
    try:
        odoo_mcp = OdooMCP(vault_path=vault_path)
    except Exception as e:
        print(f"Error initializing OdooMCP: {e}")
        return

    # Test the connection to Odoo
    print("Testing connection to Odoo...")
    if not odoo_mcp.connect():
        print("Error: Could not connect to Odoo. Please check your configuration in odoo_vault.json")
        return

    # Scan the Approved folder and process any invoice approval files
    scan_approved_folder(odoo_mcp)

    # Disconnect from Odoo
    odoo_mcp.disconnect()

    print("Odoo invoice approval processing completed.")


if __name__ == "__main__":
    main()