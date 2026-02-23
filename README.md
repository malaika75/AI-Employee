# Personal AI Employee - Bronze Tier

This is a local-first AI employee implementation using Claude Code with file-based operations.

## Folder Structure
```
/Inbox
/Needs_Action
/Done
/Logs
/Plans
Dashboard.md
Company_Handbook.md
Skills/
  SKILL_ScanNeedsAction.md
  SKILL_ProcessTaskFile.md
  SKILL_UpdateDashboard.md
  SKILL_CreatePlanForTask.md
filesystem_watcher.py
ai_employee.py
```

## Available Skills

### 1. SKILL_ScanNeedsAction.md
Scans the `/Needs_Action` folder and lists all `.md` files with brief summaries.

**Usage:**
```bash
python ai_employee.py scan-needs-action
```

### 2. SKILL_ProcessTaskFile.md
Processes a specific task file from `/Needs_Action` and moves it to `/Done` if complete.
You would run Claude commands like:
  # After a file is detected in Needs_Action by the watcher
  claude "Please check the Needs_Action folder using the 'Scan Needs_Action Folder' skill, then create plans for any new tasks using the 'Create Plan For Task' skill."

  # After plans are created, to process them
  claude "Please process the task files in Needs_Action using the 'Process Task File' skill, then update the dashboard with 'Update Dashboard' skill."

**Usage:**
```bash
python ai_employee.py process-task-file <filename>
```

### 3. SKILL_UpdateDashboard.md
Updates the Dashboard.md file with a new activity entry.

**Usage:**
```bash
python ai_employee.py update-dashboard "Your message here"
```

### 4. SKILL_CreatePlanForTask.md
Creates a plan file for a given task in the `/Plans` folder.

**Usage:**
```bash
python ai_employee.py create-plan-for-task <filename> <objective>
```

## File System Watcher

The `filesystem_watcher.py` script monitors the `/Inbox` folder and automatically:
1. Copies new files to `/Needs_Action`
2. Creates companion metadata files in `/Needs_Action`
3. Logs activity to the console

**Setup:**
```bash
pip install watchdog
```

**Usage:**
```bash
python filesystem_watcher.py --vault-path "/path/to/AI_Employee_Vault"
```

## How It Works

1. Place task files in the `/Inbox` folder
2. The file system watcher automatically copies files to `/Needs_Action` with metadata
3. Use the skills to process tasks:
   - Scan `/Needs_Action` for new items
   - Create plans using `SKILL_CreatePlanForTask.md`
   - Process tasks when ready
4. Completed tasks are moved to `/Done`
5. Activity is logged in `/Logs`
6. Dashboard is updated with recent activity

## End-to-End Bronze Tier Workflow

1. **Start the watcher:**
   ```bash
   python filesystem_watcher.py --vault-path "/path/to/AI_Employee_Vault"
   ```

2. **Drop a file in /Inbox:** Place any file in the Inbox folder

3. **Observe automatic processing:** The watcher creates a copy in `/Needs_Action` with metadata

4. **Create a plan:** Use Claude Code to create a plan for the new task
   ```bash
   claude --cwd "/path/to/vault" --message "New file dropped. Scan Needs_Action folder and create a plan for the new task."
   ```

5. **Process the task:** When the task is complete, move it to `/Done`

6. **Update dashboard:** Log the activity in the dashboard

All operations are performed locally using Python file operations.