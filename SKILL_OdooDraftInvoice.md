# SKILL: Odoo Draft Invoice with Approval

## Description
Creates a draft invoice in Odoo ERP that requires human approval before posting. This skill follows the Gold Tier compliance requirements with full logging, operation tracking, and approval workflow.

## Method
```
draft_invoice
```

## Parameters
- `partner_id` (integer): Customer/supplier ID in Odoo
- `product_ids` (array): List of product IDs to include in the invoice
- `quantities` (array): List of quantities for each product (must match length of product_ids)
- `prices` (array): List of prices for each product (must match length of product_ids)
- `description` (string, optional): Description for the invoice
- `journal_id` (integer, optional): Journal ID to use (default: 1 for sales journal)

## Response
- `status` (string): "success" or "error"
- `draft_id` (integer): The ID of the created draft invoice in Odoo
- `approval_id` (string): Unique ID for the approval request
- `message` (string): Human-readable status message
- `operation_id` (string): Unique operation identifier for tracking

## Example Request
```json
{
  "method": "draft_invoice",
  "params": {
    "partner_id": 1,
    "product_ids": [1, 2],
    "quantities": [2, 1],
    "prices": [50.0, 30.0],
    "description": "Sample invoice for approval"
  }
}
```

## Example Response
```json
{
  "status": "success",
  "draft_id": 123,
  "approval_id": "invoice_123_20230101_120000_123456",
  "operation_id": "op_invoice_123_20230101_120000_123456",
  "message": "Draft invoice 123 created successfully and queued for approval. Approval ID: invoice_123_20230101_120000_123456. Operation ID: op_invoice_123_20230101_120000_123456. Requires human approval before posting."
}
```

## Workflow
1. Creates a draft invoice in Odoo ERP system
2. Automatically assigns a unique operation_id for tracking
3. Queues the operation for human approval (Pending_Approval status)
4. Log the operation to vault/Logs/odoo_operations.json
5. Returns the approval_id and operation_id for status tracking
6. Invoice remains in draft mode until human approves via approve_operation
7. Human must move approval request from Pending_Approval to Approved to post
8. Use get_draft_status(operation_id) to check if draft was posted after approval
9. Use reject_operation(operation_id) to cancel draft if rejected

## Compliance Notes
- All operations are draft-only until approved by human
- Operation logging to vault/Logs/odoo_operations.json
- Error recovery with retry mechanism (max 3 attempts)
- Operation tracking via operation_id
- Human must explicitly approve before posting to production system