---
name: Update Dashboard
description: Update the Dashboard.md file with a new activity entry
parameters:
  - name: message
    type: string
    description: The message to add to the Recent Activity section
returns:
  - type: object
    description: Object containing update result
---

# Skill: Update Dashboard

This skill updates the Dashboard.md file by adding a new entry to the "Recent Activity" section.

## Functionality
1. Takes a message as parameter
2. Reads Dashboard.md
3. Finds or creates the "## Recent Activity" section
4. Appends a new line: "- [YYYY-MM-DDTHH:MM:SSZ] Message here"
5. Saves the file

## Python Implementation
```python
import os
from datetime import datetime

def skill_update_dashboard(message):
    """
    Update Dashboard.md with a new activity entry
    :param message: The message to add to Recent Activity
    """
    dashboard_path = "./Dashboard.md"

    # If Dashboard.md doesn't exist, create a basic one
    if not os.path.exists(dashboard_path):
        with open(dashboard_path, 'w', encoding='utf-8') as file:
            file.write(f"""# 🤖 Personal AI Employee Dashboard

## Current Status
- **AI Employee**: [CONNECTED/DISCONNECTED]
- **Last Action**: [Pending]
- **Tasks Completed Today**: 0
- **Tasks Pending**: 0

## Recent Activity
- [{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}] Dashboard initialized

## Pending Items
- [No pending items]

## AI Employee Health
- **Status**: Operational
- **Memory Usage**: [N/A]
- **Response Time**: [N/A]
- **Last Check-in**: [N/A]
""")

    # Read the current dashboard content
    with open(dashboard_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Create the new activity entry
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    new_entry = f"- [{timestamp}] {message}"

    # Check if Recent Activity section exists
    if "## Recent Activity" in content:
        # Insert the new entry right after the ## Recent Activity header
        lines = content.splitlines()
        new_lines = []
        inserted = False

        for line in lines:
            new_lines.append(line)
            if line.strip() == "## Recent Activity" and not inserted:
                new_lines.append(new_entry)
                inserted = True

        updated_content = '\n'.join(new_lines)
    else:
        # If no Recent Activity section exists, add it
        updated_content = content + f"\n\n## Recent Activity\n{new_entry}\n"

    # Write the updated content back to the file
    with open(dashboard_path, 'w', encoding='utf-8') as file:
        file.write(updated_content)

    return {
        "message": "Dashboard updated successfully",
        "entry": new_entry,
        "file_path": dashboard_path
    }

# Example usage
# result = skill_update_dashboard("Completed task processing")
# print(result)
```

## Usage
Call this skill with a message to add an entry to the Dashboard's Recent Activity section.