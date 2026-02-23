"""
AI Employee Skill Executor
This script allows you to run the AI Employee skills from the command line
"""

import importlib.util
import sys
import os
from datetime import datetime


def execute_skill(skill_name, **kwargs):
    """
    Execute a skill from the Skills folder
    """
    skill_file = f"Skills/SKILL_{skill_name}.md"

    if not os.path.exists(skill_file):
        print(f"Error: Skill file {skill_file} not found")
        return None

    with open(skill_file, 'r', encoding='utf-8') as file:
        content = file.read()

    # Find the Python code block
    lines = content.splitlines()
    python_code = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith('```python'):
            in_code_block = True
            continue
        elif line.strip().startswith('```') and in_code_block:
            in_code_block = False
            continue

        if in_code_block:
            python_code.append(line)

    if not python_code:
        print(f"Error: No Python code found in {skill_file}")
        return None

    # Execute in a namespace that includes required imports
    namespace = {
        'os': __import__('os'),
        'datetime': __import__('datetime').datetime,
        'Path': __import__('pathlib').Path
    }

    # Join and execute the code in the namespace
    exec('\n'.join(python_code), namespace)

    # Add the function execution based on skill name and parameters
    if skill_name == "ScanNeedsAction":
        namespace['result'] = namespace['skill_scan_needs_action']()
        print(namespace['result'])
    elif skill_name == "ProcessTaskFile":
        if "filename" not in kwargs:
            print("Error: filename parameter required for ProcessTaskFile skill")
            return None
        namespace['result'] = namespace['skill_process_task_file'](kwargs['filename'])
        print(namespace['result'])
    elif skill_name == "UpdateDashboard":
        if "message" not in kwargs:
            print("Error: message parameter required for UpdateDashboard skill")
            return None
        namespace['result'] = namespace['skill_update_dashboard'](kwargs['message'])
        print(namespace['result'])
    elif skill_name == "CreatePlanForTask":
        if "filename" not in kwargs or "objective" not in kwargs:
            print("Error: filename and objective parameters required for CreatePlanForTask skill")
            return None
        namespace['result'] = namespace['skill_create_plan_for_task'](kwargs['filename'], kwargs['objective'])
        print(namespace['result'])


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ai_employee.py scan-needs-action")
        print("  python ai_employee.py process-task-file <filename>")
        print("  python ai_employee.py update-dashboard <message>")
        print("  python ai_employee.py create-plan-for-task <filename> <objective>")
        return

    command = sys.argv[1]

    if command == "scan-needs-action":
        execute_skill("ScanNeedsAction")
    elif command == "process-task-file":
        if len(sys.argv) < 3:
            print("Error: Please provide a filename")
            return
        filename = sys.argv[2]
        execute_skill("ProcessTaskFile", filename=filename)
    elif command == "update-dashboard":
        if len(sys.argv) < 3:
            print("Error: Please provide a message")
            return
        message = ' '.join(sys.argv[2:])
        execute_skill("UpdateDashboard", message=message)
    elif command == "create-plan-for-task":
        if len(sys.argv) < 4:
            print("Error: Please provide both filename and objective")
            return
        filename = sys.argv[2]
        objective = ' '.join(sys.argv[3:])
        execute_skill("CreatePlanForTask", filename=filename, objective=objective)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: scan-needs-action, process-task-file, update-dashboard, create-plan-for-task")


if __name__ == "__main__":
    main()