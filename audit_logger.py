import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

class AuditLogger:
    def __init__(self, log_file: str = "vault/Logs/full_audit.json"):
        """Initialize the audit logger."""
        self.log_file = log_file
        # Ensure log directory exists
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Set up standard Python logging as well
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "application.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def log_action(self,
                   action_type: str,
                   status: str,
                   details: Dict[str, Any],
                   error: Optional[str] = None,
                   user_id: Optional[str] = None,
                   session_id: Optional[str] = None):
        """
        Log an action to the audit log in JSONL format.

        Args:
            action_type: Type of action (e.g., 'email_send', 'odoo_invoice', 'social_post')
            status: Status of the action ('success', 'error', 'retrying', 'skipped', etc.)
            details: Additional details about the action
            error: Error message if any
            user_id: ID of the user triggering the action
            session_id: Session ID for grouping related actions
        """
        timestamp = datetime.utcnow().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "action_type": action_type,
            "status": status,
            "details": details,
            "error": error,
            "user_id": user_id,
            "session_id": session_id
        }

        # Write as JSONL (JSON Lines format) - ensure the log file has .jsonl extension for clarity
        if not self.log_file.endswith('.jsonl'):
            # Create a new file path for the full audit log with correct extension
            base_path = Path(self.log_file)
            jsonl_path = base_path.parent / "full_audit.jsonl"
            log_file = str(jsonl_path)
        else:
            log_file = self.log_file

        # Write as JSONL (JSON Lines format)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Also log to standard logger
        log_msg = f"{action_type} - {status}"
        if error:
            log_msg += f" - Error: {error}"
        self.logger.info(f"{log_msg} - Details: {details}")

    def log_retry(self,
                  action_type: str,
                  attempt: int,
                  max_attempts: int,
                  error: str,
                  details: Dict[str, Any] = None):
        """Log a retry attempt."""
        self.log_action(
            action_type=action_type,
            status="retrying",
            details={
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error": error,
                **(details or {})
            },
            error=error
        )

    def log_error(self,
                  action_type: str,
                  error: str,
                  details: Dict[str, Any] = None,
                  user_id: Optional[str] = None,
                  session_id: Optional[str] = None):
        """Log an error action."""
        self.log_action(
            action_type=action_type,
            status="error",
            details=details or {},
            error=error,
            user_id=user_id,
            session_id=session_id
        )

    def log_success(self,
                    action_type: str,
                    details: Dict[str, Any] = None,
                    user_id: Optional[str] = None,
                    session_id: Optional[str] = None):
        """Log a successful action."""
        self.log_action(
            action_type=action_type,
            status="success",
            details=details or {},
            user_id=user_id,
            session_id=session_id
        )

    def log_warning(self,
                    action_type: str,
                    warning: str,
                    details: Dict[str, Any] = None):
        """Log a warning action."""
        self.log_action(
            action_type=action_type,
            status="warning",
            details=details or {},
            error=warning
        )

# Global logger instance
audit_logger = AuditLogger()