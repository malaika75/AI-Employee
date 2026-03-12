#!/usr/bin/env python3
"""
Process pending invoice files and create draft invoices in Odoo with approval workflow.
"""
import json
import os
import frontmatter
from datetime import datetime
from pathlib import Path
import sys

# Add the current directory to the path so we can import odoo_mcp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from odoo_mcp import OdooMCP


def read_invoice_file(file_path):
    """Read the invoice markdown file and extract metadata."""
    with open(file_path, 'r') as f:
        post = frontmatter.load(f)
        return post.metadata


def create_approval_file(approval_id, operation_id, invoice_data, odoo_response):
    """Create an approval file in the Pending_Approval directory."""
    approval_dir = Path("vault/Pending_Approval")
    approval_dir.mkdir(exist_ok=True)

    # Create the fresh approval file with fixed name
    approval_filename = "ODOO_INVOICE_FRESH.md"
    approval_path = approval_dir / approval_filename

    approval_content = f"""---
type: odoo_invoice_approval
original_file: pending_invoice_fresh.md
status: pending_approval
priority: high
approval_id: {approval_id}
operation_id: {operation_id}
invoice_number: {invoice_data.get('invoice_number', 'N/A')}
client_name: {invoice_data.get('client_name', 'N/A')}
amount: {invoice_data.get('amount', 'N/A')}
due_date: {invoice_data.get('due_date', 'N/A')}
description: {invoice_data.get('description', 'N/A')}
---
# Fresh Odoo Invoice Approval Request

## Invoice Details

- **Invoice Number**: {invoice_data.get('invoice_number', 'N/A')}
- **Client**: {invoice_data.get('client_name', 'N/A')}
- **Amount**: ${invoice_data.get('amount', 'N/A')}
- **Due Date**: {invoice_data.get('due_date', 'N/A')}
- **Description**: {invoice_data.get('description', 'N/A')}
- **Draft ID**: {odoo_response.get('draft_id', 'N/A')}
- **Operation ID**: {operation_id}
- **Approval ID**: {approval_id}

## Action Required

A fresh invoice has been created in draft mode in Odoo and requires human approval before posting. Please review the details and approve or reject the invoice.

## Approval Options

- [ ] Approve and post invoice to Odoo
- [ ] Reject invoice
- [ ] Review details before approving
"""

    with open(approval_path, 'w') as f:
        f.write(approval_content)

    print(f"Fresh approval file created: {approval_path}")
    return approval_path


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


def process_pending_invoice(invoice_file_path, odoo_mcp):
    """Process a pending invoice file by creating a draft in Odoo and generating approval workflow."""
    print(f"Processing invoice file: {invoice_file_path}")

    # Read the invoice file
    invoice_data = read_invoice_file(invoice_file_path)
    print(f"Invoice data: {invoice_data}")

    # Ensure connection is active before proceeding
    if not odoo_mcp.odoo or not odoo_mcp.uid:
        print("Reconnecting to Odoo...")
        if not odoo_mcp.connect():
            return {
                'status': 'error',
                'error': 'Could not connect to Odoo',
                'message': 'Failed to connect to Odoo'
            }

    # Ensure connection is still active before creating draft invoice
    if not odoo_mcp.odoo or not odoo_mcp.uid:
        if not odoo_mcp.connect():
            return {
                'status': 'error',
                'error': 'Could not connect to Odoo',
                'message': 'Failed to connect to Odoo'
            }

    # Determine partner_id based on client name (in a real system, you'd look up the partner ID)
    # For this example, we'll use a default partner ID of 1
    partner_id = 1  # This would typically come from a mapping or lookup

    # For this test, we'll use simplified product mapping
    # In a real system, product_ids would be determined from the description
    product_ids = [1]  # Default product
    quantities = [1]   # Default quantity
    prices = [float(invoice_data.get('amount', 0.0))]  # Use the invoice amount as price

    # Create draft invoice in Odoo
    print("Creating draft invoice in Odoo...")
    result = odoo_mcp.draft_invoice(
        partner_id=partner_id,
        product_ids=product_ids,
        quantities=quantities,
        prices=prices,
        description=invoice_data.get('description', ''),
    )

    print(f"Odoo response: {result}")

    if result.get('status') == 'success':
        # Queue the invoice for approval
        approval_id = odoo_mcp.queue_for_approval(
            'invoice',
            result['draft_id'],
            {
                'partner_id': partner_id,
                'amount': float(invoice_data.get('amount', 0.0)),  # Use the invoice amount
                'description': invoice_data.get('description', '')
            }
        )

        # Get the operation_id from the approval queue
        operation_id = odoo_mcp.approval_queue[approval_id].get('operation_id', approval_id)

        # Update the result with approval info
        result['approval_id'] = approval_id
        result['operation_id'] = operation_id
        result['message'] += f" Approval ID: {approval_id}. Operation ID: {operation_id}."

        # Create approval file in Pending_Approval directory
        approval_path = create_approval_file(
            result.get('approval_id'),
            result.get('operation_id'),
            invoice_data,
            result
        )

        # Log operation to vault/Logs/odoo_operations.json
        log_odoo_operation(
            operation_id=result.get('operation_id'),
            action='process_pending_invoice',
            status='success',
            details={
                'invoice_file': str(invoice_file_path),
                'draft_id': result.get('draft_id'),
                'approval_id': result.get('approval_id'),
                'client_name': invoice_data.get('client_name'),
                'amount': invoice_data.get('amount'),
                'message': result.get('message')
            }
        )

        # Move the original invoice file to the Done directory
        done_dir = Path("vault/Done")
        done_dir.mkdir(exist_ok=True)

        # Create a backup of the original file in Done
        original_filename = Path(invoice_file_path).name
        done_path = done_dir / f"processed_{original_filename}"

        import shutil
        shutil.copy2(invoice_file_path, done_path)
        print(f"Original invoice file backed up to: {done_path}")

        return {
            'status': 'success',
            'draft_id': result.get('draft_id'),
            'approval_id': result.get('approval_id'),
            'operation_id': result.get('operation_id'),
            'approval_file': str(approval_path),
            'message': f"Invoice processed successfully. Draft {result.get('draft_id')} created in Odoo and approval file generated."
        }
    else:
        # Log error operation
        log_odoo_operation(
            operation_id=f"op_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            action='process_pending_invoice',
            status='error',
            details={
                'invoice_file': str(invoice_file_path),
                'error': result.get('error'),
                'client_name': invoice_data.get('client_name'),
                'amount': invoice_data.get('amount')
            }
        )

        return {
            'status': 'error',
            'error': result.get('error'),
            'message': f"Failed to process invoice: {result.get('error')}"
        }


def main():
    # Path to the invoice file to process
    invoice_file_path = "vault/Accounting/ODOO_INVOICE_FRESH.md"

    # Vault file path for Odoo connection
    vault_path = "odoo_vault.json"  # This should exist and be in gitignore

    # Check if files exist
    if not os.path.exists(invoice_file_path):
        print(f"Error: Invoice file not found: {invoice_file_path}")
        return

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

    # Process the invoice
    result = process_pending_invoice(invoice_file_path, odoo_mcp)

    print(f"Processing result: {result['message']}")

    # Disconnect from Odoo
    odoo_mcp.disconnect()

    if result['status'] == 'success':
        print("Invoice processed successfully!")
        print(f"   - Draft ID: {result['draft_id']}")
        print(f"   - Approval ID: {result['approval_id']}")
        print(f"   - Operation ID: {result['operation_id']}")
        print(f"   - Approval file: {result['approval_file']}")
    else:
        print(f"Error processing invoice: {result['error']}")


if __name__ == "__main__":
    main()