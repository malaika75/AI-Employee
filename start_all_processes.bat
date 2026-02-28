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

echo [%date% %time%] All processes started successfully! >> "D:\code\AI-Employee\vault\Logs\process_log.txt"
echo.
echo All AI Employee processes have been started:
echo.   1. Process Watcher - monitors vault changes and triggers daily process
echo.   2. Filesystem Watcher - monitors Inbox folder for new files
echo.   3. Gmail Watcher - monitors Gmail for important emails
echo.
echo Each process is running in its own window. You can close this window now.
echo.
pause