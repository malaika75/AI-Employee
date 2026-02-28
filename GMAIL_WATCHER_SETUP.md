# Gmail Watcher Setup Guide

## Prerequisites

1. Python 3.7 or higher
2. Google Account with Gmail enabled
3. Google Cloud Project with Gmail API enabled

## Setup Instructions

### 1. Enable Gmail API and Create Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - For application type, select "Desktop application"
   - Name it "Gmail Watcher" or similar
   - Download the credentials JSON file
   - Rename the downloaded file to `credentials.json`

### 2. Install Required Packages

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 python-frontmatter
```

Or using the requirements.txt file:

```bash
pip install -r requirements.txt
```

### 3. Configure the Gmail Watcher

1. Place `credentials.json` in the same directory as `gmail_watcher.py`
2. Run the script for the first time:
   ```bash
   python gmail_watcher.py --vault-path /path/to/your/obsidian/vault
   ```
3. The first run will open a browser window to authenticate with your Google account
4. After authentication, a `token.json` file will be created (this stores your access token)
5. The script will begin monitoring your Gmail for new important emails

### 4. Running the Watcher

The script can be run continuously to monitor for new emails every 2 minutes:

```bash
python gmail_watcher.py --vault-path /path/to/your/obsidian/vault
```

### 5. Security Notes

- Keep `credentials.json` and `token.json` outside of your Obsidian vault for security
- These files contain authentication tokens and should not be shared or committed to version control
- To revoke access, delete `token.json` and re-authenticate

### 6. How It Works

1. The script uses OAuth 2.0 to authenticate with Gmail
2. Every 120 seconds, it polls for unread + important emails
3. For each new email found:
   - Creates an EMAIL_{message_id}.md file in the /Needs_Action folder
   - Includes metadata in frontmatter (from, subject, received time, etc.)
   - Tracks processed emails to avoid duplicates
   - Logs new email detection

### 7. Troubleshooting

- If the script fails with authentication errors, delete `token.json` and run again
- Make sure your Google account has Gmail enabled
- Check that the vault path is correct and accessible
- Verify that the Gmail API is enabled in your Google Cloud project

## 8. Scheduling with Cron

To run Claude AI processing tasks automatically, you can set up cron jobs or scheduled tasks:

### Linux/macOS (using crontab)

1. Open terminal and edit crontab:
```
crontab -e
```

2. Add these lines for daily Claude processing at 8 AM:
```
# Daily email processing and briefing at 8 AM
0 8 * * * cd /path/to/AI-Employee && /usr/bin/env python3 process_new_emails.py >> logs/email_processing_$(date +\%Y\%m\%d).log 2>&1

# Daily LinkedIn post check at 9 AM (to review/approve drafts)
0 9 * * * cd /path/to/AI-Employee && /usr/bin/env python3 check_linkedin_drafts.py >> logs/linkedin_check_$(date +\%Y\%m\%d).log 2>&1

# Weekly summary generation every Monday at 10 AM
0 10 * * 1 cd /path/to/AI-Employee && /usr/bin/env python3 generate_weekly_summary.py >> logs/weekly_summary_$(date +\%Y\%m\%d).log 2>&1
```

### Windows (using Task Scheduler)

1. Open Task Scheduler as Administrator
2. Create Basic Task
3. Set trigger to Daily at 8:00 AM
4. Set action to "Start a program":
   - Program: `C:\Python39\python.exe` (or your Python path)
   - Arguments: `process_new_emails.py`
   - Start in: `C:\path\to\AI-Employee` (your project directory)

Alternative Windows approach using a batch file:

Create `daily_claude_task.bat`:
```batch
@echo off
cd /d "C:\path\to\AI-Employee"
python process_new_emails.py >> logs\daily_processing.log 2>&1
```

Then schedule this batch file in Task Scheduler.

### Cross-platform Python-based scheduler

You can also create a dedicated scheduler script:

Create `scheduler.py`:
```python
#!/usr/bin/env python3
"""
AI Employee Task Scheduler
"""
import schedule
import time
import subprocess
import os
from datetime import datetime

def run_email_processing():
    """Run the email processing script"""
    print(f"[{datetime.now()}] Running email processing...")
    try:
        result = subprocess.run(['python', 'process_new_emails.py'],
                              capture_output=True, text=True, cwd='.')
        print(f"Email processing completed with return code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error running email processing: {e}")

def run_linkedin_post_generation():
    """Run the LinkedIn post generation"""
    print(f"[{datetime.now()}] Running LinkedIn post generation...")
    try:
        result = subprocess.run(['python', 'generate_linkedin_post.py'],
                              capture_output=True, text=True, cwd='.')
        print(f"LinkedIn post generation completed with return code: {result.returncode}")
    except Exception as e:
        print(f"Error running LinkedIn post generation: {e}")

def run_daily_briefing():
    """Run daily briefing generation"""
    print(f"[{datetime.now()}] Running daily briefing...")
    try:
        result = subprocess.run(['python', 'generate_daily_briefing.py'],
                              capture_output=True, text=True, cwd='.')
        print(f"Daily briefing completed with return code: {result.returncode}")
    except Exception as e:
        print(f"Error running daily briefing: {e}")

def main():
    # Schedule tasks
    schedule.every().day.at("08:00").do(run_email_processing)
    schedule.every().day.at("08:15").do(run_daily_briefing)
    schedule.every().monday.at("09:00").do(run_linkedin_post_generation)

    print("AI Employee scheduler started. Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
```

To install the schedule library:
```
pip install schedule
```

Run the scheduler with:
```
python scheduler.py
```