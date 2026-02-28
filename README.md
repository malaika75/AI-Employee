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

## Bronze Tier - How It Works (Minimized)

1. Place task files in the `/Inbox` folder
2. The file system watcher automatically copies files to `/Needs_Action` with metadata
3. Use the skills to process tasks:
   - Scan `/Needs_Action` for new items
   - Create plans using `SKILL_CreatePlanForTask.md`
   - Process tasks when ready
4. Completed tasks are moved to `/Done`
5. Activity is logged in `/Logs`
6. Dashboard is updated with recent activity

---

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


# Personal AI Employee - Silver Tier

Enhanced functionality with Gmail integration and human-in-the-loop approval system.

## New Folder Structure
```
/Inbox
/Needs_Action
/Done
/Logs
/Plans
/Drafts
/vault
  /Approved
  /Rejected
  /Pending_Approval
  /Archive
Dashboard.md
Company_Handbook.md
Skills/
  SKILL_ScanNeedsAction.md
  SKILL_ProcessTaskFile.md
  SKILL_UpdateDashboard.md
  SKILL_CreatePlanForTask.md
  SKILL_TriageEmail.md
  SKILL_RequestEmailApproval.md
  SKILL_ProcessEmailForResponse.md
  SKILL_MoveApprovedToArchived.md
  SKILL_PostToLinkedIn.md
  SKILL_ScanNeedsAction.md
  SKILL_CreatePlanForTask.md
filesystem_watcher.py
gmail_watcher.py
process_watcher.py
start_processes.py
start_all_processes.bat
email_mcp.py
daily_claude_run.bat
mcp.json
```

## Silver Tier Features

### 1. Gmail Integration
- **Gmail Watcher (`gmail_watcher.py`)**: Monitors Gmail inbox for new emails and processes them
- Automatically categorizes emails using Claude Code
- Creates appropriate task files in the `/Inbox` or `/Needs_Action` folder
- Requires Gmail API credentials and OAuth setup

**Setup:**
```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 python-frontmatter pathlib
```

**Usage:**
```bash
python gmail_watcher.py --credentials credentials.json --token token.json
```

### 2. Human-in-the-Loop Email Approval System
- **Email MCP Server (`email_mcp.py`)**: Handles email-related actions with human approval
- **Approval Flow**:
  - When requesting to send/draft email, creates a pending approval file in `/Pending_Approval`
  - User must manually move file to `/Approved` to execute or `/Rejected` to cancel
  - Server monitors approval directories and processes accordingly
- **Skills for Email Actions**:
  - `SKILL_RequestEmailApproval.md`: Creates approval request files instead of sending emails directly

**MCP Configuration:**
- Server runs with `python email_mcp.py`
- Configured via `mcp.json` file
- Exposes `send_email` and `draft_email` capabilities

**Approval File Format:**
```
---
type: approval_request
action: send_email  # or draft_email
to: recipient@example.com
subject: Email Subject
created: 2026-02-24T10:30:00Z
---

Email body content here...
```

### 3. New Skills

#### SKILL_TriageEmail.md
Processes incoming emails and categorizes them based on content and sender.

#### SKILL_RequestEmailApproval.md
Handles sending or drafting emails with human-in-the-loop approval. Instead of sending emails directly, creates a pending approval file in the `/Pending_Approval` directory.

#### SKILL_ProcessEmailForResponse.md
Intelligently processes emails from `/Needs_Action` and determines the appropriate response:
- **Sensitive emails** (containing payment, invoice, urgent, confidential, etc.): Creates approval request in `/Pending_Approval`
- **Normal emails**: Crafts contextual response and places directly in `/Archived` for MCP to send
- **No-reply emails** (spam, newsletters): Moves directly to `/Done`

#### SKILL_MoveApprovedToArchived.md
Moves approved files from `/Approved` to `/Archived` after human review, making them ready for MCP server to send.

#### SKILL_PostToLinkedIn.md
Generates professional LinkedIn updates based on business activities, achievements, or insights. Creates draft posts in `/Drafts` with approval requests in `/Pending_Approval`.

#### SKILL_CreatePlanForTask.md
Creates structured plan files for each task to ensure thorough processing.

### 4. Process Automation and Monitoring
- **Process Watcher (`process_watcher.py`)**: Monitors vault changes and triggers automated processes
- **File System Watcher (`filesystem_watcher.py`)**: Monitors Inbox for new files
- **Start Scripts**: `start_processes.py` and `start_all_processes.bat` to launch all components
- **Daily Process (`daily_claude_run.bat`)**: Automates routine tasks including email processing, LinkedIn drafts, and logging

### 5. LinkedIn Integration
- **SKILL_PostToLinkedIn.md**: Generates professional LinkedIn updates based on business activities
- Creates draft posts in `/Drafts` with approval requests in `/Pending_Approval`

## Claude Prompts for Email Processing Workflow

To implement the complete email processing workflow with Claude Code, use these prompts:

### For processing new emails in `/Needs_Action`:
```
Process all EMAIL_*.md files in `/Needs_Action` using SKILL_ProcessEmailForResponse.md.
For each email:
1. Read content, sender, and subject
2. Determine if sensitive (payment, invoice, urgent, confidential) or normal
3. If sensitive: create approval file in `/Pending_Approval`
4. If normal: create response file in `/Archived` with Claude's crafted contextual response
5. If spam/newsletter: move to `/Done`
```

### For handling approved emails:
```
Monitor `/Approved` folder. For any file there:
1. Use SKILL_MoveApprovedToArchived.md to move file to `/Archived`
2. MCP server will automatically send the email from `/Archived`
3. After sending confirmed, move original email from `/Needs_Action` to `/Done`
4. Create log entry in `/Logs`
```

### For direct email processing:
```
For normal emails that don't need approval:
1. Read the original email from `/Needs_Action`
2. Generate contextual response personalized to sender and content
3. Create file in `/Archived` with YAML frontmatter:
   ---
   type: email_response
   action: send_email
   to: [original sender]
   subject: Re: [original subject]
   created: [timestamp]
   ---

   [Claude's contextual response crafted based on original email]
4. MCP server monitors `/Archived` and will automatically send the email
5. Move original email to `/Done` and create log in `/Logs`
```

## Setup for Silver Tier

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Gmail Watcher:**
   - Set up Google API credentials (follow GMAIL_WATCHER_SETUP.md)
   - Obtain OAuth token (first run will prompt for authorization)

3. **Start MCP Server:**
   ```bash
   python email_mcp.py &
   ```

4. **Run Complete System:**
   ```bash
   # Method 1: Using Python script
   python start_processes.py

   # Method 2: Using batch file
   start_all_processes.bat

   # Method 3: Manual start (alternative)
   python email_mcp.py &
   python gmail_watcher.py --vault-path ./vault &
   python filesystem_watcher.py --vault-path ./vault &
   python process_watcher.py --vault-path ./vault &
   ```

## Silver Tier Workflow

### Email Processing Flow:
1. **Gmail Watcher** monitors your Gmail inbox continuously
2. New emails trigger `SKILL_TriageEmail.md` to categorize them
3. Categorized emails create tasks in `/Needs_Action`
4. **Process Watcher** automatically triggers the daily process when new emails are detected
5. AI Employee processes email-based tasks according to sensitivity level

### Email Sending Flow (Human-in-the-Loop):
1. When AI Employee needs to send/draft email, it uses `SKILL_RequestEmailApproval.md`
2. Instead of sending directly, creates approval file as `EMAIL_{timestamp}.md` in `/Pending_Approval`
3. **Human review**: User moves file to `/Approved` (to execute) or `/Rejected` (to cancel)
4. **Email MCP Server** monitors approval directories and processes accordingly
5. If approved, email is sent/drafted; results logged to `email_log.json`
6. Processed files moved to `/Archive`

### Daily Automation Flow:
1. **Process Watcher** monitors changes in vault directories
2. When files are added to `/Needs_Action`, `/Inbox`, or `/Approved`, triggers `daily_claude_run.bat`
3. **Daily Process** executes comprehensive workflow:
   - Scans all pending tasks
   - Creates plans for each task
   - Processes emails appropriately
   - Generates LinkedIn drafts
   - Updates dashboard and logs

## End-to-End Silver Tier Workflow

1. **Setup:**
   ```bash
   # Install dependencies
   pip install -r requirements.txt

   # Configure Gmail (first time only)
   # Follow instructions in GMAIL_WATCHER_SETUP.md

   # Start complete AI Employee system
   python start_processes.py
   # OR
   start_all_processes.bat
   ```

2. **Email Monitoring:** Gmail Watcher continuously monitors your inbox

3. **Email Processing:** New emails are automatically categorized and processed as tasks

4. **Email Sending (Human-in-the-Loop):** When AI needs to send an email:
   - Creates `EMAIL_{timestamp}.md` in `/Pending_Approval`
   - You review and approve/reject by moving to appropriate folder
   - MCP Server processes the approval action

5. **Daily Automation:** Process Watcher triggers daily routines automatically

6. **LinkedIn Updates:** Automatic LinkedIn draft generation based on business activities

7. **Complete Logging:** All activities logged in `/Logs` with timestamps

All operations maintain security through human oversight for sensitive actions while providing full automation for routine tasks. The system operates continuously, handling email processing, task management, and business updates automatically.