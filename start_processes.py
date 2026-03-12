#!/usr/bin/env python3
"""
Start All AI Employee Processes

This script starts all required AI Employee processes as background subprocesses.
"""

import os
import sys
import time
import subprocess
import logging
import signal
from pathlib import Path
from datetime import datetime
import threading

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('vault/Logs/process_log.txt', mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def start_process_watcher():
    """Start the process watcher"""
    try:
        process = subprocess.Popen([
            sys.executable, 'process_watcher.py'
        ], cwd='.')
        logging.info("Process Watcher started with PID: {}".format(process.pid))
        return process
    except Exception as e:
        logging.error(f"Failed to start Process Watcher: {e}")
        return None

def start_filesystem_watcher():
    """Start the filesystem watcher"""
    try:
        process = subprocess.Popen([
            sys.executable, 'filesystem_watcher.py', '--vault-path', 'vault'
        ], cwd='.')
        logging.info("Filesystem Watcher started with PID: {}".format(process.pid))
        return process
    except Exception as e:
        logging.error(f"Failed to start Filesystem Watcher: {e}")
        return None

def start_gmail_watcher():
    """Start the gmail watcher"""
    try:
        process = subprocess.Popen([
            sys.executable, 'gmail_watcher.py', '--vault-path', 'vault'
        ], cwd='.')
        logging.info("Gmail Watcher started with PID: {}".format(process.pid))
        return process
    except Exception as e:
        logging.error(f"Failed to start Gmail Watcher: {e}")
        return None

def start_email_mcp():
    """Start the email MCP server"""
    try:
        process = subprocess.Popen([
            sys.executable, 'email_mcp.py'
        ], cwd='.')
        logging.info("Email MCP Server started with PID: {}".format(process.pid))
        return process
    except Exception as e:
        logging.error(f"Failed to start Email MCP Server: {e}")
        return None

def start_odoo_mcp():
    """Start the odoo MCP server"""
    try:
        process = subprocess.Popen([
            sys.executable, 'odoo_mcp.py', '--vault-path', 'odoo_vault.json'
        ], cwd='.')
        logging.info("Odoo MCP Server started with PID: {}".format(process.pid))
        return process
    except Exception as e:
        logging.error(f"Failed to start Odoo MCP Server: {e}")
        return None

def start_social_mcp():
    """Start the social MCP server"""
    try:
        process = subprocess.Popen([
            sys.executable, 'social_mcp.py'
        ], cwd='.')
        logging.info("Social MCP Server started with PID: {}".format(process.pid))
        return process
    except Exception as e:
        logging.error(f"Failed to start Social MCP Server: {e}")
        return None

def signal_handler(signum, frame, processes):
    """Handle shutdown signals"""
    logging.info("Shutdown signal received. Terminating processes...")
    for process in processes:
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    logging.info("All processes terminated.")
    sys.exit(0)

def main():
    """Main function to start all processes"""
    setup_logging()
    logging.info("Starting all AI Employee processes...")

    # Store process references
    processes = []

    # Start all processes
    process_watcher = start_process_watcher()
    if process_watcher:
        processes.append(process_watcher)

    time.sleep(1)  # Brief pause between starting processes

    filesystem_watcher = start_filesystem_watcher()
    if filesystem_watcher:
        processes.append(filesystem_watcher)

    time.sleep(1)  # Brief pause between starting processes

    gmail_watcher = start_gmail_watcher()
    if gmail_watcher:
        processes.append(gmail_watcher)

    time.sleep(1)  # Brief pause between starting processes

    email_mcp = start_email_mcp()
    if email_mcp:
        processes.append(email_mcp)

    time.sleep(1)  # Brief pause between starting processes

    odoo_mcp = start_odoo_mcp()
    if odoo_mcp:
        processes.append(odoo_mcp)

    time.sleep(1)  # Brief pause between starting processes

    social_mcp = start_social_mcp()
    if social_mcp:
        processes.append(social_mcp)

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, processes))
    signal.signal(signal.SIGTERM, lambda sig, frame: signal_handler(sig, frame, processes))

    expected_processes = 6  # process_watcher, filesystem_watcher, gmail_watcher, email_mcp, odoo_mcp, social_mcp
    if len(processes) == expected_processes:
        logging.info("All processes started successfully!")
        logging.info("Processes are running in the background.")
        logging.info("Press Ctrl+C to stop all processes.")

        try:
            # Monitor processes and restart if needed
            while True:
                for i, process in enumerate(processes):
                    if process and process.poll() is not None:
                        logging.warning(f"Process {i+1} has exited with code {process.returncode}")
                        # Restart the process
                        if i == 0:
                            processes[i] = start_process_watcher()
                        elif i == 1:
                            processes[i] = start_filesystem_watcher()
                        elif i == 2:
                            processes[i] = start_gmail_watcher()
                        elif i == 3:
                            processes[i] = start_email_mcp()
                        elif i == 4:
                            processes[i] = start_odoo_mcp()
                        elif i == 5:
                            processes[i] = start_social_mcp()

                time.sleep(10)  # Check every 10 seconds
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None, processes)
    else:
        logging.error("Failed to start all processes. Exiting.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())