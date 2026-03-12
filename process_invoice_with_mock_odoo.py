#!/usr/bin/env python3
"""
Process pending invoice files and create draft invoices in Odoo with approval workflow.
This version includes a mock Odoo connection for testing when a real Odoo server is not available.
"""
import json
import os
import frontmatter
from datetime import datetime
from pathlib import Path
import sys
import random
import string


def generate_mock_odoo_response():
    """Generate a mock Odoo response for testing purposes."""
    draft_id = random.randint(100, 999)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = ''.join(random.choices(string.digits, k=6))

    approval_id = f"invoice_{draft_id}_{timestamp}_{random_suffix}"
    operation_id = f"op_invoice_{draft_id}_{timestamp}_{random_suffix}"

    return {
        "status": "success",
        "draft_id": draft_id,
        "approval_id": approval_id,
        "operation_id": operation_id,
        "message": f"Draft invoice {draft_id} created successfully and queued for approval. Approval ID: {approval_id}. Operation ID: {operation_id}. Requires human approval before posting."
    }


def read_invoice_file(file_path):
    """Read the invoice markdown file and extract metadata."""
    with open(file_path, 'r') as f:
        post = frontmatter.load(f)
        return post.metadata


def create_approval_file(approval_id, operation_id, invoice_data, odoo_response):
    """Create an approval file in the Pending_Approval directory."""
    approval_dir = Path("vault/Pending_Approval")
    approval_dir.mkdir(exist_ok=True)

    # Generate a unique filename for the approval
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    approval_filename = f"ODOO_INVOICE_APPROVAL_{timestamp}.md"
    approval_path = approval_dir / approval_filename

    approval_content = f"""---
type: odoo_invoice_approval
original_file: pending_invoice_test.md
status: pending_approval
priority: normal
approval_id: {approval_id}
operation_id: {operation_id}
invoice_number: {invoice_data.get('invoice_number', 'N/A')}
client_name: {invoice_data.get('client_name', 'N/A')}
amount: {invoice_data.get('amount', 'N/A')}
---

# Odoo Invoice Approval Request

## Invoice Details

- **Invoice Number**: {invoice_data.get('invoice_number', 'N/A')}
- **Client**: {invoice_data.get('client_name', 'N/A')}
- **Amount**: ${invoice_data.get('amount', 'N/A')}
- **Due Date**: {invoice_data.get('due_date', 'N/A')}
- **Description**: {invoice_data.get('description', 'N/A')}
- **Odoo Draft ID**: {odoo_response.get('draft_id', 'N/A')}
- **Operation ID**: {operation_id}
- **Approval ID**: {approval_id}

## Action Required

An invoice has been created in draft mode in Odoo and requires human approval before posting. Please review the details and approve or reject the invoice.

### Odoo System Response:
{odoo_response.get('message', 'N/A')}

## Approval Options

- [ ] Approve and post invoice to Odoo
- [ ] Reject invoice
- [ ] Review details before approving
"""

    with open(approval_path, 'w') as f:
        f.write(approval_content)

    print(f"Approval file created: {approval_path}")
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


def process_pending_invoice_with_mock(invoice_file_path):
    """Process a pending invoice file using mock Odoo responses."""
    print(f"Processing invoice file: {invoice_file_path}")

    # Read the invoice file
    invoice_data = read_invoice_file(invoice_file_path)
    print(f"Invoice data: {invoice_data}")

    # Simulate creating a draft invoice in Odoo (with mock response)
    print("Creating draft invoice in Odoo (mock)...")
    result = generate_mock_odoo_response()

    print(f"Mock Odoo response: {result}")

    if result.get('status') == 'success':
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
                'error': result.get('error', 'Mock error'),
                'client_name': invoice_data.get('client_name'),
                'amount': invoice_data.get('amount')
            }
        )

        return {
            'status': 'error',
            'error': result.get('error', 'Mock error'),
            'message': f"Failed to process invoice: {result.get('error', 'Mock error')}"
        }


def main():
    # Path to the invoice file to process
    invoice_file_path = "vault/Accounting/pending_invoice_test.md"

    # Check if file exists
    if not os.path.exists(invoice_file_path):
        print(f"Error: Invoice file not found: {invoice_file_path}")
        return

    # Process the invoice with mock Odoo
    result = process_pending_invoice_with_mock(invoice_file_path)

    print(f"Processing result: {result['message']}")

    if result['status'] == 'success':
        print("Invoice processed successfully!")
        print(f"   - Draft ID: {result['draft_id']}")
        print(f"   - Approval ID: {result['approval_id']}")
        print(f"   - Operation ID: {result['operation_id']}")
        print(f"   - Approval file: {result['approval_file']}")

        # Show where the log was created
        print(f"   - Operation logged to vault/Logs/odoo_operations.json")
    else:
        print(f"Error processing invoice: {result['error']}")


if __name__ == "__main__":
    main()