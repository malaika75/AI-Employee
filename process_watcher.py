#!/usr/bin/env python3
"""
Process Watcher - Monitors the AI Employee Vault for changes and triggers the daily process

This script watches the vault directories for changes and automatically runs the
daily_claude_run.bat file when changes are detected that might require processing.
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class ProcessEventHandler(FileSystemEventHandler):
    """
    Event handler for monitoring file changes in the vault that should trigger the process.
    """

    def __init__(self, vault_path, batch_file_path):
        """
        Initialize the event handler with vault path and batch file path.

        Args:
            vault_path (Path): Path to the AI Employee Vault
            batch_file_path (Path): Path to the daily_claude_run.bat file
        """
        self.vault_path = Path(vault_path)
        self.batch_file_path = Path(batch_file_path)
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.approved_path = self.vault_path / "Approved"
        self.inbox_path = self.vault_path / "Inbox"

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Track last execution time to prevent multiple rapid executions
        self.last_execution = 0
        self.execution_cooldown = 30  # 30 seconds cooldown

    def should_trigger_process(self, file_path):
        """
        Determine if a file change should trigger the process.

        Args:
            file_path (Path): Path of the changed file

        Returns:
            bool: True if process should be triggered
        """
        # Check if the file is in a directory that should trigger processing
        parent_dir = file_path.parent

        # Trigger if file is added to Needs_Action, Inbox, or Approved folders
        if parent_dir == self.needs_action_path or \
           parent_dir == self.inbox_path or \
           parent_dir == self.approved_path:
            return True

        # Also trigger if it's a file being added to any of these directories
        if parent_dir.name in ['Needs_Action', 'Inbox', 'Approved']:
            return True

        return False

    def on_created(self, event):
        """
        Handle file creation events.

        Args:
            event: The file system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if self.should_trigger_process(file_path):
            self.trigger_process(file_path, "created")

    def on_moved(self, event):
        """
        Handle file move events.

        Args:
            event: The file system event
        """
        if event.is_directory:
            return

        # Use dest_path for moved files
        file_path = Path(event.dest_path)

        if self.should_trigger_process(file_path):
            self.trigger_process(file_path, "moved")

    def trigger_process(self, file_path, event_type):
        """
        Trigger the daily process execution.

        Args:
            file_path (Path): Path of the file that triggered the event
            event_type (str): Type of event (created/moved)
        """
        current_time = time.time()

        # Check if enough time has passed since last execution
        if current_time - self.last_execution < self.execution_cooldown:
            self.logger.info(f"Process execution skipped due to cooldown: {file_path.name}")
            return

        self.last_execution = current_time

        try:
            self.logger.info(f"File {event_type}: {file_path.name} - Triggering daily process...")

            # Execute the batch file
            result = subprocess.run(
                [str(self.batch_file_path)],
                cwd=str(self.vault_path.parent),  # Run from the parent directory of the vault
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                self.logger.info(f"Process completed successfully for {file_path.name}")
            else:
                self.logger.error(f"Process failed for {file_path.name}: {result.stderr}")

        except subprocess.TimeoutExpired:
            self.logger.error(f"Process timed out for {file_path.name}")
        except Exception as e:
            self.logger.error(f"Error running process for {file_path.name}: {str(e)}")


def main():
    """Main function to run the process watcher"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Define paths
    script_dir = Path(__file__).parent
    vault_path = script_dir / "vault"
    batch_file_path = script_dir / "daily_claude_run.bat"

    # Validate paths
    if not vault_path.exists():
        logging.error(f"Vault path does not exist: {vault_path}")
        return 1

    if not batch_file_path.exists():
        logging.error(f"Batch file does not exist: {batch_file_path}")
        return 1

    # Create event handler
    event_handler = ProcessEventHandler(vault_path, batch_file_path)

    # Create observer
    observer = Observer()

    # Watch the entire vault directory for changes
    observer.schedule(event_handler, str(vault_path), recursive=True)

    # Start the observer
    observer.start()
    logging.info(f"Process Watcher started - monitoring {vault_path} for changes...")
    logging.info("Process will trigger when files are added to Needs_Action, Inbox, or Approved folders")
    logging.info("Press Ctrl+C to stop.")

    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Handle graceful shutdown
        logging.info("Stopping process watcher...")
        observer.stop()

    # Wait for observer to finish
    observer.join()
    logging.info("Process watcher stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())