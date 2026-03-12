#!/usr/bin/env python3
"""
Ralph Wiggum Loop - Autonomous multi-step task completion system

This script implements a wrapper that keeps iterating until a task is complete.
It can use either promise-based completion (Claude outputs <promise>TASK_COMPLETE</promise>)
or file-based completion (moving task file to /Done when complete).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import re
import shutil


class RalphLoop:
    def __init__(self, max_iterations=10, log_file="vault/Logs/ralph_loop.json"):
        """
        Initialize the Ralph Wiggum loop with parameters

        Args:
            max_iterations (int): Maximum number of iterations to prevent infinite loops
            log_file (str): Path to the log file for each iteration
        """
        self.max_iterations = max_iterations
        self.log_file = log_file
        self.logs_dir = Path("vault/Logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Create log file if it doesn't exist
        self.log_path = Path(log_file)
        if not self.log_path.exists():
            self.log_path.write_text("[]")

    def log_iteration(self, iteration, prompt, output, status, task_file=None):
        """
        Log each iteration to the log file

        Args:
            iteration (int): Current iteration number
            prompt (str): The prompt that was sent
            output (str): The output received
            status (str): Status of the iteration
            task_file (str): Optional task file being processed
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "iteration": iteration,
            "prompt": prompt,
            "output": output,
            "status": status,
            "task_file": task_file
        }

        # Read existing logs
        if self.log_path.exists():
            with open(self.log_path, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        # Append new log entry
        logs.append(log_entry)

        # Write back to file
        with open(self.log_path, 'w') as f:
            json.dump(logs, f, indent=2)

    def check_promise_completion(self, output):
        """
        Check if the output contains the promise completion tag

        Args:
            output (str): The output from Claude

        Returns:
            bool: True if TASK_COMPLETE promise is found, False otherwise
        """
        # Look for <promise>TASK_COMPLETE</promise> pattern
        pattern = r'<promise>\s*TASK_COMPLETE\s*</promise>'
        return bool(re.search(pattern, output, re.IGNORECASE))

    def check_file_moved_to_done(self, original_file_path):
        """
        Check if the task file has been moved to the /Done directory

        Args:
            original_file_path (str): Path to the original task file

        Returns:
            bool: True if file is in /Done directory, False otherwise
        """
        original_path = Path(original_file_path)
        done_path = Path("vault/Done") / original_path.name

        return done_path.exists()

    def run_claude_with_prompt(self, prompt):
        """
        Execute Claude with the given prompt

        Args:
            prompt (str): The prompt to send to Claude

        Returns:
            str: The output from Claude
        """
        try:
            # Execute Claude Code with the prompt and capture output
            result = subprocess.run([
                "claude", "Code", prompt
            ], capture_output=True, text=True, timeout=300)  # 5 minute timeout

            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error running Claude: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Claude execution timed out after 5 minutes"
        except Exception as e:
            return f"Error running Claude: {str(e)}"

    def process_task_with_claude(self, task_prompt):
        """
        Process a task with Claude using the existing skills system

        Args:
            task_prompt (str): The prompt describing the task to process

        Returns:
            str: The output from Claude
        """
        # Use the existing Claude Code interface with comprehensive skill guidance
        full_prompt = f"""{task_prompt}

You are an AI Employee operating in autonomous mode. Please use the following existing skills as needed:

Bronze Tier Skills:
- SKILL_ScanNeedsAction.md: Scan the /Needs_Action folder for pending tasks
- SKILL_CreatePlanForTask.md: Create detailed plans for tasks
- SKILL_ProcessTaskFile.md: Process specific task files and move to /Done when complete
- SKILL_UpdateDashboard.md: Update the dashboard with status information

Silver/Gold Tier Skills:
- SKILL_TriageEmail.md: Categorize incoming emails
- SKILL_ProcessEmailForResponse.md: Determine email response strategy
- SKILL_RequestEmailApproval.md: Create approval requests for sensitive emails
- SKILL_MoveApprovedToArchived.md: Move approved files to archived for processing
- SKILL_PostToLinkedIn.md: Generate LinkedIn business updates
- SKILL_OdooDraftInvoice.md: Handle Odoo invoice creation with approval workflow
- SKILL_SocialPost.md: Handle social media posting with approval workflow

MCP Integration:
- All MCP operations (Odoo, Email, Social) require human approval before execution
- Sensitive operations should create approval requests in /Pending_Approval
- Monitor /Approved directory for approved items to process

Task Completion:
- For promise-based completion: Output <promise>TASK_COMPLETE</promise> when done
- For file-based completion: Ensure task files are moved to /Done directory
- Only mark complete when all related work is finished

Approach:
1. Analyze the current state of the system
2. Use appropriate skills to process the task
3. Follow the approval workflow where required
4. Log progress as needed
5. Check for completion conditions"""

        return self.run_claude_with_prompt(full_prompt)

    def run_loop(self, task_prompt, task_file=None):
        """
        Main loop that runs until the task is complete or max iterations reached

        Args:
            task_prompt (str): The initial prompt describing the task
            task_file (str): Optional path to the task file being processed

        Returns:
            dict: Final result with status and metrics
        """
        print(f"Starting Ralph Wiggum loop with max {self.max_iterations} iterations")
        print(f"Task: {task_prompt}")

        if task_file:
            print(f"Processing file: {task_file}")

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n--- Iteration {iteration} ---")

            # Run Claude with the current prompt
            output = self.process_task_with_claude(task_prompt)

            # Check for promise completion
            promise_complete = self.check_promise_completion(output)

            # Check for file-based completion if a task file was provided
            file_complete = False
            if task_file:
                file_complete = self.check_file_moved_to_done(task_file)

            # Determine if task is complete
            task_complete = promise_complete or file_complete

            # Log the iteration
            status = "completed" if task_complete else "running"
            self.log_iteration(iteration, task_prompt, output, status, task_file)

            print(f"Iteration {iteration} completed. Status: {status}")

            if task_complete:
                print(f"Task completed after {iteration} iterations!")

                if promise_complete:
                    print("Completion detected via promise tag: <promise>TASK_COMPLETE</promise>")
                if file_complete:
                    print(f"Completion detected via file movement: {task_file} moved to /Done")

                return {
                    "status": "completed",
                    "iterations": iteration,
                    "promise_complete": promise_complete,
                    "file_complete": file_complete,
                    "max_iterations_reached": False
                }

            # Small delay between iterations to avoid overwhelming the system
            time.sleep(2)

        # If we reach here, max iterations were reached without completion
        print(f"Max iterations ({self.max_iterations}) reached without task completion")

        self.log_iteration(
            self.max_iterations,
            task_prompt,
            "Max iterations reached without completion",
            "max_iterations_reached",
            task_file
        )

        return {
            "status": "incomplete",
            "iterations": self.max_iterations,
            "promise_complete": False,
            "file_complete": False,
            "max_iterations_reached": True
        }


def main():
    parser = argparse.ArgumentParser(description="Ralph Wiggum Loop - Autonomous multi-step task completion")
    parser.add_argument("prompt", help="The prompt describing the task to complete")
    parser.add_argument("--max-iterations", type=int, default=10,
                       help="Maximum number of iterations (default: 10)")
    parser.add_argument("--task-file", type=str,
                       help="Path to the task file to process (for file-based completion)")
    parser.add_argument("--log-file", type=str, default="vault/Logs/ralph_loop.json",
                       help="Path to the log file (default: vault/Logs/ralph_loop.json)")

    args = parser.parse_args()

    # Validate that Claude is available
    try:
        subprocess.run(["claude", "--version"],
                      capture_output=True, check=True, timeout=10)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("Error: Claude Code command not found. Please ensure Claude Code is installed and available in PATH.")
        sys.exit(1)

    # Create RalphLoop instance
    ralph = RalphLoop(max_iterations=args.max_iterations, log_file=args.log_file)

    # Run the loop
    result = ralph.run_loop(args.prompt, args.task_file)

    # Print final result
    print(f"\n--- Ralph Wiggum Loop Complete ---")
    print(f"Final Status: {result['status']}")
    print(f"Iterations executed: {result['iterations']}")
    print(f"Promise completion achieved: {result['promise_complete']}")
    print(f"File completion achieved: {result['file_complete']}")
    print(f"Max iterations reached: {result['max_iterations_reached']}")
    print(f"Logs saved to: {args.log_file}")


if __name__ == "__main__":
    main()