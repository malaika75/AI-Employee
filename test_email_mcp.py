#!/usr/bin/env python3
"""
Test script for Email MCP Server
"""

import sys
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from email_mcp import EmailMCPServer
    print("[OK] Successfully imported EmailMCPServer")

    # Create server instance
    server = EmailMCPServer(port=8081)  # Use different port for testing
    print("[OK] Successfully created EmailMCPServer instance")

    # Verify directories were created
    for dir_path in [server.approval_dir, server.rejected_dir, server.pending_dir]:
        if dir_path.exists():
            print(f"[OK] Directory exists: {dir_path}")
        else:
            print(f"[ERROR] Directory does not exist: {dir_path}")

    print("\n[OK] Server setup test completed successfully!")
    print("The Email MCP Server is ready to use.")

except Exception as e:
    print(f"[ERROR] Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)