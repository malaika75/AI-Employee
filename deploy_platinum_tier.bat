@echo off
REM Platinum Tier Deployment Script for Windows

echo AI Employee Platinum Tier Deployment Script
echo ===========================================

REM Check if required tools are installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

git --version >nul 2>&1
if errorlevel 1 (
    echo Error: Git is not installed or not in PATH
    pause
    exit /b 1
)

echo All required tools are available.

REM Check if GitPython is installed
python -c "import git" >nul 2>&1
if errorlevel 1 (
    echo Installing GitPython...
    pip install GitPython
)

REM Create vault structure if it doesn't exist
echo Setting up vault structure...
if not exist "vault\Needs_Action\email" mkdir "vault\Needs_Action\email"
if not exist "vault\Needs_Action\social" mkdir "vault\Needs_Action\social"
if not exist "vault\Needs_Action\odoo" mkdir "vault\Needs_Action\odoo"
if not exist "vault\Needs_Action\payment" mkdir "vault\Needs_Action\payment"
if not exist "vault\Needs_Action\whatsapp" mkdir "vault\Needs_Action\whatsapp"

if not exist "vault\Plans\email" mkdir "vault\Plans\email"
if not exist "vault\Plans\social" mkdir "vault\Plans\social"
if not exist "vault\Plans\odoo" mkdir "vault\Plans\odoo"
if not exist "vault\Plans\payment" mkdir "vault\Plans\payment"
if not exist "vault\Plans\whatsapp" mkdir "vault\Plans\whatsapp"

if not exist "vault\Pending_Approval\email" mkdir "vault\Pending_Approval\email"
if not exist "vault\Pending_Approval\social" mkdir "vault\Pending_Approval\social"
if not exist "vault\Pending_Approval\odoo" mkdir "vault\Pending_Approval\odoo"
if not exist "vault\Pending_Approval\payment" mkdir "vault\Pending_Approval\payment"
if not exist "vault\Pending_Approval\whatsapp" mkdir "vault\Pending_Approval\whatsapp"

if not exist "vault\In_Progress\cloud_exec" mkdir "vault\In_Progress\cloud_exec"
if not exist "vault\In_Progress\local_exec" mkdir "vault\In_Progress\local_exec"

if not exist "vault\Updates" mkdir "vault\Updates"
if not exist "vault\Signals" mkdir "vault\Signals"
if not exist "vault\Drafts" mkdir "vault\Drafts"
if not exist "vault\Archive" mkdir "vault\Archive"
if not exist "vault\Done" mkdir "vault\Done"
if not exist "vault\Approved" mkdir "vault\Approved"
if not exist "vault\Rejected" mkdir "vault\Rejected"
if not exist "vault\Logs" mkdir "vault\Logs"

echo Vault structure created.

REM Initialize git repo in vault if it doesn't exist
if not exist "vault\.git" (
    echo Initializing vault as git repository...
    cd vault
    git init
    echo .env > .gitignore
    echo tokens.json >> .gitignore
    echo credentials.json >> .gitignore
    echo whatsapp_session* >> .gitignore
    echo banking_creds* >> .gitignore
    echo *_token.json >> .gitignore
    echo *_session.json >> .gitignore
    echo WhatsApp/ >> .gitignore
    echo Banking/ >> .gitignore
    echo Payments/ >> .gitignore
    echo .gitkeep
    git add .gitkeep .gitignore
    git commit -m "Initial vault commit"
    cd ..
)

echo Vault git repository set up with exclusions.

REM Check arguments
if "%1"=="" (
    echo Usage: %0 [cloud^|local] [remote_repo_url]
    echo   cloud: Start as Cloud Executive
    echo   local: Start as Local Executive
    echo   remote_repo_url: Git repository URL for vault sync (optional)
    echo.
    echo Examples:
    echo   %0 local                    REM Start as Local Executive (local-only)
    echo   %0 cloud git@repo:url       REM Start as Cloud Executive with sync
    echo   %0 local git@repo:url       REM Start as Local Executive with sync
    pause
    exit /b 1
)

set EXECUTIVE_TYPE=%1
set REMOTE_REPO=%2

if "%EXECUTIVE_TYPE%"=="cloud" (
    if "%REMOTE_REPO%"=="" (
        echo Running as Cloud Executive without remote repo
        python orchestrator.py --vault-path ./vault --is-cloud --sync-interval 30
    ) else (
        echo Running as Cloud Executive with remote repo: %REMOTE_REPO%
        python orchestrator.py --vault-path ./vault --is-cloud --remote-repo %REMOTE_REPO% --sync-interval 30
    )
) else if "%EXECUTIVE_TYPE%"=="local" (
    if "%REMOTE_REPO%"=="" (
        echo Running as Local Executive without remote repo
        python orchestrator.py --vault-path ./vault --sync-interval 30
    ) else (
        echo Running as Local Executive with remote repo: %REMOTE_REPO%
        python orchestrator.py --vault-path ./vault --remote-repo %REMOTE_REPO% --sync-interval 30
    )
) else (
    echo Error: Invalid executive type. Use 'cloud' or 'local'.
    pause
    exit /b 1
)

pause