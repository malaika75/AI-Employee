#!/usr/bin/env python3
"""
Test script to verify Gmail API authentication and basic functionality.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path to import from gmail_watcher
sys.path.insert(0, str(Path(__file__).parent))

from gmail_watcher import authenticate_gmail, get_unread_important_emails

def test_gmail_connection():
    """Test basic Gmail API connection"""
    print("Testing Gmail API connection...")

    # Authenticate
    creds = authenticate_gmail()
    if not creds:
        print("❌ Failed to authenticate with Gmail")
        return False

    print("✅ Successfully authenticated with Gmail")

    # Test getting emails (with empty set for processed emails)
    from googleapiclient.discovery import build
    try:
        service = build('gmail', 'v1', credentials=creds)
        # Get just a few emails to test the connection
        results = service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=1
        ).execute()

        messages = results.get('messages', [])
        print(f"✅ Gmail API connection working. Found {len(messages)} unread important emails to test with.")

        return True
    except Exception as e:
        print(f"❌ Error testing Gmail API: {e}")
        return False

if __name__ == "__main__":
    success = test_gmail_connection()
    if not success:
        sys.exit(1)
    print("✅ All tests passed!")