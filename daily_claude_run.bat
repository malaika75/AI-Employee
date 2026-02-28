@echo off
echo [%date% %time%] Starting AI Employee Daily Run >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"

cd /d "D:\code\AI-Employee\vault"
echo [%date% %time%] Changed to vault directory: %cd% >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"

echo [%date% %time%] Running Claude Code now... >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"

"C:\Users\Hassan Computer\AppData\Roaming\npm\claude.cmd" "Daily AI Employee Run:

1. Scan /Needs_Action for existing files using SKILL_ScanNeedsAction.md (only existing, no new).

2. For each file: Create Plan_{filename}.md using SKILL_CreatePlanForTask.md.

3. Generate custom reply (reason: polite, relevant 3-5 sentences).

4. If sensitive: Create /Pending_Approval/APPROVAL_{filename}.md with reply body.

5. If normal: Create /Archived/RESPONSE_{filename}.md with reply, move original to /Done.

6. Check /Approved: Read files, call MCP to send (use send_email with to, subject, body), if success log to /Logs/email_operations.json with timestamp/action/status, move to /Done.

7. Always generate LinkedIn draft using SKILL_PostToLinkedIn.md (based on Dashboard, even if not Sunday), put in /Drafts.

8. Log every step to /Logs/daily_{date}.json (JSON format: {timestamp, action, status}).
9. Update Dashboard.md with 'Processed [X] tasks, sent [Y] emails, LinkedIn draft generated'.

Execute all steps now without asking questions." >> "D:\code\AI-Employee\vault\Logs\daily_log.txt" 2>&1

echo [%date% %time%] Claude run completed >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"
echo. >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"