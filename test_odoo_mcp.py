#!/usr/bin/env python3
"""
Test script for Odoo MCP server
This script tests the functionality of the Odoo MCP server without requiring an actual Odoo instance
"""
import json
import os
from unittest.mock import Mock, patch
import sys
import tempfile

# Add the current directory to the path so we can import odoo_mcp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from odoo_mcp import OdooMCP


def test_odoo_mcp():
    """Test the basic functionality of the OdooMCP class"""

    # Create a temporary vault file for testing
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as vault_file:
        vault_data = {
            'odoo_host': 'localhost',
            'odoo_port': 8069,
            'odoo_db': 'test_db',
            'odoo_username': 'admin',
            'odoo_password': 'admin'
        }
        json.dump(vault_data, vault_file)
        vault_path = vault_file.name

    try:
        # Create the OdooMCP instance
        odoo_mcp = OdooMCP(vault_path)

        # Test that the vault data was loaded correctly
        assert odoo_mcp.odoo_host == 'localhost'
        assert odoo_mcp.odoo_port == 8069
        assert odoo_mcp.odoo_db == 'test_db'
        assert odoo_mcp.odoo_username == 'admin'
        assert odoo_mcp.odoo_password == 'admin'

        print("OK - Vault data loaded correctly")

        # Mock the odoorpc module for testing
        with patch('odoorpc.ODOO') as mock_odoo_class:
            # Create a mock Odoo instance
            mock_odoo_instance = Mock()
            mock_odoo_class.return_value = mock_odoo_instance
            mock_odoo_instance.login.return_value = 1  # Return a valid user ID

            # Mock the execute method to return test data
            def mock_execute(model, method, *args, **kwargs):
                if model == 'account.move' and method == 'create':
                    return 123  # Return a test invoice ID
                elif model == 'account.payment' and method == 'create':
                    return 456  # Return a test payment ID
                elif model == 'account.bank.statement.line' and method == 'create':
                    return 789  # Return a test transaction ID
                elif model == 'account.move' and method == 'action_post':
                    return True  # Mock successful posting
                elif model == 'account.payment' and method == 'action_post':
                    return True  # Mock successful posting
                return None

            mock_odoo_instance.execute.side_effect = mock_execute

            # Test connection
            assert odoo_mcp.connect() == True
            print("OK - Connection test passed")

            # Test draft_invoice
            result = odoo_mcp.draft_invoice(
                partner_id=1,
                product_ids=[1, 2],
                quantities=[2, 3],
                prices=[10.0, 15.0],
                description="Test invoice"
            )

            assert result['status'] == 'success'
            assert result['draft_id'] == 123
            print("OK - Draft invoice test passed")

            # Test draft_payment
            result = odoo_mcp.draft_payment(
                partner_id=1,
                amount=100.0,
                payment_type='inbound'
            )

            assert result['status'] == 'success'
            assert result['draft_id'] == 456
            print("OK - Draft payment test passed")

            # Test sync_bank_transactions
            result = odoo_mcp.sync_bank_transactions(
                bank_account_id=1,
                transactions=[
                    {
                        'date': '2023-01-01',
                        'description': 'Test transaction',
                        'amount': 50.0
                    }
                ]
            )

            assert result['status'] == 'success'
            assert result['transaction_count'] == 1
            print("OK - Sync bank transactions test passed")

            # Test approval queue functionality
            # Queue an invoice for approval
            approval_id = odoo_mcp.queue_for_approval(
                'invoice',
                123,
                {'partner_id': 1, 'amount': 95.0, 'description': 'Test invoice'}
            )

            assert approval_id.startswith('invoice_123_')
            print("OK - Queue for approval test passed")

            # Check approval queue status
            status = odoo_mcp.get_approval_queue_status()
            assert status['total_pending'] == 1
            print("OK - Approval queue status test passed")

            # Test approve operation
            result = odoo_mcp.approve_operation(approval_id)
            assert result['status'] == 'success'

            # Check that the approval status is now approved
            assert odoo_mcp.approval_queue[approval_id]['status'] == 'approved'
            print("OK - Approve operation test passed")

            # Test handle_request method
            # Test draft_invoice request
            request = {
                'method': 'draft_invoice',
                'params': {
                    'partner_id': 1,
                    'product_ids': [1],
                    'quantities': [1],
                    'prices': [10.0],
                    'description': 'Test request'
                }
            }

            result = odoo_mcp.handle_request(request)
            assert result['status'] == 'success'
            assert 'approval_id' in result
            print("OK - Handle request (draft_invoice) test passed")

            # Test approve_operation request
            approval_id = result['approval_id']
            request = {
                'method': 'approve_operation',
                'params': {
                    'approval_id': approval_id
                }
            }

            result = odoo_mcp.handle_request(request)
            assert result['status'] == 'success'
            print("OK - Handle request (approve_operation) test passed")

            # Test get_approval_queue_status request
            request = {
                'method': 'get_approval_queue_status',
                'params': {}
            }

            result = odoo_mcp.handle_request(request)
            assert 'total_pending' in result
            print("OK - Handle request (get_approval_queue_status) test passed")

            # Test unknown method
            request = {
                'method': 'unknown_method',
                'params': {}
            }

            result = odoo_mcp.handle_request(request)
            assert 'error' in result
            print("OK - Handle unknown method test passed")

            print("\nAll tests passed! The Odoo MCP server implementation is working correctly.")

    finally:
        # Clean up the temporary vault file
        os.unlink(vault_path)


if __name__ == "__main__":
    test_odoo_mcp()