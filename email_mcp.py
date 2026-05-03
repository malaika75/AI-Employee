#!/usr/bin/env python3
"""
Email MCP Server for Claude Code
This server handles email-related actions with human-in-the-loop approval
"""

import json
import socket
import threading
import time
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Gmail API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pickle

# Import the new utilities
from retry_utils import retry_with_exponential_backoff
from audit_logger import audit_logger


class ApprovalHandler(FileSystemEventHandler):
    def __init__(self, server):
        self.server = server

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.md'):
            filename = Path(event.src_path).name
            if 'Archived' in event.src_path:
                self.server.handle_archived_email(filename)
            elif 'Approved' in event.src_path:
                self.server.handle_approval(filename)
            elif 'Rejected' in event.src_path:
                self.server.handle_rejection(filename)


class EmailMCPServer:
    def __init__(self, host='localhost', port=8081):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.clients = set()

        # Setup directories
        self.archived_dir = Path('vault') / 'Archived'
        self.approval_dir = Path('vault') / 'Approved'
        self.rejected_dir = Path('vault') / 'Rejected'
        self.pending_dir = Path('vault') / 'Pending_Approval'

        # Create directories if they don't exist
        self.ensure_directories()

        # Setup file watchers
        self.setup_file_watchers()

        # Setup Gmail service
        self.gmail_service = self.setup_gmail_service()

        # Thread for the server
        self.server_thread = None

    def ensure_directories(self):
        """Create required directories if they don't exist"""
        for directory in [self.approval_dir, self.rejected_dir, self.pending_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def setup_file_watchers(self):
        """Setup file system watchers for approval/rejection directories"""
        self.observer = Observer()

        # Watch Archived directory for emails to send
        if self.archived_dir.exists():
            archived_handler = ApprovalHandler(self)
            self.observer.schedule(archived_handler, str(self.archived_dir), recursive=False)

        # Watch Approved directory (for backward compatibility)
        if self.approval_dir.exists():
            approval_handler = ApprovalHandler(self)
            self.observer.schedule(approval_handler, str(self.approval_dir), recursive=False)

        # Watch Rejected directory
        if self.rejected_dir.exists():
            rejection_handler = ApprovalHandler(self)
            self.observer.schedule(rejection_handler, str(self.rejected_dir), recursive=False)

        self.observer.start()

    def setup_gmail_service(self):
        """Setup Gmail API service using existing credentials or initiate OAuth flow"""
        try:
            # Use the same token.json and credentials.json as gmail_watcher.py
            token_path = Path(__file__).parent / 'token.json'
            credentials_path = Path(__file__).parent / 'credentials.json'

            creds = None
            # If token doesn't exist, we'll need to initiate OAuth flow
            if token_path.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(token_path), [
                        'https://www.googleapis.com/auth/gmail.send',
                        'https://www.googleapis.com/auth/gmail.compose',
                        'https://www.googleapis.com/auth/gmail.modify',
                        'https://www.googleapis.com/auth/gmail.readonly'
                    ])
                except Exception as e:
                    error_msg = f"Error loading existing token: {e}"
                    print(error_msg)
                    audit_logger.log_error(
                        action_type="gmail_service_init",
                        error=error_msg,
                        details={"step": "token_load"}
                    )
                    creds = None

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        error_msg = f"Failed to refresh credentials: {e}"
                        print(error_msg)
                        audit_logger.log_error(
                            action_type="gmail_service_init",
                            error=error_msg,
                            details={"step": "token_refresh"}
                        )
                        # If refresh fails, we need to get new credentials
                        creds = None

                # If still no valid credentials, initiate OAuth flow
                if not creds:
                    if not credentials_path.exists():
                        error_msg = f"Error: Credentials file not found: {credentials_path}"
                        print(error_msg)
                        print("Please set up your Google API credentials.json first")
                        audit_logger.log_error(
                            action_type="gmail_service_init",
                            error=error_msg,
                            details={"step": "credentials_check"}
                        )
                        return None

                    print("No valid token found. Initiating OAuth flow for email permissions...")
                    audit_logger.log_warning(
                        action_type="gmail_service_init",
                        warning="No valid token found, initiating OAuth flow",
                        details={"step": "oauth_init"}
                    )
                    try:
                        from google_auth_oauthlib.flow import InstalledAppFlow
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_path, [
                                'https://www.googleapis.com/auth/gmail.send',
                                'https://www.googleapis.com/auth/gmail.compose',
                                'https://www.googleapis.com/auth/gmail.modify',
                                'https://www.googleapis.com/auth/gmail.readonly'
                            ])
                        creds = flow.run_local_server(port=0)

                        # Save the credentials for the next run
                        with open(token_path, 'w') as token:
                            token.write(creds.to_json())
                        print("New token created successfully!")
                        audit_logger.log_success(
                            action_type="gmail_service_init",
                            details={"step": "token_creation"}
                        )
                    except Exception as e:
                        error_msg = f"Failed to initiate OAuth flow: {e}"
                        print(error_msg)
                        audit_logger.log_error(
                            action_type="gmail_service_init",
                            error=error_msg,
                            details={"step": "oauth_flow"}
                        )
                        return None

            service = build('gmail', 'v1', credentials=creds)
            print("Gmail service initialized successfully")
            audit_logger.log_success(
                action_type="gmail_service_init",
                details={"status": "success"}
            )
            return service
        except Exception as e:
            error_msg = f"Error setting up Gmail service: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            audit_logger.log_error(
                action_type="gmail_service_init",
                error=error_msg,
                details={"step": "final_build"}
            )
            return None

    def create_message(self, sender, to, subject, message_text):
        """Create a message for the Gmail API"""
        try:
            message = MIMEText(message_text)
            message['to'] = to
            message['from'] = sender
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            return {'raw': raw_message}
        except Exception as e:
            print(f"Error creating message: {e}")
            return None

    def handle_approval(self, filename):
        """Handle when a file is moved to the Approved directory"""
        print(f"Approval detected: {filename}")

        # Skip social media approval files - let social_mcp.py handle them
        if 'SOCIAL' in filename.upper() or 'LINKEDIN' in filename.upper() or 'TWITTER' in filename.upper() or 'FACEBOOK' in filename.upper() or 'INSTAGRAM' in filename.upper():
            print(f"Skipping social media approval file: {filename} (will be handled by social_mcp.py)")
            return

        # Only handle EMAIL files
        if 'EMAIL' not in filename.upper():
            print(f"Skipping non-email file: {filename}")
            return

        file_path = self.approval_dir / filename

        # Add small delay to ensure file is fully written
        time.sleep(0.5)

        if not file_path.exists():
            print(f"File {filename} no longer exists, may have been processed by another handler")
            return

        # Create a lock file to prevent race conditions
        lock_file = file_path.with_suffix('.lock')
        try:
            # Try to create lock file (atomic operation)
            if lock_file.exists():
                print(f"File {filename} is locked by another process")
                return

            lock_file.touch()

            # Double-check file still exists after acquiring lock
            if not file_path.exists():
                print(f"File {filename} was removed before processing")
                if lock_file.exists():
                    lock_file.unlink()
                return

            try:
                content = file_path.read_text()
                parsed = self.parse_approval_file(content)

                # Process the email based on action type
                action = parsed.get('action', '')

                # If no action specified but it's an email file, default to send_email
                if not action and parsed.get('type') == 'email':
                    action = 'send_email'
                    print(f"No action specified, defaulting to send_email for {filename}")

                if action == 'send_email':
                    self.send_email(parsed)
                elif action == 'draft_email':
                    self.draft_email(parsed)
                else:
                    print(f"Unknown or missing action: {action} for {filename}")
                    raise Exception(f"Unknown action: {action}")

                # Update the status in the file to "completed"
                content = file_path.read_text()
                updated_content = content.replace('status: pending', 'status: completed')
                updated_content = updated_content.replace('status: draft', 'status: completed')
                file_path.write_text(updated_content)

                # Only move to Done if processing was successful (no exception raised)
                done_dir = Path('vault') / 'Done'
                done_dir.mkdir(exist_ok=True)
                done_path = done_dir / filename

                # Use shutil.move for safer file moving
                import shutil
                if file_path.exists():
                    shutil.move(str(file_path), str(done_path))
                    print(f"Successfully processed and moved {filename} to Done folder")

            except Exception as e:
                print(f"Error processing approved file {filename}: {e}")
                traceback.print_exc()

                # Move to error folder for manual review
                error_dir = Path('vault') / 'Errors'
                error_dir.mkdir(exist_ok=True)
                error_path = error_dir / f"ERROR_{filename}"
                if file_path.exists():
                    import shutil
                    shutil.move(str(file_path), str(error_path))
                    print(f"Moved failed file to {error_path}")

            finally:
                # Always remove lock file
                if lock_file.exists():
                    lock_file.unlink()

        except Exception as e:
            print(f"Error acquiring lock for {filename}: {e}")
            if lock_file.exists():
                lock_file.unlink()

    def handle_archived_email(self, filename):
        """Handle when a file is placed in the Archived directory - these are emails to send directly"""
        print(f"Archived email detected (sending directly): {filename}")
        file_path = self.archived_dir / filename

        if file_path.exists():
            try:
                content = file_path.read_text()
                parsed = self.parse_approval_file(content)

                # Determine action - could be send_email or draft_email
                action = parsed.get('action', 'send_email')

                if action == 'send_email':
                    self.send_email(parsed)
                elif action == 'draft_email':
                    self.draft_email(parsed)
                elif action == 'sent_direct':  # For emails that are already sent but need archiving
                    print(f"Email already sent: {filename}")
                else:
                    print(f"Unknown action '{action}' for file: {filename}")

                # Move file to internal archive after processing
                archive_dir = Path('vault') / 'Archive'
                archive_dir.mkdir(exist_ok=True)
                archive_path = archive_dir / filename
                file_path.rename(archive_path)

            except Exception as e:
                print(f"Error processing archived email {filename}: {e}")
                if "cannot find the file specified" in str(e) or "No such file or directory" in str(e):
                    print(f"File {filename} may have already been processed or moved by another event.")
                else:
                    import traceback
                    traceback.print_exc()

    def handle_rejection(self, filename):
        """Handle when a file is moved to the Rejected directory"""
        print(f"Rejection detected: {filename}")
        file_path = self.rejected_dir / filename

        if file_path.exists():
            try:
                # Move rejected file to archive
                archive_dir = Path('vault') / 'Archive'
                archive_dir.mkdir(exist_ok=True)
                archive_path = archive_dir / f"REJECTED_{filename}"
                file_path.rename(archive_path)
            except Exception as e:
                print(f"Error processing rejected file {filename}: {e}")

    def parse_approval_file(self, content):
        """Parse the approval file to extract metadata"""
        try:
            lines = content.split('\n')
            parsed = {}
            body_start_index = -1
            yaml_started = False
            yaml_ended = False

            for i, line in enumerate(lines):
                line = line.strip()

                if line == '---':
                    if not yaml_started:
                        yaml_started = True
                        continue  # Skip first ---
                    elif yaml_started and not yaml_ended:
                        yaml_ended = True
                        body_start_index = i + 1
                        break

                if yaml_started and not yaml_ended and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]  # Remove single quotes
                        elif value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]  # Remove double quotes
                        parsed[key] = value

            if body_start_index != -1 and body_start_index < len(lines):
                parsed['body'] = '\n'.join(lines[body_start_index:]).strip()
            elif not yaml_ended and body_start_index == -1:
                # If no YAML frontmatter was found, treat all content as body
                parsed['body'] = content.strip()

            return parsed
        except Exception as e:
            print(f"Error parsing approval file: {e}")
            # Return a minimal valid structure for error handling
            return {"body": content, "action": "unknown", "to": "", "subject": ""}

    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_factor=2.0,
        exceptions=(HttpError, ConnectionError, socket.error)
    )
    def send_email(self, email_data):
        """Actually send the email using the email data"""
        print(f"Sending email to: {email_data.get('to')}, subject: {email_data.get('subject')}")

        # Log the attempt
        audit_logger.log_action(
            action_type="email_send_attempt",
            status="attempting",
            details={
                "to": email_data.get("to"),
                "subject": email_data.get("subject"),
                "attempt_number": getattr(self.send_email, 'attempt_number', 1)
            }
        )

        try:
            if not self.gmail_service:
                raise Exception("Gmail service not initialized. Make sure token.json exists.")

            to = email_data.get('to', '')
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')

            if not to or not subject:
                raise Exception("Missing required email fields: to or subject")

            # Get the user's email address from Gmail profile
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            sender = profile['emailAddress']

            # Create the email message
            message = self.create_message(sender, to, subject, body)
            if not message:
                raise Exception("Failed to create email message")

            # Send the email
            result = self.gmail_service.users().messages().send(
                userId='me',
                body=message
            )
            sent_message = result.execute()

            # Ensure the response has the expected format
            if not sent_message or 'id' not in sent_message:
                raise Exception(f"Invalid response from Gmail API: {sent_message}")

            print("Email sent successfully!")
            print(f'Message Id: {sent_message["id"]}')

            # Log the sent email to both local and audit logs
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "email_sent",
                "to": email_data.get("to"),
                "subject": email_data.get("subject"),
                "message_id": sent_message["id"],
                "status": "success"
            }

            # Store log in vault/Logs directory for clean structure
            vault_logs_path = Path('vault') / 'Logs'
            vault_logs_path.mkdir(parents=True, exist_ok=True)
            log_path = vault_logs_path / 'email_operations.json'
            logs = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            logs.append(log_entry)

            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)

            # Also log to comprehensive audit log
            audit_logger.log_success(
                action_type="email_sent",
                details={
                    "to": email_data.get("to"),
                    "subject": email_data.get("subject"),
                    "message_id": sent_message["id"]
                }
            )

        except Exception as e:
            error_msg = str(e)
            print(f"Error sending email: {e}")
            import traceback
            traceback.print_exc()

            # Log the failed email to both local and audit logs
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "email_send_failed",
                "to": email_data.get("to"),
                "subject": email_data.get("subject"),
                "error": error_msg,
                "status": "failed"
            }

            # Store log in vault/Logs directory for clean structure
            vault_logs_path = Path('vault') / 'Logs'
            vault_logs_path.mkdir(parents=True, exist_ok=True)
            log_path = vault_logs_path / 'email_operations.json'
            logs = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            logs.append(log_entry)

            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)

            # Also log to comprehensive audit log
            audit_logger.log_error(
                action_type="email_send_failed",
                error=error_msg,
                details={
                    "to": email_data.get("to"),
                    "subject": email_data.get("subject")
                }
            )

            # Re-raise the exception to trigger retry
            raise e

    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_factor=2.0,
        exceptions=(HttpError, ConnectionError, socket.error)
    )
    def draft_email(self, email_data):
        """Create an email draft using the email data"""
        print(f"Creating email draft for: {email_data.get('to')}, subject: {email_data.get('subject')}")

        # Log the attempt
        audit_logger.log_action(
            action_type="email_draft_attempt",
            status="attempting",
            details={
                "to": email_data.get("to"),
                "subject": email_data.get("subject"),
                "attempt_number": getattr(self.draft_email, 'attempt_number', 1)
            }
        )

        try:
            if not self.gmail_service:
                raise Exception("Gmail service not initialized. Make sure token.json exists.")

            to = email_data.get('to', '')
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')

            if not to or not subject:
                raise Exception("Missing required email fields: to or subject")

            # Get the user's email address from Gmail profile
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            sender = profile['emailAddress']

            # Create the email message
            message = self.create_message(sender, to, subject, body)
            if not message:
                raise Exception("Failed to create email message")

            # Create the draft
            result = self.gmail_service.users().drafts().create(
                userId='me',
                body={
                    'message': message
                }
            )
            draft = result.execute()

            # Ensure the response has the expected format
            if not draft or 'id' not in draft:
                raise Exception(f"Invalid response from Gmail API: {draft}")

            print("Email draft created successfully!")
            print(f'Draft Id: {draft["id"]}')

            # Log the draft email to both local and audit logs
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "email_draft_created",
                "to": email_data.get("to"),
                "subject": email_data.get("subject"),
                "draft_id": draft["id"],
                "status": "success"
            }

            # Store log in vault/Logs directory for clean structure
            vault_logs_path = Path('vault') / 'Logs'
            vault_logs_path.mkdir(parents=True, exist_ok=True)
            log_path = vault_logs_path / 'email_operations.json'
            logs = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            logs.append(log_entry)

            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)

            # Also log to comprehensive audit log
            audit_logger.log_success(
                action_type="email_draft_created",
                details={
                    "to": email_data.get("to"),
                    "subject": email_data.get("subject"),
                    "draft_id": draft["id"]
                }
            )

        except Exception as e:
            error_msg = str(e)
            print(f"Error creating email draft: {e}")
            import traceback
            traceback.print_exc()

            # Log the failed draft to both local and audit logs
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "email_draft_failed",
                "to": email_data.get("to"),
                "subject": email_data.get("subject"),
                "error": error_msg,
                "status": "failed"
            }

            # Store log in vault/Logs directory for clean structure
            vault_logs_path = Path('vault') / 'Logs'
            vault_logs_path.mkdir(parents=True, exist_ok=True)
            log_path = vault_logs_path / 'email_operations.json'
            logs = []
            if log_path.exists():
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            logs.append(log_entry)

            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)

            # Also log to comprehensive audit log
            audit_logger.log_error(
                action_type="email_draft_failed",
                error=error_msg,
                details={
                    "to": email_data.get("to"),
                    "subject": email_data.get("subject")
                }
            )

            # Re-raise the exception to trigger retry
            raise e

    def start(self):
        """Start the MCP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)

        self.running = True
        print(f"Email MCP Server listening on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
            except socket.error:
                if self.running:
                    print("Socket error occurred")
                break

    def handle_client(self, client_socket):
        """Handle communication with a client"""
        self.clients.add(client_socket)

        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break

                try:
                    request = json.loads(data.decode())
                    print(f"Received request: {request}")

                    response = self.process_request(request)
                    client_socket.send(json.dumps(response).encode() + b'\n')

                except json.JSONDecodeError:
                    error_response = {
                        "id": int(time.time() * 1000000) % 1000000,
                        "error": {"code": -32700, "message": "Parse error"}
                    }
                    client_socket.send(json.dumps(error_response).encode() + b'\n')
        except Exception as e:
            print(f"Client handling error: {e}")
        finally:
            client_socket.close()
            self.clients.discard(client_socket)

    def process_request(self, request):
        """Process individual requests"""
        method = request.get('method')

        try:
            if method == 'send_email':
                return self.handle_send_email(request.get('params', {}))
            elif method == 'draft_email':
                return self.handle_draft_email(request.get('params', {}))
            elif method == 'get_capabilities':
                return self.get_capabilities(request.get('id', 1))
            else:
                return {
                    "id": request.get('id', 1),
                    "error": {"code": -32601, "message": "Method not found"}
                }
        except Exception as e:
            return {
                "id": request.get('id', 1),
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }

    def handle_send_email(self, params):
        """Handle send_email request by creating a pending approval file"""
        email_id = int(time.time() * 1000)
        filename = f"EMAIL_{email_id}.md"
        file_path = self.pending_dir / filename

        content = f"""---
type: approval_request
action: send_email
to: {params.get('to', '')}
subject: {params.get('subject', '')}
created: {datetime.now().isoformat()}
---

{params.get('body', '')}"""

        file_path.write_text(content)

        return {
            "id": int(time.time() * 1000000) % 1000000,
            "result": {
                "success": True,
                "pending_approval": True,
                "approval_file": filename,
                "message": "Email requires approval before sending. Check Pending_Approval directory."
            }
        }

    def handle_draft_email(self, params):
        """Handle draft_email request by creating a pending approval file"""
        email_id = int(time.time() * 1000)
        filename = f"EMAIL_{email_id}.md"
        file_path = self.pending_dir / filename

        content = f"""---
type: approval_request
action: draft_email
to: {params.get('to', '')}
subject: {params.get('subject', '')}
created: {datetime.now().isoformat()}
---

{params.get('body', '')}"""

        file_path.write_text(content)

        return {
            "id": int(time.time() * 1000000) % 1000000,
            "result": {
                "success": True,
                "pending_approval": True,
                "approval_file": filename,
                "message": "Email draft requires approval before creation. Check Pending_Approval directory."
            }
        }

    def get_capabilities(self, request_id):
        """Return server capabilities"""
        return {
            "id": request_id,
            "result": {
                "name": "Email MCP Server",
                "version": "1.0.0",
                "description": "Email sending and drafting with human-in-the-loop approval",
                "capabilities": [
                    {
                        "name": "send_email",
                        "description": "Send an email that requires human approval",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string", "description": "Recipient email address"},
                                "subject": {"type": "string", "description": "Email subject"},
                                "body": {"type": "string", "description": "Email body content"}
                            },
                            "required": ["to", "subject", "body"]
                        }
                    },
                    {
                        "name": "draft_email",
                        "description": "Create an email draft that requires human approval",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string", "description": "Recipient email address"},
                                "subject": {"type": "string", "description": "Email subject"},
                                "body": {"type": "string", "description": "Email body content"}
                            },
                            "required": ["to", "subject", "body"]
                        }
                    }
                ]
            }
        }

    def stop(self):
        """Stop the server"""
        self.running = False

        # Close all client connections
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()

        # Close main socket
        if self.socket:
            self.socket.close()

        # Stop file system observer
        self.observer.stop()
        self.observer.join()

    def run(self):
        """Run the server in the main thread"""
        try:
            self.start()
        except KeyboardInterrupt:
            print("\nShutting down Email MCP Server...")
        finally:
            self.stop()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = EmailMCPServer(port=port)
    server.run()