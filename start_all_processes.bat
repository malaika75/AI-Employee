@echo off
echo [%date% %time%] Starting All AI Employee Processes >> "D:\code\AI-Employee\vault\Logs\process_log.txt"

cd /d "D:\code\AI-Employee"

echo [%date% %time%] Starting Process Watcher... >> "D:\code\AI-Employee\vault\Logs\process_log.txt"

REM Start the process watcher in a new window
start "AI Employee Process Watcher" cmd /c "python process_watcher.py"

timeout /t 2 /nobreak >nul

echo [%date% %time%] Starting Filesystem Watcher... >> "D:\code\AI-Employee\vault\Logs\process_log.txt"

REM Start the filesystem watcher in a new window
start "AI Employee Filesystem Watcher" cmd /c "python filesystem_watcher.py --vault-path D:\code\AI-Employee\vault"

timeout /t 2 /nobreak >nul

echo [%date% %time%] Starting Gmail Watcher... >> "D:\code\AI-Employee\vault\Logs\process_log.txt"

REM Start the gmail watcher in a new window
start "AI Employee Gmail Watcher" cmd /c "python gmail_watcher.py --vault-path D:\code\AI-Employee\vault"

timeout /t 2 /nobreak >nul

echo [%date% %time%] Starting Email MCP Server... >> "D:\code\AI-Employee\vault\Logs\process_log.txt"

REM Start the email MCP server in a new window
start "AI Employee Email MCP Server" cmd /c "python email_mcp.py"

timeout /t 2 /nobreak >nul

echo [%date% %time%] Starting Odoo MCP Server... >> "D:\code\AI-Employee\vault\Logs\process_log.txt"

REM Start the odoo MCP server in a new window
start "AI Employee Odoo MCP Server" cmd /c "python odoo_mcp.py --vault-path D:\code\AI-Employee\odoo_vault.json"

timeout /t 2 /nobreak >nul

echo [%date% %time%] Starting Social MCP Server... >> "D:\code\AI-Employee\vault\Logs\process_log.txt"

REM Start the social MCP server in a new window
start "AI Employee Social MCP Server" cmd /c "python social_mcp.py"

echo [%date% %time%] All processes started successfully! >> "D:\code\AI-Employee\vault\Logs\process_log.txt"
echo.
echo All AI Employee processes have been started:
echo.   1. Process Watcher - monitors vault changes and triggers daily process
echo.   2. Filesystem Watcher - monitors Inbox folder for new files
echo.   3. Gmail Watcher - monitors Gmail for important emails
echo.   4. Email MCP Server - handles email operations with approval workflow
echo.   5. Odoo MCP Server - manages ERP operations (invoices, payments) with approval workflow
echo.   6. Social MCP Server - manages social media posts with approval workflow
echo.
echo Each process is running in its own window. You can close this window now.
echo.
pause