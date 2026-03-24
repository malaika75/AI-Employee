# Personal AI Employee - Multi-Tier System

A comprehensive AI employee automation system with Bronze, Silver, Gold, and Platinum tiers.

## 📋 System Overview

This project implements an AI-powered employee that handles:
- 📧 Email triage and responses (Gmail integration)
- 📱 Social media posting (Facebook, LinkedIn, Twitter)
- 💰 Accounting & invoicing (Odoo ERP integration)
- 📊 Weekly business audits and CEO briefings
- 🔄 Task automation with human-in-the-loop approval
- 🏥 Health monitoring and self-healing
- 📈 Dashboard for system monitoring

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI EMPLOYEE SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────┐      ┌──────────────────────┐       │
│  │   MAIN.PY            │      │  START_PROCESSES.PY  │       │
│  │  (Platinum Core)     │      │  (MCP Servers)       │       │
│  ├──────────────────────┤      ├──────────────────────┤       │
│  │ • Health Monitor     │      │ • Email MCP          │       │
│  │ • Self-Healing Mgr   │      │ • Odoo MCP           │       │
│  │ • Orchestrator       │      │ • Social MCP         │       │
│  │ • Dashboard (5000)   │      │ • Gmail Watcher      │       │
│  │                      │      │ • File Watchers      │       │
│  └──────────┬───────────┘      └──────────┬───────────┘       │
│             │                             │                    │
│             └─────────────┬───────────────┘                    │
│                           ▼                                    │
│              ┌─────────────────────────┐                       │
│              │   VAULT/ (Shared Data)  │                       │
│              ├─────────────────────────┤                       │
│              │ • Needs_Action/         │                       │
│              │ • Pending_Approval/     │                       │
│              │ • Approved/             │                       │
│              │ • Done/                 │                       │
│              │ • Logs/                 │                       │
│              │ • Secrets.json (🔒)     │                       │
│              │ • Dashboard.md          │                       │
│              └─────────────────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start Guide

### Prerequisites
```bash
pip install -r requirements.txt
```

### Running the System

**For Full Platinum Tier Experience (Recommended):**

Open TWO terminals:

**Terminal 1 - Core System:**
```bash
python main.py
```
Starts: Health Monitor, Self-Healing, Orchestrator, Dashboard (http://localhost:5000)

**Terminal 2 - MCP Servers:**
```bash
python start_processes.py
```
Starts: Email MCP, Odoo MCP, Social MCP, Gmail Watcher, File Watchers

### What Each Command Does

| Command | Purpose | Components |
|---------|---------|------------|
| `python main.py` | Platinum Tier core system | Health Monitor, Self-Healing Manager, Executive Orchestrator, Dashboard Web UI |
| `python start_processes.py` | MCP servers & watchers | Email/Odoo/Social MCP servers, Gmail/Filesystem/Process watchers |

## 📊 Component Details

### Main.py Components

| Component | Function | Check Interval |
|-----------|----------|----------------|
| **Health Monitor** | Monitors system health, checks if services are running | Every 30 seconds |
| **Self-Healing Manager** | Auto-restarts failed services, recovers from errors | Every 15 seconds |
| **Executive Orchestrator** | Processes tasks from vault, manages workflow | Every 60 seconds |
| **Dashboard** | Web UI for monitoring system status | Real-time (Port 5000) |

### Start_processes.py Components

| Component | Function | Purpose |
|-----------|----------|---------|
| **Email MCP** | Email operations with approval workflow | Send/draft emails via Gmail API |
| **Odoo MCP** | ERP integration for invoices/payments | Create invoices, track payments |
| **Social MCP** | Social media posting | Post to Facebook, LinkedIn, Twitter |
| **Gmail Watcher** | Monitor Gmail inbox | Auto-triage incoming emails |
| **Filesystem Watcher** | Monitor vault/Inbox folder | Detect new task files |
| **Process Watcher** | Monitor vault changes | Trigger automated workflows |

## 🔄 Workflow Diagram

```
┌─────────────┐
│ New Email   │
│ Arrives     │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Gmail Watcher   │
│ Detects Email   │
└──────┬──────────┘
       │
       ▼
┌─────────────────────┐
│ Creates Task File   │
│ in Needs_Action/    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Orchestrator        │
│ Processes Task      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Email MCP Creates   │
│ Draft Reply         │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Moves to            │
│ Pending_Approval/   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 👤 Human Reviews    │
│ Moves to Approved/  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Email MCP Sends     │
│ Email via Gmail     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Moves to Done/      │
│ Logs to vault/Logs/ │
└─────────────────────┘
```

## 📁 Vault Folder Structure

| Folder | Purpose | Who Writes | Who Reads |
|--------|---------|------------|-----------|
| `Needs_Action/` | New tasks waiting to be processed | Watchers, MCP Servers | Orchestrator |
| `Pending_Approval/` | Tasks requiring human approval | MCP Servers | Human, Orchestrator |
| `Approved/` | Human-approved tasks ready to execute | Human | MCP Servers |
| `Rejected/` | Human-rejected tasks | Human | Logging system |
| `Done/` | Completed tasks | Orchestrator, MCP Servers | Weekly Audit |
| `Logs/` | All system logs (JSON/JSONL) | All components | Dashboard, Audit |
| `Drafts/` | Draft content (emails, posts) | MCP Servers | Human review |
| `Archive/` | Old completed tasks | Orchestrator | Audit system |
| `Briefings/` | Weekly CEO briefings | Weekly Audit | Human |

### Important Notes

- **All logs are stored in `vault/Logs/`** - Never in root directory
- **Secrets are encrypted** - `vault/Secrets.json` uses Fernet encryption
- **Dashboard available at** - http://localhost:5000 (when main.py is running)
- **Human approval required** - All sensitive operations need manual approval in `vault/Pending_Approval/`

## 🔐 Security Model

| File | Status | Description |
|------|--------|-------------|
| `vault/Secrets.json` | 🔒 Encrypted | All API keys, passwords encrypted with Fernet |
| `vault/Secrets.key` | 🔒 Ignored by git | Encryption key (NEVER commit) |
| `vault/Users.json` | 🔒 Hashed | User passwords hashed with bcrypt |
| `credentials.json` | 🔒 Ignored by git | Gmail OAuth credentials |
| `*.env` files | 🔒 Ignored by git | Environment variables |

### What Gets Pushed to GitHub

| ✅ Safe to Push | ❌ Never Push |
|----------------|---------------|
| Python code (*.py) | vault/Secrets.json |
| README.md | vault/Secrets.key |
| requirements.txt | vault/Users.json |
| .gitignore | credentials.json |
| vault/Logs/*.json | *.env files |
| vault/Dashboard.md | token.json |

## 🎯 Tier Comparison

| Feature | Bronze | Silver | Gold | Platinum |
|---------|--------|--------|------|----------|
| **File-based tasks** | ✅ | ✅ | ✅ | ✅ |
| **Gmail integration** | ❌ | ✅ | ✅ | ✅ |
| **Email MCP** | ❌ | ✅ | ✅ | ✅ |
| **Social media posting** | ❌ | ✅ | ✅ | ✅ |
| **Odoo ERP integration** | ❌ | ❌ | ✅ | ✅ |
| **Weekly audit & CEO briefing** | ❌ | ❌ | ✅ | ✅ |
| **Error recovery & retry** | ❌ | ❌ | ✅ | ✅ |
| **Comprehensive logging** | ❌ | ❌ | ✅ | ✅ |
| **Health monitoring** | ❌ | ❌ | ❌ | ✅ |
| **Self-healing** | ❌ | ❌ | ❌ | ✅ |
| **Dashboard UI** | ❌ | ❌ | ❌ | ✅ |
| **Cloud/Local executive** | ❌ | ❌ | ❌ | ✅ |

## 🛠️ Troubleshooting

| Problem | Solution | Check |
|---------|----------|-------|
| **Dashboard not loading** | Ensure `main.py` is running | Visit http://localhost:5000 |
| **Emails not being processed** | Check if `start_processes.py` is running | Look for Gmail Watcher in logs |
| **Secrets not loading** | Run `python secrets_manager.py` to initialize | Check `vault/Secrets.json` exists |
| **MCP server errors** | Check credentials in `vault/Secrets.json` | Review `vault/Logs/errors.json` |
| **Tasks stuck in Pending_Approval** | Manually move files to `Approved/` or `Rejected/` | Check folder permissions |
| **Health Monitor alerts** | Check `vault/Logs/health_alerts.json` | Restart failed services |
| **Logs in wrong location** | All logs should be in `vault/Logs/` only | Delete any root `Logs/` folder |
| **Git push rejected** | Ensure secrets are in `.gitignore` | Run `git check-ignore vault/Secrets.json` |

## 📝 Quick Reference

### Port Usage
| Port | Service | URL |
|------|---------|-----|
| 5000 | Dashboard | http://localhost:5000 |
| 8080 | Email MCP | http://localhost:8080 |
| 8081 | Odoo MCP | http://localhost:8081 |
| 8082 | Social MCP | http://localhost:8082 |

### Log Files Location
All logs are stored in `vault/Logs/`:
- `full_audit.jsonl` - Complete audit trail
- `errors.json` - Error logs
- `odoo_operations.json` - Odoo operations
- `social_operations.json` - Social media operations
- `health_alerts.json` - Health monitoring alerts
- `weekly_audit.json` - Weekly business audits

### Key Commands
```bash
# Start everything
python main.py                    # Terminal 1
python start_processes.py         # Terminal 2

# Initialize secrets (first time only)
python secrets_manager.py

# Test health monitoring
python simple_health_test.py

# Run weekly audit manually
python weekly_audit.py

# Create new user
python create_users.py
```

## 🔐 Dashboard Login & Access

### Accessing the Dashboard

1. **Start the system:**
   ```bash
   python main.py
   ```

2. **Open browser:**
   ```
   http://localhost:5000
   ```

3. **Login with default credentials:**
   - **Username:** `admin`
   - **Password:** `admin`
   - ⚠️ **Change this password immediately in production!**

### User Roles & Permissions

| Role | Dashboard Access | Approve Tasks | Manage Users | View Financials |
|------|-----------------|---------------|--------------|-----------------|
| **Admin** | Full access | ✅ Yes | ✅ Yes | ✅ Yes |
| **Approver** | Most features | ✅ Yes | ❌ No | ✅ Yes |
| **Viewer** | Basic status only | ❌ No | ❌ No | ❌ No |

### Dashboard Features

- 📊 **Real-time monitoring** (updates every 5 seconds)
- 💻 **System health** (CPU, Memory, Disk)
- 🚨 **Health alerts** (automatic system monitoring)
- 📋 **Pending tasks** (Needs Action, Pending Approval, Drafts)
- 💰 **Financial data** (Odoo invoices, revenue forecasts)
- 📱 **Social media** (recent posts and activity)
- 📝 **Live logs** (Social and Odoo operations)

### Creating New Users

```bash
python create_users.py
```

Follow the prompts to create Admin, Approver, or Viewer accounts.

---

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



# Personal AI Employee - Gold Tier

Advanced functionality with weekly business & accounting audit, error recovery, graceful degradation, and comprehensive logging.

## Enhanced Folder Structure
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
  /Briefings
  /Needs_Action
  /Done
  /Pending_Approval
  /Drafts
  /Approved
  /Rejected
  /Inbox
  /Archive
  /Logs
Dashboard.md
Business_Goals.md
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
  SKILL_WeeklyAudit.md
  SKILL_OdooDraftInvoice.md
  SKILL_SocialPost.md
filesystem_watcher.py
gmail_watcher.py
process_watcher.py
start_processes.py
start_all_processes.bat
email_mcp.py
odoo_mcp.py
social_mcp.py
daily_claude_run.bat
mcp.json
weekly_audit.py
retry_utils.py
audit_logger.py
Documentation/
  Gold_Tier_Architecture.md
  Final_Gold_Completion_Checklist.md
test_weekly_audit.py
```

# Gold Tier Features

## 1. Weekly Business & Accounting Audit System

### CEO Briefing Generation
- **Weekly Audit (`weekly_audit.py`)**: Runs automatically every Sunday to generate comprehensive CEO briefings
- **Business Goals Analysis**: Reads from `Business_Goals.md` for strategic alignment
- **Task Completion Tracking**: Analyzes `/Done` folder for completed tasks from the current week
- **Revenue Reporting**: Fetches financial data via Odoo MCP integration
- **Bottleneck Identification**: Identifies delayed tasks and pending items requiring attention
- **Proactive Suggestions**: Generates actionable suggestions (e.g., cancel underperforming subscriptions, follow up with clients)

**Briefing File Format** (`/vault/Briefings/{date}_CEO_Briefing.md`):
```
# Weekly CEO Briefing - 2026-02-28

## Executive Summary
This week's business audit covering key metrics, completed tasks, and strategic recommendations.

## Business Goals Overview
[Summary of business goals alignment]

## Revenue Analysis
### This Week
- Total Revenue: $[amount]
- Number of Invoices: [count]
- Average Invoice Value: $[amount]

## Completed Tasks
### This Week
- [List of completed tasks from /Done folder]

## Bottlenecks & Delays
### Current Issues
- [List of pending approvals, delayed tasks]

## Proactive Suggestions
### Recommendations for Next Week
- [List of proactive suggestions in dry-run mode]
```

### Scheduler Integration
- **Daily Batch Script (`daily_claude_run.bat`)**: Updated to check if today is Sunday and run weekly audit automatically
- **PowerShell Integration**: Uses PowerShell command to detect day of week
- **Dashboard Updates**: Automatically updates dashboard with audit information

## 2. Multi-MCP Integration System

### Odoo MCP Server (`odoo_mcp.py`)
- Handles ERP operations including invoices and payments
- Implements draft approval system for financial operations
- Provides revenue data for weekly audits
- Coordinated with email and social MCPs

### Social MCP Server (`social_mcp.py`)
- Manages social media posting with human approval
- Generates content suggestions for business updates
- Integrates with weekly audit for social media content creation
- Supports multiple platforms (Facebook, Instagram, Twitter)

### Email MCP Server (`email_mcp.py`)
- Enhanced with audit logging capabilities
- Coordinated operation with other MCPs for comprehensive workflows
- Maintains human-in-the-loop approval for sensitive operations

## 3. Error Recovery & Graceful Degradation

### Retry Mechanisms
- **Exponential Backoff (`retry_utils.py`)**: Implements configurable retry mechanism with exponential backoff
- **Decorator Pattern**: Uses `@retry_with_exponential_backoff` decorator across all API calls
- **Configurable Parameters**: Maximum retries, base delay, max delay, and backoff factor
- **Jitter Implementation**: Includes random jitter to prevent thundering herd effect

**Retry Configuration**:
```python
@retry_with_exponential_backoff(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    backoff_factor=2.0,
    exceptions=(Exception,)
)
def api_call_function():
    # Your API call implementation
    pass
```

### Graceful Degradation Strategies
- **MCP Server Failures**: Operations are queued in appropriate directories when MCP servers are unavailable
- **File Watcher Failures**: System continues with manual processing capabilities
- **API Unavailability**: Operations remain in draft/approval status until systems are restored
- **Credential Expiration**: System logs issues and awaits manual intervention
- **Component Failures**: System continues operating even when individual components fail

### Connection Recovery
- **Automatic Reconnection**: MCP servers automatically reconnect when connections fail
- **Operation Queuing**: Failed operations are queued for later retry
- **Fallback Strategies**: Defined procedures for different failure scenarios

## 4. Comprehensive Logging System

### JSONL Audit Logging (`audit_logger.py`)
- **Full Audit Trail**: All operations logged to `/vault/Logs/full_audit.jsonl` in JSONL format
- **Standardized Format**: Consistent structure with action_type, status, details, error, user_id, session_id
- **UTC Timestamps**: All operations timestamped in UTC ISO format
- **Cross-Service Integration**: Standardized logging across all MCP servers

**JSONL Log Entry Format**:
```json
{"timestamp": "2026-03-04T08:32:09.906955", "action_type": "email_sent", "status": "success", "details": {"to": "user@example.com", "subject": "Weekly Report", "message_id": "1a2b3c"}, "user_id": "system"}
{"timestamp": "2026-03-04T08:32:15.123456", "action_type": "odoo_invoice_draft", "status": "pending", "details": {"partner_id": 123, "amount": 1500.00}, "error": null, "user_id": "system"}
```

### Log Categories
- **Operations Logs**: Track successful operations
- **Error Logs**: Capture failures and issues
- **Retry Logs**: Document failed attempts and retry mechanics
- **Audit Trail**: Complete system activity tracking

## 5. New Skills for Gold Tier

### SKILL_WeeklyAudit.md
- Defines the weekly audit functionality with proper MCP integration
- Includes parameters and return values for the audit process
- Coordinates with multiple MCPs for comprehensive data gathering

### SKILL_OdooDraftInvoice.md
- Handles Odoo invoice operations with approval workflow
- Integrates with the weekly audit for financial reporting
- Implements draft-only operations for financial security

### SKILL_SocialPost.md
- Manages social media content creation
- Coordinates with weekly audit for business updates
- Implements approval workflow for social media posts

## 6. Architecture & Documentation

### Comprehensive Documentation
- **Gold_Tier_Architecture.md**: Detailed system architecture with ASCII diagrams
- **Final_Gold_Completion_Checklist.md**: Complete checklist of all implemented features
- **Lessons Learned**: Best practices and implementation insights
- **Setup Guide**: Complete installation and configuration instructions

### Modular Design Benefits
- MCP servers can be independently updated
- File system approach enables offline operations
- Human-in-the-loop prevents automation errors
- Directory-based workflow resilient to system failures

## Testing Gold Tier Functionality

### Manual Testing
1. **Weekly Audit Test**: Force run the weekly audit by temporarily changing the date or directly executing `python weekly_audit.py`
2. **MCP Integration Test**: Verify all three MCP servers (email, odoo, social) can coordinate properly
3. **Error Recovery Test**: Simulate API failures to verify retry mechanisms activate
4. **Logging Test**: Verify all operations are logged to the JSONL audit file
5. **Human-in-the-Loop Test**: Test approval workflows with draft operations

### Automated Testing
- **test_weekly_audit.py**: Comprehensive test suite for weekly audit functionality
- Unit tests for all core functions
- Simulation of Sunday execution scenarios
- Validation of CEO briefing generation

### End-to-End Gold Tier Workflow
1. **Sunday Execution**: Weekly audit automatically runs on Sundays
2. **Data Gathering**: Collects information from Business_Goals.md, /Done folder, and Odoo via MCP
3. **Analysis**: Identifies revenue, completed tasks, bottlenecks, and proactive suggestions
4. **Briefing Generation**: Creates CEO briefing in /vault/Briefings
5. **MCP Coordination**: Coordinates with email, odoo, and social MCPs for comprehensive operations
6. **Logging**: Records all operations to comprehensive audit log
7. **Dashboard Update**: Updates dashboard with audit information

The Gold Tier implementation provides enterprise-grade business automation with comprehensive error recovery, graceful degradation, and detailed audit trails.

## Setup for Gold Tier

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure MCP Servers:**
   - Set up OAuth credentials for Gmail, Odoo, and social media
   - Configure `mcp.json` with appropriate endpoints

3. **Start Complete System:**
   ```bash
   # Method 1: Using Python script
   python start_processes.py

   # Method 2: Using batch file
   start_all_processes.bat

   # Method 3: Manual start (alternative)
   python email_mcp.py &
   python odoo_mcp.py --vault-path odoo_vault.json &
   python social_mcp.py &
   python gmail_watcher.py --vault-path ./vault &
   python filesystem_watcher.py --vault-path ./vault &
   python process_watcher.py --vault-path ./vault &
   ```

4. **Initialize Business Data:**
   - Add your business goals to `Business_Goals.md`
   - Configure Odoo connection for financial data access
   - Set up social media accounts and permissions


# Personal AI Employee - Platinum Tier

Advanced distributed architecture with Always-on Cloud Executive and Local Executive coordination through synced vault system.

## 🚀 Quick Start - Running the Complete System

### Option 1: Platinum Tier (Recommended - Latest)
Run the complete Platinum Tier system with health monitoring, self-healing, orchestrator, and dashboard:

```bash
python main.py
```

This starts:
- ✅ Health Monitor (monitors system health every 30s)
- ✅ Self-Healing Manager (auto-recovery every 15s)
- ✅ Executive Orchestrator (task scheduler every 60s)
- ✅ Dashboard Web UI (http://localhost:5000)

### Option 2: Gold/Silver Tier (Legacy - All MCP Servers)
Run all MCP servers and watchers for email, social, and Odoo integration:

```bash
python start_processes.py
```

This starts:
- ✅ Process Watcher
- ✅ Filesystem Watcher
- ✅ Gmail Watcher
- ✅ Email MCP Server
- ✅ Odoo MCP Server
- ✅ Social MCP Server

### Option 3: Run Everything Together
For complete functionality, run both commands in separate terminals:

**Terminal 1:**
```bash
python main.py
```

**Terminal 2:**
```bash
python start_processes.py
```

This gives you the full Platinum Tier experience with all MCP integrations.

---

## Platinum Tier Architecture

### Cloud Executive Responsibilities
- **Email triage**: Categorizes incoming emails and creates draft replies
- **Social post drafts**: Generates social media content drafts and scheduling suggestions
- **Draft-only operations**: Creates drafts requiring local approval but does not execute final actions
- **Read-only access**: Can read audit logs and system status but cannot modify sensitive operations
- **Sync responsibility**: Pushes new drafts and categorized items to the shared vault

### Local Executive Responsibilities
- **Approvals**: Reviews and approves/rejects all pending actions
- **WhatsApp session management**: Handles WhatsApp communications and sessions
- **Payments and banking**: Processes financial transactions and banking operations
- **Final send/post actions**: Executes final email sends, social media posts, and financial operations
- **Dashboard updates**: Maintains the single-writer Dashboard.md file
- **Sync responsibility**: Pulls cloud drafts and pushes approved actions

## Enhanced Folder Structure
```
vault/
├── Needs_Action/
│   ├── email/
│   ├── social/
│   ├── odoo/
│   ├── payment/
│   └── whatsapp/
├── Plans/
│   ├── email/
│   ├── social/
│   ├── odoo/
│   ├── payment/
│   └── whatsapp/
├── Pending_Approval/
│   ├── email/
│   ├── social/
│   ├── odoo/
│   ├── payment/
│   └── whatsapp/
├── In_Progress/
│   ├── cloud_exec/
│   └── local_exec/
├── Updates/
├── Signals/
├── Drafts/
├── Archive/
├── Done/
├── Approved/
├── Rejected/
├── Logs/
└── Dashboard.md
```

## Key Features

### 1. Claim-by-Move Rule
- First agent to move item from `/Needs_Action` to `/In_Progress/<agent>/` owns it
- Prevents duplicate processing of the same task
- Implemented atomically to handle concurrent access

### 2. Single-Writer Rule
- Only Local Executive can update `Dashboard.md`
- Prevents sync conflicts on dashboard updates
- Cloud Executive can read but not write to dashboard

### 3. Secret Protection
- Secrets never sync to cloud via Git exclusions
- Protected files: `.env`, tokens, sessions, banking credentials
- Configured in `VaultSyncManager` exclusions

### 4. Operation Separation
- **Cloud Operations**: email_triage, draft_reply, social_post_draft, social_post_schedule, weekly_audit_read, odoo_read
- **Local Operations**: approval, whatsapp_session, payments_banking, final_send, final_post, dashboard_write, email_send, social_post_execute, odoo_execute

## Core Implementation

### orchestrator.py
The main orchestrator manages executive coordination:
- `VaultSyncManager`: Handles Git-based vault synchronization with exclusions
- `ExecutiveOrchestrator`: Main orchestrator class with cloud/local role management
- Cloud operations: email triage, social draft creation
- Local operations: approvals, final actions
- Sync cycle management with pull/push operations

### Deployment
The system can be deployed on free cloud VMs (Oracle Cloud Free Tier recommended, or AWS free):
- Cloud Executive runs on VM for continuous availability
- Local Executive runs on user's machine for sensitive operations
- Git-based synchronization with automatic exclusion of sensitive files

## Running the System

### Cloud Executive Setup
```bash
python3 orchestrator.py --vault-path ./vault --is-cloud --remote-repo <git_repo_url>
```

### Local Executive Setup
```bash
python3 orchestrator.py --vault-path ./vault --remote-repo <git_repo_url>
```

## Security Model

### Data Flow Security
- Cloud Executive never sees sensitive credentials
- Local Executive handles all sensitive operations
- Vault sync excludes all secret files
- All communications through the shared vault with approval workflows

### Access Control
- Cloud Executive: Read access to most data, write to drafts and categorizations
- Local Executive: Full access including sensitive operations
- All operations follow the principle of least privilege

### Audit Trail
- All operations logged in `vault/Logs/orchestrator.log`
- Dashboard updates provide system status
- Git history provides change tracking (excluding secrets)

The Platinum Tier implementation provides enterprise-grade distributed automation with secure separation of duties, continuous availability, and comprehensive synchronization.