---
name: Create Plan For Task
description: Create a plan file for a given task file
parameters:
  - name: filename
    type: string
    description: The name of the file to create a plan for
  - name: objective
    type: string
    description: The objective for the plan
returns:
  - type: object
    description: Object containing creation result
---

# Skill: Create Plan For Task

This skill creates a plan file for a given task in the vault root directory.

## Functionality
1. Takes a filename and objective as parameters
2. Creates a Plan_{filename}.md file in the vault root (or in /Plans folder if it exists)
3. Includes YAML frontmatter, objective, steps, and needed approvals/risks sections

## Python Implementation
```python
import os
from datetime import datetime
from pathlib import Path

def skill_create_plan_for_task(filename, objective):
    """
    Create a plan file for a given task
    :param filename: The name of the file to create a plan for
    :param objective: The objective for the plan
    """
    # Determine the output directory (use Plans folder if it exists, otherwise root)
    plans_dir = Path("./Plans")
    root_dir = Path(".")

    if plans_dir.exists():
        output_dir = plans_dir
    else:
        output_dir = root_dir

    # Create the plan filename
    name_part = Path(filename).stem if Path(filename).suffix else filename
    plan_filename = f"Plan_{name_part}.md"
    plan_path = output_dir / plan_filename

    # Create the plan content
    plan_content = f"""---
created_at: {datetime.now().isoformat()}
original_file: {filename}
status: pending
---

# Plan for {filename}

## Objective
{objective}

## Steps
- [ ] Review the original file and its contents
- [ ] Determine necessary actions based on file content
- [ ] Execute appropriate task processing
- [ ] Update any relevant records or systems
- [ ] Move file to Done when complete

## Needed Approvals or Risks
- Review required before execution
- Check Company_Handbook.md for rules of engagement
- Flag any payments > $100 or sensitive information for approval

## Notes
- Created automatically by AI Employee
- Review and customize as needed
"""

    # Write the plan file
    with open(plan_path, 'w', encoding='utf-8') as file:
        file.write(plan_content)

    return {
        "message": f"Plan created successfully for {filename}",
        "plan_file": str(plan_path),
        "objective": objective
    }

# Example usage
# result = skill_create_plan_for_task("test_invoice.pdf", "Process the invoice and flag for payment approval if under $100")
# print(result)
```

## Usage
Call this skill with a filename and objective to create a plan file for the task.