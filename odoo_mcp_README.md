# Odoo MCP Server

This MCP server provides draft-only operations for Odoo ERP integration with human-in-the-loop approval.

## Features

- Draft invoices (requires approval before posting)
- Draft payments (requires approval before posting)
- Sync bank transactions in draft mode (requires approval before posting)
- Human-in-the-loop approval workflow
- All operations are draft-only by default

## Requirements

- Python 3.7+
- `odoorpc` library
- `aiohttp` library

Install dependencies:
```bash
pip install odoorpc aiohttp
```

## Usage

Run the server:
```bash
python odoo_mcp.py --vault-path /path/to/vault.json
python odoo_mcp.py --vault-path odoo_vault.json
```

The server will be available at `http://localhost:8080` by default.

## Vault File Format

Create a JSON file with your Odoo connection details:

```json
{
    "odoo_host": "localhost",
    "odoo_port": 8069,
    "odoo_db": "your_database_name",
    "odoo_username": "your_username",
    "odoo_password": "your_password"
}
```

## Available Capabilities

### 1. draft_invoice
Creates a draft invoice in Odoo that requires approval. Returns a unique operation_id for tracking.

**Parameters:**
- `partner_id`: Customer/supplier ID
- `product_ids`: Array of product IDs
- `quantities`: Array of quantities for each product
- `prices`: Array of prices for each product
- `description`: Invoice description (optional)
- `journal_id`: Journal ID (default: 1)

**Returns:**
- `status`: "success" or "error"
- `draft_id`: The ID of the created draft invoice in Odoo
- `approval_id`: Unique ID for the approval request
- `operation_id`: Unique operation identifier for tracking
- `message`: Human-readable status message

### 2. draft_payment
Creates a draft payment in Odoo that requires approval. Returns a unique operation_id for tracking.

**Parameters:**
- `partner_id`: Customer/supplier ID
- `amount`: Payment amount
- `payment_type`: "inbound" or "outbound" (default: "inbound")
- `journal_id`: Journal ID (default: 1)
- `partner_type`: "customer" or "supplier" (default: "customer")

**Returns:**
- `status`: "success" or "error"
- `draft_id`: The ID of the created draft payment in Odoo
- `approval_id`: Unique ID for the approval request
- `operation_id`: Unique operation identifier for tracking
- `message`: Human-readable status message

### 3. sync_bank_transactions
Syncs bank transactions in draft mode with Odoo that require approval. Returns a unique operation_id for tracking.

**Parameters:**
- `bank_account_id`: Bank account ID in Odoo
- `transactions`: Array of transaction objects containing:
  - `date`: Transaction date (YYYY-MM-DD)
  - `description`: Transaction description
  - `amount`: Transaction amount
  - `partner_id`: Optional partner ID

**Returns:**
- `status`: "success" or "error"
- `transaction_count`: Number of synced transactions
- `transaction_ids`: Array of created transaction IDs
- `approval_id`: Unique ID for the approval request
- `operation_id`: Unique operation identifier for tracking
- `message`: Human-readable status message

### 4. approve_operation
Approves a draft operation and posts it to Odoo. This is part of the human-in-the-loop approval process.

**Parameters:**
- `approval_id`: The unique ID of the approval request

**Returns:**
- `status`: "success" or "error"
- `message`: Human-readable status message

### 5. get_approval_queue_status
Returns the status of all pending approval requests.

**Parameters:** None

**Returns:**
- `total_pending`: Number of pending approval requests
- `approvals`: Detailed information about pending approvals

### 6. get_draft_status
Check if a draft operation was posted after approval.

**Parameters:**
- `operation_id`: The unique operation ID to check

**Returns:**
- `status`: "success" or "error"
- `operation_id`: The checked operation ID
- `approval_id`: The approval request ID
- `draft_id`: The draft record ID in Odoo
- `current_state`: Current state of the operation ("draft", "posted", etc.)
- `operation_type`: Type of operation ("invoice", "payment", "bank_transaction")
- `message`: Human-readable status message

### 7. reject_operation
Cancel a draft operation if rejected. Can cancel operations before or after approval.

**Parameters:**
- `operation_id`: The unique operation ID to reject

**Returns:**
- `status`: "success" or "error"
- `message`: Human-readable status message
- `operation_id`: The rejected operation ID

## Example Usage

### 1. Create a draft invoice:
```json
{
  "method": "draft_invoice",
  "params": {
    "partner_id": 1,
    "product_ids": [1, 2],
    "quantities": [2, 1],
    "prices": [50.0, 30.0],
    "description": "Sample invoice"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "draft_id": 123,
  "approval_id": "invoice_123_20230101_120000_123456",
  "operation_id": "op_invoice_123_20230101_120000_123456",
  "message": "Draft invoice 123 created successfully and queued for approval. Approval ID: invoice_123_20230101_120000_123456. Operation ID: op_invoice_123_20230101_120000_123456. Requires human approval before posting."
}
```

### 2. Approve an operation:
```json
{
  "method": "approve_operation",
  "params": {
    "approval_id": "invoice_123_20230101_120000_123456"
  }
}
```

### 3. Check approval queue status:
```json
{
  "method": "get_approval_queue_status",
  "params": {}
}
```

### 4. Check draft status:
```json
{
  "method": "get_draft_status",
  "params": {
    "operation_id": "op_invoice_123_20230101_120000_123456"
  }
}
```

### 5. Reject an operation:
```json
{
  "method": "reject_operation",
  "params": {
    "operation_id": "op_invoice_123_20230101_120000_123456"
  }
}
```

## Human-in-the-Loop Approval Process

1. All operations (invoices, payments, bank transactions) are created in draft mode
2. Each draft operation is assigned a unique approval ID and queued for approval
3. The operation remains in draft mode until approved
4. Use `approve_operation` to approve and post the draft to Odoo
5. Approved operations are permanently posted to Odoo

## Security

- Store your Odoo credentials securely in the vault file
- The vault file should not be committed to version control
- Use appropriate file permissions to protect the vault file