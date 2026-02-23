---
name: Process Task File
description: Process a specific task file from Needs_Action folder
parameters:
  - name: filename
    type: string
    description: The name of the file to process (e.g. TEST_task.md)
returns:
  - type: object
    description: Object containing processing result
---

# Skill: Process Task File

This skill processes a specific task file from the `/Needs_Action` folder and moves it to `/Done` if complete.

## Functionality
1. Takes a filename as parameter
2. Reads the file from `/Needs_Action`
3. Checks if task is complete (looks for status: done or all checkboxes checked)
4. If complete, writes a log entry in `/Logs/tasks_log.md` and moves the file to `/Done`
5. If not complete, returns "Task not ready yet"

## Python Implementation
```python
import os
import shutil
from datetime import datetime

def skill_process_task_file(filename):
    """
    Process a specific task file from Needs_Action folder
    :param filename: The name of the file to process
    """
    needs_action_dir = "./Needs_Action"
    done_dir = "./Done"
    logs_dir = "./Logs"

    # Ensure the Logs directory exists
    os.makedirs(logs_dir, exist_ok=True)

    # Check if file exists in Needs_Action
    source_path = os.path.join(needs_action_dir, filename)
    if not os.path.exists(source_path):
        return {"error": f"File {filename} not found in Needs_Action folder"}

    # Read the file content
    with open(source_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Check if task is complete
    # Look for status: done or completed, or check if all checkboxes are checked
    is_complete = False

    # Check for status keywords in content
    content_lower = content.lower()
    if 'status: done' in content_lower or 'status: completed' in content_lower:
        is_complete = True

    # Check for unchecked checkboxes (if all are checked, then task is complete)
    unchecked_checkboxes = content.count('[ ]')
    checked_checkboxes = content.count('[x]')

    if unchecked_checkboxes == 0 and checked_checkboxes > 0:
        is_complete = True

    if is_complete:
        # Write log entry
        log_entry = f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}] Processed and completed task: {filename}\n"
        log_path = os.path.join(logs_dir, "tasks_log.md")

        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry)

        # Move file to Done folder
        destination_path = os.path.join(done_dir, filename)
        shutil.move(source_path, destination_path)

        return {
            "message": f"Task {filename} was complete and moved to Done folder",
            "action": "file_moved_to_done",
            "log_entry": log_entry.strip()
        }
    else:
        return {
            "message": "Task not ready yet",
            "action": "none_taken",
            "details": {
                "unchecked_boxes": unchecked_checkboxes,
                "checked_boxes": checked_checkboxes
            }
        }

# Example usage
# result = skill_process_task_file("example_task.md")
# print(result)
```

## Usage
Call this skill with a filename to process a specific task from the Needs_Action folder.