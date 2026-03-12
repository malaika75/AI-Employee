@echo off
echo [%date% %time%] Starting AI Employee Daily Run >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"

cd /d "D:\code\AI-Employee"
echo [%date% %time%] Changed to project directory: %cd% >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"

REM Check if today is Sunday (weekday is 1 for Sunday in Windows)
for /f "skip=1 tokens=2 delims=:.," %%x in ('wmic path win32_operatingsystem get locale') do set locale=%%x
for /f "tokens=1" %%a in ('powershell -command "(Get-Date).DayOfWeek"') do set day=%%a
if /i "%day%"=="Sunday" (
    echo [%date% %time%] Today is Sunday - running weekly audit >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"
    python weekly_audit.py >> "D:\code\AI-Employee\vault\Logs\daily_log.txt" 2>&1
)

echo [%date% %time%] Running Odoo approval handler... >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"
python handle_odoo_approvals.py >> "D:\code\AI-Employee\vault\Logs\daily_log.txt" 2>&1

echo [%date% %time%] Running Claude Code now... >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"

"C:\Users\Hassan Computer\AppData\Roaming\npm\claude.cmd" "Daily AI Employee Run:

1. Scan vault/Needs_Action for existing files using SKILL_ScanNeedsAction.md (only existing, no new).

2. For each file: Create Plan_{filename}.md using SKILL_CreatePlanForTask.md.

3. Generate custom reply (reason: polite, relevant 3-5 sentences).

4. If sensitive: Create vault/Pending_Approval/APPROVAL_{filename}.md with reply body.

5. If normal: Create vault/Archived/RESPONSE_{filename}.md with reply, move original to vault/Done.

6. Check vault/Approved: Read files, call MCP to send (use send_email with to, subject, body), if success log to vault/Logs/email_operations.json with timestamp/action/status, move to vault/Done. Also check for Odoo invoice approvals and process them.

7. Always generate LinkedIn draft using SKILL_PostToLinkedIn.md (based on Dashboard, even if not Sunday), put in vault/Drafts.

8. Log every step to vault/Logs/daily_{date}.json (JSON format: {timestamp, action, status}).
9. Update vault/Dashboard.md with 'Processed [X] tasks, sent [Y] emails, LinkedIn draft generated'.

Execute all steps now without asking questions." >> "D:\code\AI-Employee\vault\Logs\daily_log.txt" 2>&1

echo [%date% %time%] Claude run completed >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"
echo. >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"