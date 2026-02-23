#!/usr/bin/env python3
"""
File System Watcher for AI Employee Vault

This script monitors the /Inbox folder in an AI Employee Vault and automatically
copies new files to /Needs_Action with companion metadata files.
"""

import argparse
import logging
import shutil
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class InboxEventHandler(FileSystemEventHandler):
    """
    Event handler for monitoring file creation in the Inbox folder.
    """

    def __init__(self, vault_path):
        """
        Initialize the event handler with the vault path.

        Args:
            vault_path (Path): Path to the AI Employee Vault
        """
        self.vault_path = Path(vault_path)
        self.inbox_path = self.vault_path / "Inbox"
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.logs_path = self.vault_path / "Logs"

        # Ensure Logs directory exists
        self.logs_path.mkdir(exist_ok=True)

        # Set up logging
        self.logger = logging.getLogger(__name__)

    def on_created(self, event):
        """
        Handle file creation events in the watched directory.

        Args:
            event: The file system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process files that are directly in the Inbox folder
        if file_path.parent == self.inbox_path:
            self.process_new_file(file_path)

    def on_moved(self, event):
        """
        Handle file move events in the watched directory.

        Args:
            event: The file system event
        """
        if event.is_directory:
            return

        file_path = Path(event.dest_path)  # Use dest_path for moves

        # Only process files that are moved into the Inbox folder
        if file_path.parent == self.inbox_path:
            self.process_new_file(file_path)

    def process_new_file(self, file_path):
        """
        Process a new file by copying it to Needs_Action and creating metadata.

        Args:
            file_path (Path): Path to the new file in Inbox
        """
        try:
            # Ensure the Needs_Action directory exists
            self.needs_action_path.mkdir(exist_ok=True)

            # Copy the original file to Needs_Action
            target_file_path = self.needs_action_path / file_path.name
            shutil.copy2(file_path, target_file_path)

            # Create metadata file
            metadata_filename = f"{file_path.stem}_metadata.md"
            metadata_file_path = self.needs_action_path / metadata_filename

            # Get file size
            file_size = file_path.stat().st_size

            # Generate timestamp with timezone
            timestamp = datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')
            # Format timezone part to include ':'
            if len(timestamp) > 5:
                timestamp = timestamp[:-2] + ':' + timestamp[-2:]

            # Create metadata content
            metadata_content = f"""---
type: file_drop
original_name: {file_path.name}
size_bytes: {file_size}
dropped_at: {timestamp}
status: pending
---
## File Drop Notification
New file ready for AI Employee processing.
"""

            # Write metadata file
            with open(metadata_file_path, 'w', encoding='utf-8') as f:
                f.write(metadata_content)

            # Create or append to the log file
            log_path = self.logs_path / "tasks_log.md"
            log_timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

            # Check if log file already exists
            log_exists = log_path.exists()
            with open(log_path, 'a', encoding='utf-8') as log_file:
                if not log_exists:
                    log_file.write("# AI Employee Logs\n\n## File Processing Log\n\n")

                log_file.write(f"### {file_path.name}\n")
                log_file.write(f"- **Received:** {log_timestamp} - File placed in Inbox\n")
                log_file.write(f"- **Status:** Pending\n")
                log_file.write(f"- **Summary:** File received and copied to Needs_Action for processing\n\n")

            # Log successful processing
            self.logger.info(f"New drop: {file_path.name} → copied to Needs_Action + metadata created + log entry added")

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")


def main():
    """
    Main function to run the file system watcher.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Monitor AI Employee Vault Inbox folder')
    parser.add_argument(
        '--vault-path',
        type=str,
        required=True,
        help='Absolute path to the AI Employee Vault'
    )

    args = parser.parse_args()

    # Validate vault path
    vault_path = Path(args.vault_path)
    if not vault_path.exists():
        print(f"Error: Vault path does not exist: {args.vault_path}")
        return 1

    inbox_path = vault_path / "Inbox"
    if not inbox_path.exists():
        print(f"Error: Inbox folder does not exist: {inbox_path}")
        return 1

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create event handler
    event_handler = InboxEventHandler(vault_path)

    # Create observer
    observer = Observer()
    observer.schedule(event_handler, str(inbox_path), recursive=False)

    # Start the observer
    observer.start()
    logging.info(f"Watching {inbox_path} for new files...")
    logging.info("Press Ctrl+C to stop.")

    try:
        # Keep the script running
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        # Handle graceful shutdown
        logging.info("Stopping file system watcher...")
        observer.stop()

    # Wait for observer to finish
    observer.join()
    logging.info("File system watcher stopped.")

    return 0


if __name__ == "__main__":
    exit(main())