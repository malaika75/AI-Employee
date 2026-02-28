#!/usr/bin/env python3
"""
Simple client to test the Email MCP Server
"""

import socket
import json

def test_server_capabilities():
    """Test the server capabilities"""
    try:
        # Connect to the server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 8080))

        # Send get_capabilities request
        request = {
            "id": 1,
            "method": "get_capabilities",
            "params": {}
        }

        client_socket.send(json.dumps(request).encode() + b'\n')

        # Receive response
        response_data = client_socket.recv(4096).decode()
        response = json.loads(response_data.strip())

        print("Server Response:", json.dumps(response, indent=2))

        if "result" in response:
            print("\nServer is working correctly!")
            print(f"Name: {response['result']['name']}")
            print(f"Version: {response['result']['version']}")
            print("Capabilities:")
            for cap in response['result']['capabilities']:
                print(f"  - {cap['name']}: {cap['description']}")
        else:
            print(f"Error: {response.get('error', 'Unknown error')}")

        client_socket.close()
        return True

    except Exception as e:
        print(f"Error connecting to server: {e}")
        return False

if __name__ == "__main__":
    print("Testing Email MCP Server...")
    success = test_server_capabilities()
    if success:
        print("\n[OK] Server test completed successfully!")
    else:
        print("\n[ERROR] Server test failed!")