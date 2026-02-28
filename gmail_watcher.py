#!/usr/bin/env python3
"""
Gmail Watcher - Monitors Gmail for new unread/important emails and creates
markdown files in the Needs_Action folder of your Obsidian vault.

This script uses the Gmail API to check for new emails every 2 minutes,
then creates markdown files with email metadata and suggested actions.
"""
import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, Any

# Gmail API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def authenticate_gmail():
    """
    Authenticate with Gmail API.
    Uses credentials.json and token.json in same directory as script.
    """
    creds = None
    # Token stored in same directory as script for security (not in vault)
    token_path = Path(__file__).parent / 'token.json'
    credentials_path = Path(__file__).parent / 'credentials.json'

    # Load existing token if available
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Failed to refresh credentials: {e}")
                # If refresh fails, delete token and re-authenticate
                if token_path.exists():
                    token_path.unlink()
                creds = None

        if not creds:
            if not credentials_path.exists():
                logging.error(f"Credentials file not found: {credentials_path}")
                logging.error("Please set up your Google API credentials.json first")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds

def get_unread_important_emails(service, processed_message_ids: Set[str]):
    """
    Fetch unread emails with 'important' category from Gmail.
    Returns a list of email objects that haven't been processed yet.
    """
    try:
        # Search for unread emails that are important
        # Using 'is:important is:unread' query to get important unread emails
        results = service.users().messages().list(
            userId='me',
            q='is:important is:unread',
            maxResults=10  # Limit to 10 emails per check to avoid rate limits
        ).execute()

        messages = results.get('messages', [])
        new_emails = []

        for message in messages:
            message_id = message['id']

            # Skip if already processed
            if message_id in processed_message_ids:
                continue

            # Get the full message details
            msg = service.users().messages().get(
                userId='me',
                id=message_id
            ).execute()

            # Extract email data
            email_data = extract_email_data(msg)
            if email_data:
                email_data['message_id'] = message_id
                new_emails.append(email_data)

        return new_emails

    except HttpError as error:
        logging.error(f'An error occurred while fetching emails: {error}')
        return []

def extract_email_data(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant data from Gmail message object.
    """
    email_data = {
        'from': '',
        'subject': '',
        'body': '',
        'snippet': '',
        'received': '',
        'priority': 'normal'  # Default to normal priority
    }

    # Extract headers
    headers = message.get('payload', {}).get('headers', [])
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')

        if name == 'from':
            email_data['from'] = value
        elif name == 'subject':
            email_data['subject'] = value
        elif name == 'date':
            # Convert Gmail date format to ISO format
            try:
                import email.utils
                parsed_date = email.utils.parsedate_to_datetime(value)
                email_data['received'] = parsed_date.isoformat()
            except:
                email_data['received'] = datetime.utcnow().isoformat()

    # Extract the full email body
    email_data['body'] = extract_email_body(message)

    # Extract snippet (short preview of email)
    email_data['snippet'] = message.get('snippet', '')

    # Use the body if available, otherwise fallback to snippet
    email_content = email_data['body'] if email_data['body'] else email_data['snippet']

    # Determine priority based on sender and content
    email_data['priority'] = determine_email_priority_with_content(email_data, email_content)

    # Determine received timestamp if not already set
    if not email_data['received']:
        email_data['received'] = datetime.utcnow().isoformat()

    return email_data


def extract_email_body(message: Dict[str, Any]) -> str:
    """
    Extract the text body from a Gmail message object.
    """
    import base64
    payload = message.get('payload', {})
    body = ''

    # Handle different message formats
    if 'parts' in payload:
        # Multipart message - look for text/plain or text/html parts
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                # Decode the base64 encoded message body
                body_data = part['body']['data']
                body_decoded = base64.urlsafe_b64decode(body_data.encode('ASCII'))
                body = body_decoded.decode('utf-8')
                break  # Use the text/plain version if available
            elif part['mimeType'] == 'text/html' and not body:
                # If no plain text version found, try html version
                body_data = part['body']['data']
                body_decoded = base64.urlsafe_b64decode(body_data.encode('ASCII'))
                import html
                body = html.unescape(body_decoded.decode('utf-8'))
    else:
        # Single part message
        if 'body' in payload and 'data' in payload['body']:
            body_data = payload['body']['data']
            body_decoded = base64.urlsafe_b64decode(body_data.encode('ASCII'))
            body = body_decoded.decode('utf-8')

    # Clean up the email body to remove common quoted reply patterns
    if body:
        body = clean_email_body(body)

    return body


def clean_email_body(body: str) -> str:
    """
    Clean email body to remove quoted replies and signatures.
    """
    import re

    # First, handle the case where quoted text is in the same line (like "text On DATE, NAME wrote: more text")
    # This handles the specific issue in the example: "I am not available today. On Tue, Feb 24, 2026, 11:39 PM <malaika57680@gmail.com> wrote: you are available..."
    body = re.sub(r'\s*On\s+.*?\d{4}.*?wrote:.*$', '', body, flags=re.IGNORECASE)

    # Also handle the pattern "text <email> wrote: more text"
    body = re.sub(r'\s*<[^>]+@[^>]+>\s+wrote:\s*.*$', '', body)

    # Split into lines for other cleaning operations
    lines = body.split('\n')
    cleaned_lines = []
    skip_section = False

    for line in lines:
        # Skip lines that look like quoted replies
        if line.strip().startswith('>'):
            skip_section = True
            continue

        # Skip lines that look like date/sender headers in quotations
        if re.match(r'^On.*\d{4},.*wrote:$', line.strip(), re.IGNORECASE):
            skip_section = True
            continue
        if re.match(r'^.*<.*@.*>.*wrote:$', line.strip()):
            skip_section = True
            continue
        if line.strip().startswith('On ') and ('wrote:' in line or 'said:' in line):
            skip_section = True
            continue

        # Skip common reply headers
        if re.match(r'^.*wrote:$', line.strip(), re.IGNORECASE):
            skip_section = True
            continue

        # Check if we're in a quoted section and this line isn't a new message
        if skip_section:
            # If we encounter a normal line after skipping, this might be the start of new content
            if line.strip() and not line.strip().startswith('>'):
                # Reset skip_section to process further lines (this handles cases where new content follows quoted content)
                skip_section = False
                cleaned_lines.append(line)
            else:
                # Still in a skipped section
                continue
        else:
            # Add the line if it's not a quoted reply
            cleaned_lines.append(line)

    cleaned_body = '\n'.join(cleaned_lines)

    # Remove multiple consecutive blank lines
    cleaned_body = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_body)

    # Strip leading/trailing whitespace
    cleaned_body = cleaned_body.strip()

    return cleaned_body


def determine_email_priority_with_content(email_data: Dict[str, Any], email_content: str) -> str:
    """
    Determine email priority based on sender, subject, and content.
    """
    sender = email_data.get('from', '').lower()
    subject = email_data.get('subject', '').lower()
    content = email_content.lower()

    # Define high priority keywords and senders
    high_priority_keywords = [
        'urgent', 'asap', 'immediate', 'important', 'critical',
        'emergency', 'deadline', 'meeting', 'today', 'now'
    ]

    high_priority_senders = [
        'boss@', 'manager@', 'director@', 'ceo@', 'cto@',
        'executive@', 'supervisor@', 'founder@', 'president@'
    ]

    # Check for high priority senders
    for high_sender in high_priority_senders:
        if high_sender in sender:
            return 'high'

    # Check for high priority keywords in subject and content
    combined_text = f"{subject} {content}"
    for keyword in high_priority_keywords:
        if keyword in combined_text:
            return 'high'

    # Check for medium priority keywords
    medium_priority_keywords = [
        'follow', 'reply', 'response', 'action', 'required',
        'request', 'needed', 'review', 'discuss', 'call'
    ]

    for keyword in medium_priority_keywords:
        if keyword in combined_text:
            return 'medium'

    # Default to normal priority
    return 'normal'


def determine_email_priority(email_data: Dict[str, Any]) -> str:
    """
    Legacy function to maintain compatibility with existing code.
    """
    # This function is kept for compatibility but should not be used directly
    return determine_email_priority_with_content(email_data, email_data.get('snippet', ''))

def create_email_markdown_file(email_data: Dict[str, Any], vault_path: Path):
    """
    Create a markdown file for the email in the Needs_Action folder.
    """
    needs_action_path = vault_path / 'Needs_Action'
    needs_action_path.mkdir(exist_ok=True)  # Create folder if it doesn't exist

    # Sanitize filename based on email subject and message ID
    safe_subject = "".join(c for c in email_data['subject'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"EMAIL_{email_data['message_id']}.md"
    file_path = needs_action_path / filename

    # Create frontmatter with metadata
    frontmatter = f"""---
type: email
from: {email_data['from'].replace('"', "'")}
subject: {email_data['subject'].replace('"', "'")}
received: {email_data['received']}
priority: {email_data['priority']}
status: pending
---
"""

    # Create markdown content - use the extracted body if available, otherwise fallback to snippet
    email_content = email_data.get('body', '') or email_data.get('snippet', '')
    content = f"""{frontmatter}

## Email Content
{email_content}

## Suggested Actions
- [ ] Reply
- [ ] Forward
- [ ] Archive
"""

    # Write the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logging.info(f"New email detected: {email_data['subject']} → created {filename}")
    return file_path

def load_processed_emails(vault_path: Path) -> Set[str]:
    """
    Load previously processed email message IDs from a tracking file.
    """
    tracking_file = vault_path / '.gmail_processed.json'
    if tracking_file.exists():
        try:
            with open(tracking_file, 'r') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError):
            return set()
    return set()

def save_processed_emails(processed_ids: Set[str], vault_path: Path):
    """
    Save processed email message IDs to a tracking file.
    """
    tracking_file = vault_path / '.gmail_processed.json'
    with open(tracking_file, 'w') as f:
        json.dump(list(processed_ids), f)

def main():
    """Main function to run the Gmail watcher"""
    setup_logging()
    logging.info("Starting Gmail Watcher...")

    parser = argparse.ArgumentParser(description='Monitor Gmail for new important emails')
    parser.add_argument('--vault-path', required=True, help='Path to your Obsidian vault')
    args = parser.parse_args()

    vault_path = Path(args.vault_path).resolve()
    if not vault_path.exists():
        logging.error(f"Vault path does not exist: {vault_path}")
        return 1

    # Authenticate with Gmail
    creds = authenticate_gmail()
    if not creds:
        logging.error("Failed to authenticate with Gmail")
        return 1

    try:
        service = build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logging.error(f"Failed to build Gmail service: {e}")
        return 1

    # Load previously processed email IDs
    processed_message_ids = load_processed_emails(vault_path)
    logging.info(f"Loaded {len(processed_message_ids)} previously processed emails")

    logging.info("Gmail Watcher is now running. Press Ctrl+C to stop.")
    logging.info("Checking for new emails every 2 minutes...")

    try:
        while True:
            try:
                # Get unread important emails that haven't been processed yet
                new_emails = get_unread_important_emails(service, processed_message_ids)

                if new_emails:
                    logging.info(f"Found {len(new_emails)} new important emails")

                    for email_data in new_emails:
                        create_email_markdown_file(email_data, vault_path)
                        processed_message_ids.add(email_data['message_id'])

                    # Save the updated list of processed emails
                    save_processed_emails(processed_message_ids, vault_path)
                else:
                    logging.debug("No new important emails found")

            except Exception as e:
                logging.error(f"Error during email check: {e}")

            # Wait for 2 minutes before next check
            time.sleep(120)

    except KeyboardInterrupt:
        logging.info("Gmail Watcher stopped by user")
        return 0

if __name__ == '__main__':
    sys.exit(main())