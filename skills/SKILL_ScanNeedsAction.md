---
name: Scan Needs_Action Folder
description: List all .md files in /Needs_Action folder and provide short summaries
parameters:
  - name: none
    type: null
    description: This skill takes no parameters
returns:
  - type: object
    description: Object containing file list and summaries
---

# Skill: Scan Needs_Action Folder

This skill scans the `/Needs_Action` folder and lists all `.md` files with brief summaries.

## Functionality
1. Lists all `.md` files in the `/Needs_Action` folder
2. Reads each file to provide a short summary
3. Shows YAML frontmatter if present

## Python Implementation
```python
import os
from datetime import datetime

def skill_scan_needs_action():
    """Scan the Needs_Action folder for .md files and summarize their content"""
    needs_action_dir = "./Needs_Action"
    results = []

    if not os.path.exists(needs_action_dir):
        return {"message": "Needs_Action folder does not exist", "files": []}

    for filename in os.listdir(needs_action_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(needs_action_dir, filename)

            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()

                # Extract YAML frontmatter if present
                yaml_frontmatter = ""
                content_without_frontmatter = content
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        yaml_frontmatter = parts[1]
                        content_without_frontmatter = parts[2]

                # Create a short summary (first 100 characters after YAML)
                summary = content_without_frontmatter.strip()
                if len(summary) > 100:
                    summary = summary[:100] + "..."

                file_info = {
                    "filename": filename,
                    "summary": summary,
                    "yaml_frontmatter": yaml_frontmatter
                }
                results.append(file_info)

            except Exception as e:
                results.append({
                    "filename": filename,
                    "summary": f"Error reading file: {str(e)}",
                    "yaml_frontmatter": ""
                })

    return {
        "message": f"Found {len(results)} .md files in Needs_Action folder",
        "files": results
    }

# Execute the skill
result = skill_scan_needs_action()
print(f"Status: {result['message']}")
for file_info in result['files']:
    print(f"- {file_info['filename']}: {file_info['summary']}")
```

## Usage
Run this skill to see all pending tasks that need action.