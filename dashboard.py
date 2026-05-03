#!/usr/bin/env python3
"""
Platinum Tier Real-time Dashboard
Flask app that displays live data from the AI employee system
"""
import os
import json
import time
import psutil
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import subprocess
import sys

# Import the health monitor
from health_monitor import HealthMonitor


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Should be changed in production
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize health monitor
health_monitor = HealthMonitor(check_interval=30)  # Check every 30 seconds
health_monitor.start_monitoring()

# Configuration
VAULT_PATH = Path("vault").resolve()  # Use absolute path
LOGS_PATH = VAULT_PATH / "Logs"
NEEDS_ACTION_PATH = VAULT_PATH / "Needs_Action"
PENDING_APPROVAL_PATH = VAULT_PATH / "Pending_Approval"
DRAFTS_PATH = VAULT_PATH / "Drafts"

# User authentication models
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

USERS_FILE = VAULT_PATH / "Users.json"

def get_users():
    """Load users from the Users.json file"""
    # Debug: log the path being checked
    with open('vault/Logs/login_debug.log', 'a') as f:
        f.write(f"Checking USERS_FILE path: {USERS_FILE}\n")
        f.write(f"USERS_FILE exists: {USERS_FILE.exists()}\n")
        f.write(f"Current working directory: {os.getcwd()}\n")

    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        with open('vault/Logs/login_debug.log', 'a') as f:
            f.write(f"Error loading users: {e}\n")
        return {}

def save_users(users):
    """Save users to the Users.json file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

@login_manager.user_loader
def load_user(user_id):
    users = get_users()
    if user_id in users:
        user_data = users[user_id]
        return User(user_id, user_data['username'], user_data['role'])
    return None


def get_ai_employee_status():
    """Get the status of the AI Employee system"""
    # Check if AI employee processes are running by looking at recent file modifications
    try:
        # Check for recent activity in vault logs - look for activity in last 10 minutes
        recent_activity = False
        if LOGS_PATH.exists():
            for log_file in LOGS_PATH.glob("*.json"):
                if log_file.stat().st_mtime > time.time() - 600:  # 10 minutes
                    recent_activity = True
                    break

        # Also check if health_alerts.json has been modified recently (indicates health monitor running)
        health_alerts_file = LOGS_PATH / "health_alerts.json"
        health_monitor_recent = False
        if health_alerts_file.exists():
            if health_alerts_file.stat().st_mtime > time.time() - 600:  # 10 minutes
                health_monitor_recent = True

        # Also check if ralph_loop.json has been modified recently (indicates scheduler running)
        ralph_loop_file = LOGS_PATH / "ralph_loop.json"
        ralph_recent = False
        if ralph_loop_file.exists():
            if ralph_loop_file.stat().st_mtime > time.time() - 600:  # 10 minutes
                ralph_recent = True

        # Check for recent files in Needs_Action
        recent_needs_action = False
        if NEEDS_ACTION_PATH.exists():
            for file in NEEDS_ACTION_PATH.glob("*"):
                if file.stat().st_mtime > time.time() - 600:  # 10 minutes
                    recent_needs_action = True
                    break

        # Determine status - consider system running if health monitor is active OR if there's recent activity
        status = "Online" if (recent_activity or recent_needs_action or ralph_recent or health_monitor_recent) else "Offline"

        # Determine last run time by checking latest log entry
        last_run = "Unknown"
        latest_mtime = 0
        if LOGS_PATH.exists():
            for log_file in LOGS_PATH.glob("*.json"):
                mtime = log_file.stat().st_mtime
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    last_run = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

        # Calculate uptime based on the most recent activity
        uptime = "Unknown"
        if latest_mtime > 0:
            uptime_seconds = time.time() - latest_mtime
            uptime = str(datetime.timedelta(seconds=int(uptime_seconds)))

        return {
            "status": status,
            "last_run": last_run,
            "uptime": uptime
        }
    except Exception as e:
        return {
            "status": "Error",
            "last_run": "Error",
            "uptime": "Error",
            "error": str(e)
        }


def get_watchers_status():
    """Get the status of various watchers"""
    try:
        # Check for recent Gmail activity
        gmail_last_check = "Unknown"
        if (VAULT_PATH / ".gmail_processed.json").exists():
            mtime = (VAULT_PATH / ".gmail_processed.json").stat().st_mtime
            gmail_last_check = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

        # Check for file system watcher activity
        file_watcher_status = "Active" if NEEDS_ACTION_PATH.exists() else "Inactive"

        return {
            "gmail_watcher": {
                "last_check": gmail_last_check
            },
            "file_watcher": {
                "status": file_watcher_status
            }
        }
    except Exception as e:
        return {
            "gmail_watcher": {"last_check": "Error", "error": str(e)},
            "file_watcher": {"status": "Error", "error": str(e)}
        }


def get_pending_tasks():
    """Get counts of pending tasks in various directories by sub-folder"""
    try:
        # Count files in each sub-folder of Needs_Action
        needs_action_email_count = len(list((NEEDS_ACTION_PATH / "Email").glob("*"))) if (NEEDS_ACTION_PATH / "Email").exists() else 0
        needs_action_social_count = len(list((NEEDS_ACTION_PATH / "Social").glob("*"))) if (NEEDS_ACTION_PATH / "Social").exists() else 0
        needs_action_finance_count = len(list((NEEDS_ACTION_PATH / "Finance").glob("*"))) if (NEEDS_ACTION_PATH / "Finance").exists() else 0

        # Total needs action count
        needs_action_total = needs_action_email_count + needs_action_social_count + needs_action_finance_count

        # Count files in each sub-folder of Pending_Approval
        pending_approval_email_count = len(list((PENDING_APPROVAL_PATH / "Email").glob("*"))) if (PENDING_APPROVAL_PATH / "Email").exists() else 0
        pending_approval_social_count = len(list((PENDING_APPROVAL_PATH / "Social").glob("*"))) if (PENDING_APPROVAL_PATH / "Social").exists() else 0
        pending_approval_finance_count = len(list((PENDING_APPROVAL_PATH / "Finance").glob("*"))) if (PENDING_APPROVAL_PATH / "Finance").exists() else 0

        # Total pending approval count
        pending_approval_total = pending_approval_email_count + pending_approval_social_count + pending_approval_finance_count

        # Drafts count
        drafts_count = len(list(DRAFTS_PATH.glob("*"))) if DRAFTS_PATH.exists() else 0

        return {
            "needs_action": {
                "total": needs_action_total,
                "email": needs_action_email_count,
                "social": needs_action_social_count,
                "finance": needs_action_finance_count
            },
            "pending_approval": {
                "total": pending_approval_total,
                "email": pending_approval_email_count,
                "social": pending_approval_social_count,
                "finance": pending_approval_finance_count
            },
            "drafts": drafts_count
        }
    except Exception as e:
        return {
            "needs_action": {
                "total": 0,
                "email": 0,
                "social": 0,
                "finance": 0
            },
            "pending_approval": {
                "total": 0,
                "email": 0,
                "social": 0,
                "finance": 0
            },
            "drafts": 0,
            "error": str(e)
        }


def get_recent_odoo_invoices():
    """Get recent Odoo invoices from logs"""
    try:
        invoices = []
        odoo_log_path = LOGS_PATH / "odoo_operations.json"

        if odoo_log_path.exists():
            with open(odoo_log_path, 'r') as f:
                try:
                    logs = json.load(f)
                    # Get last 5 drafts/posts
                    for log in reversed(logs[-5:]):
                        details = log.get("details", {})
                        invoices.append({
                            "timestamp": log.get("timestamp", "Unknown"),
                            "action": log.get("action", "Unknown"),
                            "status": log.get("status", "Unknown"),
                            "draft_id": details.get("draft_id", details.get("id", "Unknown"))
                        })
                except json.JSONDecodeError:
                    pass  # Handle empty or malformed JSON file

        return invoices
    except Exception as e:
        return [{"error": str(e)}]


def get_social_posts():
    """Get recent social media posts/drafts"""
    try:
        posts = []

        # Look for social operation logs
        social_log_path = LOGS_PATH / "social_operations.json"
        if social_log_path.exists():
            with open(social_log_path, 'r') as f:
                try:
                    logs = json.load(f)
                    # Get last 5 posts/drafts
                    for log in reversed(logs[-5:]):
                        operation = log.get("operation", {})
                        content = operation.get("content", operation.get("post", "No content"))
                        # Create a content snippet (first 50 chars)
                        content_snippet = (content[:50] + "...") if len(content) > 50 else content
                        posts.append({
                            "timestamp": log.get("timestamp", "Unknown"),
                            "platform": operation.get("platform", operation.get("social_platform", "Unknown")),
                            "content_snippet": content_snippet,
                            "status": operation.get("status", "Unknown")
                        })
                except json.JSONDecodeError:
                    pass  # Handle empty or malformed JSON file

        return posts
    except Exception as e:
        return [{"error": str(e)}]


def get_live_logs():
    """Get last 20 lines from social and odoo operation logs"""
    try:
        social_log_path = LOGS_PATH / "social_operations.json"
        odoo_log_path = LOGS_PATH / "odoo_operations.json"

        social_logs = []
        odoo_logs = []

        if social_log_path.exists():
            with open(social_log_path, 'r') as f:
                try:
                    logs = json.load(f)
                    # Get last 20 log entries
                    for log in reversed(logs[-20:]):
                        social_logs.append(f"[SOCIAL] {log.get('timestamp', 'Unknown')}: {log.get('operation', {})}")
                except json.JSONDecodeError:
                    social_logs.append("[SOCIAL] Error reading log file")

        if odoo_log_path.exists():
            with open(odoo_log_path, 'r') as f:
                try:
                    logs = json.load(f)
                    # Get last 20 log entries
                    for log in reversed(logs[-20:]):
                        odoo_logs.append(f"[ODOO] {log.get('timestamp', 'Unknown')}: {log.get('details', {})}")
                except json.JSONDecodeError:
                    odoo_logs.append("[ODOO] Error reading log file")

        return {
            "social": social_logs,
            "odoo": odoo_logs
        }
    except Exception as e:
        return {
            "social": [f"Error reading logs: {str(e)}"],
            "odoo": [f"Error reading logs: {str(e)}"]
        }


def get_system_health():
    """Get system health metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else psutil.disk_usage('.').percent

        # Get health monitor data
        health_summary = health_monitor.get_health_summary()

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_usage": disk_usage,
            "health_monitor_status": health_summary
        }
    except Exception as e:
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_usage": 0,
            "health_monitor_status": {},
            "error": str(e)
        }


def get_weekly_report():
    """Generate detailed weekly report with day-by-day breakdown"""
    try:
        from datetime import datetime, timedelta
        from collections import defaultdict

        # Get last 7 days
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        # Structure: {day: {hour: {activities: []}}}
        daily_activities = defaultdict(lambda: defaultdict(lambda: {'linkedin': 0, 'facebook': 0, 'twitter': 0, 'invoices': 0, 'emails': 0, 'activities': []}))

        # Read social operations
        social_log_path = LOGS_PATH / "social_operations.json"
        if social_log_path.exists():
            with open(social_log_path, 'r') as f:
                try:
                    logs = json.load(f)
                    for log in logs:
                        try:
                            timestamp_str = log.get("timestamp", "")
                            if timestamp_str:
                                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00') if 'Z' in timestamp_str else timestamp_str)
                                if log_time >= week_ago:
                                    day_name = log_time.strftime('%A')
                                    day_date = log_time.strftime('%Y-%m-%d')
                                    hour = log_time.strftime('%H:%M')

                                    operation = log.get("operation", {})
                                    platform = operation.get("platform", "unknown").lower()
                                    content = operation.get("content", operation.get("post", ""))[:50]

                                    day_key = f"{day_name}, {day_date}"

                                    if 'linkedin' in platform:
                                        daily_activities[day_key][hour]['linkedin'] += 1
                                    elif 'facebook' in platform:
                                        daily_activities[day_key][hour]['facebook'] += 1
                                    elif 'twitter' in platform:
                                        daily_activities[day_key][hour]['twitter'] += 1

                                    daily_activities[day_key][hour]['activities'].append({
                                        'time': hour,
                                        'type': 'social',
                                        'platform': platform.title(),
                                        'content': content,
                                        'status': operation.get('status', 'completed')
                                    })
                        except:
                            pass
                except json.JSONDecodeError:
                    pass

        # Read Odoo operations
        odoo_log_path = LOGS_PATH / "odoo_operations.json"
        if odoo_log_path.exists():
            with open(odoo_log_path, 'r') as f:
                try:
                    logs = json.load(f)
                    for log in logs:
                        try:
                            timestamp_str = log.get("timestamp", "")
                            if timestamp_str:
                                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00') if 'Z' in timestamp_str else timestamp_str)
                                if log_time >= week_ago:
                                    day_name = log_time.strftime('%A')
                                    day_date = log_time.strftime('%Y-%m-%d')
                                    hour = log_time.strftime('%H:%M')

                                    day_key = f"{day_name}, {day_date}"

                                    if 'invoice' in log.get('action', '').lower():
                                        daily_activities[day_key][hour]['invoices'] += 1
                                        details = log.get('details', {})
                                        daily_activities[day_key][hour]['activities'].append({
                                            'time': hour,
                                            'type': 'invoice',
                                            'platform': 'Odoo',
                                            'content': f"Invoice #{details.get('draft_id', 'N/A')} - Rs. {details.get('amount', 0)}",
                                            'status': log.get('status', 'pending')
                                        })
                        except:
                            pass
                except json.JSONDecodeError:
                    pass

        # Convert to sorted list
        weekly_data = []
        for day in sorted(daily_activities.keys(), reverse=True):
            day_summary = {
                'day': day,
                'total_linkedin': sum(h['linkedin'] for h in daily_activities[day].values()),
                'total_facebook': sum(h['facebook'] for h in daily_activities[day].values()),
                'total_twitter': sum(h['twitter'] for h in daily_activities[day].values()),
                'total_invoices': sum(h['invoices'] for h in daily_activities[day].values()),
                'hourly_activities': []
            }

            for hour in sorted(daily_activities[day].keys()):
                if daily_activities[day][hour]['activities']:
                    day_summary['hourly_activities'].append({
                        'hour': hour,
                        'activities': daily_activities[day][hour]['activities']
                    })

            weekly_data.append(day_summary)

        return weekly_data
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        return []


def get_predictive_insights():
    """Calculate predictive insights from logs"""
    try:
        # Calculate weekly revenue forecast
        revenue_this_week = 0
        revenue_last_week = 0
        forecast_next_week = 0

        odoo_log_path = LOGS_PATH / "odoo_operations.json"
        if odoo_log_path.exists():
            import calendar
            from datetime import datetime, timedelta

            with open(odoo_log_path, 'r') as f:
                try:
                    logs = json.load(f)

                    # Get current week and last week
                    now = datetime.now()
                    current_week_start = now - timedelta(days=now.weekday())
                    last_week_start = current_week_start - timedelta(weeks=1)

                    for log in logs:
                        try:
                            timestamp_str = log.get("timestamp", "")
                            if timestamp_str:
                                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00') if 'Z' in timestamp_str else timestamp_str)

                                # Check if this is a completed invoice that earned revenue
                                if log.get("action") == "invoice_posted" and log.get("status") == "success":
                                    amount = log.get("details", {}).get("amount", 0)
                                    if amount and isinstance(amount, (int, float)):
                                        if log_time >= current_week_start:
                                            revenue_this_week += amount
                                        elif log_time >= last_week_start and log_time < current_week_start:
                                            revenue_last_week += amount
                        except (ValueError, TypeError):
                            continue

                    # Simple moving average forecast
                    if revenue_last_week > 0:
                        forecast_next_week = revenue_last_week
                    elif revenue_this_week > 0:
                        forecast_next_week = revenue_this_week
                except json.JSONDecodeError:
                    pass  # Handle empty or malformed JSON file

        # Bottleneck detection - tasks pending > 3 days in Pending_Approval
        bottleneck_count = 0
        pending_approval_path = PENDING_APPROVAL_PATH
        if pending_approval_path.exists():
            three_days_ago = time.time() - (3 * 24 * 60 * 60)  # 3 days in seconds

            # Count files in subfolders too
            for subfolder in ['Email', 'Social', 'Finance']:
                subfolder_path = pending_approval_path / subfolder
                if subfolder_path.exists():
                    for file in subfolder_path.glob("*"):
                        if file.stat().st_mtime < three_days_ago:  # Older than 3 days
                            bottleneck_count += 1

            # Also check main directory
            for file in pending_approval_path.glob("*"):
                if file.is_file() and file.stat().st_mtime < three_days_ago:
                    bottleneck_count += 1

        # Suggestions based on analysis
        suggestions = []

        # Check if there are bottlenecks
        if bottleneck_count > 0:
            suggestions.append(f"Clean up {bottleneck_count} tasks in Pending Approval older than 3 days")

        # Check recent social posts to analyze engagement
        social_log_path = LOGS_PATH / "social_operations.json"
        low_engagement_detected = False

        if social_log_path.exists():
            with open(social_log_path, 'r') as f:
                try:
                    logs = json.load(f)

                    # Count recent LinkedIn posts
                    linkedin_count = 0
                    recent_logs = logs[-20:] if len(logs) > 20 else logs  # Check last 20 logs

                    for log in recent_logs:
                        operation = log.get("operation", {})
                        platform = operation.get("platform", "")
                        if platform and "linkedin" in platform.lower():
                            linkedin_count += 1

                    # If very few LinkedIn posts in recent activity, suggest more
                    if linkedin_count < 3:
                        suggestions.append("Consider posting more on LinkedIn based on recent activity")

                except json.JSONDecodeError:
                    pass  # Handle empty or malformed JSON file

        # Check for overdue invoices
        overdue_count = 0
        if odoo_log_path.exists():
            with open(odoo_log_path, 'r') as f:
                try:
                    logs = json.load(f)

                    # Look for pending invoices that might be overdue
                    for log in logs[-10:]:  # Check recent logs
                        if log.get("action") == "process_pending_invoice" and log.get("status") == "error":
                            overdue_count += 1

                    if overdue_count > 0:
                        suggestions.append(f"Follow up on {overdue_count} potentially overdue invoices")

                except json.JSONDecodeError:
                    pass  # Handle empty or malformed JSON file

        # Default suggestions if no specific issues found
        if not suggestions:
            suggestions.append("System running smoothly - no immediate actions required")
            if revenue_this_week == 0:
                suggestions.append("Consider focusing on generating new revenue this week")

        return {
            "revenue_this_week": round(revenue_this_week, 2),
            "revenue_last_week": round(revenue_last_week, 2),
            "forecast_next_week": round(forecast_next_week, 2),
            "bottleneck_count": bottleneck_count,
            "suggestions": suggestions
        }
    except Exception as e:
        return {
            "revenue_this_week": 0,
            "revenue_last_week": 0,
            "forecast_next_week": 0,
            "bottleneck_count": 0,
            "suggestions": [f"Error calculating insights: {str(e)}"],
            "error": str(e)
        }




@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Log to file for debugging
        with open('vault/Logs/login_debug.log', 'a') as f:
            f.write(f"\n=== Login Attempt at {datetime.now()} ===\n")
            f.write(f"Username: {username}\n")
            f.write(f"Password length: {len(password)}\n")

        users = get_users()

        with open('vault/Logs/login_debug.log', 'a') as f:
            f.write(f"Loaded users: {list(users.keys())}\n")

        user_data = None
        user_id = None

        # Find user by username
        for uid, data in users.items():
            if data['username'] == username:
                user_data = data
                user_id = uid
                with open('vault/Logs/login_debug.log', 'a') as f:
                    f.write(f"User found: {uid}\n")
                break

        if user_data:
            with open('vault/Logs/login_debug.log', 'a') as f:
                f.write(f"Stored hash: {user_data['password']}\n")

            password_match = bcrypt.check_password_hash(user_data['password'], password)

            with open('vault/Logs/login_debug.log', 'a') as f:
                f.write(f"Password match result: {password_match}\n")

            if password_match:
                user = User(user_id, user_data['username'], user_data['role'])
                login_user(user)
                with open('vault/Logs/login_debug.log', 'a') as f:
                    f.write(f"Login successful!\n")
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                with open('vault/Logs/login_debug.log', 'a') as f:
                    f.write(f"Password mismatch!\n")
                flash('Invalid username or password')
        else:
            with open('vault/Logs/login_debug.log', 'a') as f:
                f.write(f"User not found!\n")
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout route"""
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    """Main dashboard page - requires login"""
    return render_template('index.html')


@app.route('/api/status')
@login_required
def api_status():
    """API endpoint for real-time status updates - requires login"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "ai_employee": get_ai_employee_status(),
        "watchers": get_watchers_status(),
        "pending_tasks": get_pending_tasks(),
        "recent_odoo_invoices": get_recent_odoo_invoices(),
        "social_posts": get_social_posts(),
        "live_logs": get_live_logs(),
        "system_health": get_system_health()
    }
    return jsonify(data)


@app.route('/api/health-alerts')
@login_required
def api_health_alerts():
    """API endpoint for health alerts - requires login"""
    alerts = health_monitor.get_recent_alerts()
    return jsonify({
        "alerts": alerts,
        "summary": health_monitor.get_health_summary()
    })


@app.route('/api/predictive')
@login_required
def api_predictive():
    """API endpoint for predictive analytics - requires login"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "predictive_insights": get_predictive_insights()
    }
    return jsonify(data)


@app.route('/api/weekly-report')
@login_required
def api_weekly_report():
    """API endpoint for detailed weekly report - requires login"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "weekly_report": get_weekly_report()
    }
    return jsonify(data)


def check_role(required_role):
    """Check if current user has required role"""
    if current_user.role == required_role:
        return True
    elif required_role == 'Admin' and current_user.role == 'Approver':
        return True  # Approver can also do admin actions (for this implementation)
    return False


@app.route('/api/user')
@login_required
def api_user():
    """API endpoint to get current user info - requires login"""
    return jsonify({
        'username': current_user.username,
        'role': current_user.role
    })


@app.route('/api/check_role/<role>')
@login_required
def check_user_role(role):
    """API endpoint to check if user has specific role - requires login"""
    has_role = check_role(role)
    return jsonify({
        'has_role': has_role,
        'user_role': current_user.role
    })


@app.route('/api/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    """API endpoint to manage users - requires Admin or Approver role"""
    if not check_role('Admin') and not check_role('Approver'):
        return jsonify({'error': 'Permission denied'}), 403

    if request.method == 'GET':
        # Return user list (excluding passwords for security)
        users = get_users()
        users_list = []
        for user_id, user_data in users.items():
            users_list.append({
                'id': user_id,
                'username': user_data['username'],
                'role': user_data['role']
            })
        return jsonify({'users': users_list})

    elif request.method == 'POST':
        # Create new user (only Admin can do this)
        if not check_role('Admin'):
            return jsonify({'error': 'Permission denied - only Admin can create users'}), 403

        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

        if not username or not password or not role:
            return jsonify({'error': 'Username, password, and role are required'}), 400

        if role not in ['Admin', 'Approver', 'Viewer']:
            return jsonify({'error': 'Invalid role. Must be Admin, Approver, or Viewer'}), 400

        # Check if username already exists
        users = get_users()
        for user_data in users.values():
            if user_data['username'] == username:
                return jsonify({'error': 'Username already exists'}), 400

        # Create new user
        user_id = str(len(users) + 1)  # Simple ID generation
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        users[user_id] = {
            'username': username,
            'password': hashed_password,
            'role': role
        }

        save_users(users)
        return jsonify({'message': 'User created successfully'}), 201


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    # Create the index.html template
    template_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Employee Platinum Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {
            background-color: #f8f9fa;
        }
        .card {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .row {
            display: flex;
            flex-wrap: wrap;
        }
        .col-6 {
            flex: 0 0 50%;
            max-width: 50%;
        }
        .status-badge {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .status-online { background-color: #d4edda; color: #155724; }
        .status-offline { background-color: #f8d7da; color: #721c24; }
        .status-error { background-color: #f8d7da; color: #721c24; }
        .status-active { background-color: #d4edda; color: #155724; }
        .status-inactive { background-color: #f8d7da; color: #721c24; }
        .cpu-high { background-color: #f8d7da; color: #721c24; }
        .cpu-medium { background-color: #fff3cd; color: #856404; }
        .cpu-low { background-color: #d4edda; color: #155724; }
        .progress-high { background-color: #dc3545; }
        .progress-medium { background-color: #ffc107; }
        .progress-low { background-color: #28a745; }
        .log-entry {
            font-family: monospace;
            font-size: 0.9em;
            padding: 2px 5px;
            border-bottom: 1px solid #eee;
        }
        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 0;
            margin-bottom: 30px;
        }
        .metric-card {
            text-align: center;
            padding: 20px;
        }
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .metric-title {
            font-size: 1em;
            color: #6c757d;
        }
        .refresh-indicator {
            position: fixed;
            top: 10px;
            right: 10px;
            background: #007bff;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.8em;
            display: none;
        }
        .alert-item {
            border-left: 4px solid;
            margin-bottom: 10px;
            padding: 10px;
        }
        .alert-warning {
            border-left-color: #ffc107;
            background-color: #fff3cd;
        }
        .alert-danger {
            border-left-color: #dc3545;
            background-color: #f8d7da;
        }
        .alert-info {
            border-left-color: #17a2b8;
            background-color: #d1ecf1;
        }
        .health-badge {
            font-size: 0.8em;
            padding: 3px 8px;
            border-radius: 12px;
            margin-left: 5px;
        }
        .health-good { background-color: #d4edda; color: #155724; }
        .health-warning { background-color: #fff3cd; color: #856404; }
        .health-critical { background-color: #f8d7da; color: #721c24; }
        .logs-container {
            max-height: 450px;
            overflow-y: auto;
        }
        .card-body-scrollable {
            max-height: 350px;
            overflow-y: auto;
        }
        .metric-breakdown {
            font-size: 0.75em;
            color: #6c757d;
            margin-top: 10px;
        }
        @media (max-width: 768px) {
            .dashboard-header h1 {
                font-size: 1.5em;
            }
            .metric-value {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="refresh-indicator" id="refreshIndicator">Refreshing data...</div>

    <div class="dashboard-header">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h1 class="text-center mb-0">
                        <i class="fas fa-robot me-2"></i>
                        AI Employee Platinum Dashboard
                    </h1>
                    <p class="text-center mb-0 mt-2">Real-time monitoring of your AI employee system</p>
                </div>
                <div class="text-end">
                    <div id="userInfo" class="text-white">
                        <small>Loading...</small>
                    </div>
                    <a href="/logout" class="btn btn-outline-light btn-sm mt-2">
                        <i class="fas fa-sign-out-alt me-1"></i>Logout
                    </a>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- AI Employee Status - Visible to all roles -->
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title"><i class="fas fa-cogs me-2"></i>AI Employee Status</h5>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="status-badge status-offline" id="aiStatus">Offline</span>
                            <small class="text-muted">Last run: <span id="aiLastRun">Unknown</span></small>
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">Uptime: <span id="aiUptime">Unknown</span></small>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Watchers Status - Visible to all roles -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title"><i class="fas fa-eye me-2"></i>Watchers Status</h5>
                        <div class="mb-2">
                            <strong>Gmail:</strong>
                            <small class="text-muted">Last check: <span id="gmailLastCheck">Never</span></small>
                        </div>
                        <div>
                            <strong>File System:</strong>
                            <span class="status-badge status-inactive" id="fileWatcherStatus">Inactive</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- System Health - Visible to Approver and Admin only -->
            <div class="col-md-4" id="systemHealthSection">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title"><i class="fas fa-heartbeat me-2"></i>System Health</h5>
                        <div class="mb-2">
                            <div class="d-flex justify-content-between">
                                <span>CPU Usage</span>
                                <span id="cpuPercent">0%</span>
                            </div>
                            <div class="progress" style="height: 10px;">
                                <div class="progress-bar progress-low" id="cpuBar" role="progressbar" style="width: 0%"></div>
                            </div>
                        </div>
                        <div class="mb-2">
                            <div class="d-flex justify-content-between">
                                <span>Memory</span>
                                <span id="memoryPercent">0%</span>
                            </div>
                            <div class="progress" style="height: 10px;">
                                <div class="progress-bar progress-low" id="memoryBar" role="progressbar" style="width: 0%"></div>
                            </div>
                        </div>
                        <div>
                            <div class="d-flex justify-content-between">
                                <span>Disk</span>
                                <span id="diskUsage">0%</span>
                            </div>
                            <div class="progress" style="height: 10px;">
                                <div class="progress-bar progress-low" id="diskBar" role="progressbar" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Health & Alerts - Visible to Approver and Admin only -->
        <div class="row mb-4" id="healthAlertsSection">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header bg-warning text-dark">
                        <i class="fas fa-shield-alt me-2"></i>System Health & Alerts
                        <span id="systemHealthBadge" class="health-badge health-good">Healthy</span>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-3">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <h5>Processes</h5>
                                        <h3 id="processesCount">0</h3>
                                        <small class="text-muted">Running</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <h5>Load Avg</h5>
                                        <h3 id="loadAvg">0.0</h3>
                                        <small class="text-muted">1 min</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <h5>Alerts</h5>
                                        <h3 id="alertsCount">0</h3>
                                        <small class="text-muted">Recent</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <h5>Issues</h5>
                                        <h3 id="issuesCount">0</h3>
                                        <small class="text-muted">Active</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="mt-3">
                            <h6>Recent Alerts</h6>
                            <div id="recentAlerts" class="border rounded p-2">
                                <div class="text-center text-muted py-2">Loading alerts...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Pending Tasks -->
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="card metric-card">
                    <div class="metric-value" id="needsActionCount">0</div>
                    <div class="metric-title">Needs Action</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card metric-card">
                    <div class="metric-value" id="pendingApprovalCount">0</div>
                    <div class="metric-title">Pending Approval</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card metric-card">
                    <div class="metric-value" id="draftsCount">0</div>
                    <div class="metric-title">Drafts</div>
                </div>
            </div>
        </div>

        <!-- Recent Invoices and Social Posts -->
        <div class="row g-3 mb-4" id="financialAndSocialSection" style="display: flex !important; flex-wrap: wrap !important;">
            <div class="col-6" style="flex: 0 0 50% !important; max-width: 50% !important; padding: 0 15px !important;">
                <div class="card h-100">
                    <div class="card-header bg-primary text-white">
                        <i class="fas fa-file-invoice-dollar me-2"></i>Recent Odoo Invoices
                    </div>
                    <div class="card-body card-body-scrollable">
                        <div id="recentInvoices">
                            <div class="text-center text-muted py-4">Loading...</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-6" style="flex: 0 0 50% !important; max-width: 50% !important; padding: 0 15px !important;">
                <div class="card h-100">
                    <div class="card-header bg-info text-white">
                        <i class="fas fa-share-alt me-2"></i>Social Posts
                    </div>
                    <div class="card-body card-body-scrollable">
                        <div id="socialPosts">
                            <div class="text-center text-muted py-4">Loading...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Predictive Insights & Weekly Report - Visible to Approver and Admin only -->
        <div class="row mb-4" id="predictiveSection">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-purple text-white" style="background: linear-gradient(135deg, #6f42c1, #667eea);">
                        <i class="fas fa-chart-line me-2"></i>Predictive Insights & Weekly Report
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-md-3 mb-3">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <h3 class="text-primary" id="revenueThisWeek">$0.00</h3>
                                        <p class="card-text">Revenue This Week</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3 mb-3">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <h3 class="text-success" id="forecastNextWeek">$0.00</h3>
                                        <p class="card-text">Forecast Next Week</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3 mb-3">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <h3 class="text-warning" id="bottleneckCount">0</h3>
                                        <p class="card-text">Bottlenecks</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3 mb-3">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <h3 class="text-info" id="suggestionsCount">0</h3>
                                        <p class="card-text">Suggestions</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-12">
                                <h5>Suggested Actions</h5>
                                <ul class="list-group" id="suggestionsList">
                                    <li class="list-group-item text-center text-muted">Loading suggestions...</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Weekly Activity Report - Beautiful Day-by-Day Breakdown -->
        <div class="row mb-4" id="weeklyReportSection">
            <div class="col-12">
                <div class="card">
                    <div class="card-header text-white" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <i class="fas fa-calendar-week me-2"></i>Weekly Activity Report - Day by Day
                    </div>
                    <div class="card-body">
                        <div id="weeklyReportContent">
                            <div class="text-center text-muted py-4">Loading weekly report...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Live Logs - Visible to Approver and Admin only -->
        <div class="row g-3 mb-4" id="logsSection" style="display: flex !important; flex-wrap: wrap !important;">
            <div class="col-6" style="flex: 0 0 50% !important; max-width: 50% !important; padding: 0 15px !important;">
                <div class="card h-100">
                    <div class="card-header bg-success text-white">
                        <i class="fas fa-rss me-2"></i>Live Social Logs
                    </div>
                    <div class="card-body p-0">
                        <div class="list-group list-group-flush logs-container" id="socialLogs">
                            <div class="text-center text-muted py-4">Loading...</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-6" style="flex: 0 0 50% !important; max-width: 50% !important; padding: 0 15px !important;">
                <div class="card h-100">
                    <div class="card-header bg-warning text-dark">
                        <i class="fas fa-database me-2"></i>Live Odoo Logs
                    </div>
                    <div class="card-body p-0">
                        <div class="list-group list-group-flush logs-container" id="odooLogs">
                            <div class="text-center text-muted py-4">Loading...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let refreshInterval;

        // Get user information
        function updateUserInfo() {
            fetch('/api/user')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('userInfo').innerHTML = `
                        <small><i class="fas fa-user me-1"></i> ${data.username} (${data.role})</small>
                    `;

                    // Show/hide sections based on role
                    const userRole = data.role;
                    const systemHealthSection = document.getElementById('systemHealthSection');
                    const healthAlertsSection = document.getElementById('healthAlertsSection');
                    const financialAndSocialSection = document.getElementById('financialAndSocialSection');
                    const predictiveSection = document.getElementById('predictiveSection');
                    const logsSection = document.getElementById('logsSection');

                    if (userRole === 'Viewer') {
                        // Hide system health, health alerts, financial/social posts, predictive insights, and logs for viewers
                        if (systemHealthSection) systemHealthSection.style.display = 'none';
                        if (healthAlertsSection) healthAlertsSection.style.display = 'none';
                        if (financialAndSocialSection) financialAndSocialSection.style.display = 'none';
                        if (predictiveSection) predictiveSection.style.display = 'none';
                        if (logsSection) logsSection.style.display = 'none';
                    } else {
                        // For Admin and Approver, show all sections
                        if (systemHealthSection) systemHealthSection.style.display = 'block';
                        if (healthAlertsSection) healthAlertsSection.style.display = 'block';
                        if (financialAndSocialSection) financialAndSocialSection.style.display = 'flex';
                        if (predictiveSection) predictiveSection.style.display = 'block';
                        if (logsSection) logsSection.style.display = 'flex';
                    }
                })
                .catch(error => {
                    console.error('Error getting user info:', error);
                });
        }

        function updateDashboard() {
            document.getElementById('refreshIndicator').style.display = 'block';

            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update AI Employee Status
                    const aiStatus = data.ai_employee.status;
                    document.getElementById('aiStatus').textContent = aiStatus;
                    document.getElementById('aiStatus').className = 'status-badge ' +
                        (aiStatus === 'Online' ? 'status-online' : 'status-offline');
                    document.getElementById('aiLastRun').textContent = data.ai_employee.last_run;
                    document.getElementById('aiUptime').textContent = data.ai_employee.uptime;

                    // Update Watchers Status
                    document.getElementById('gmailLastCheck').textContent = data.watchers.gmail_watcher.last_check;
                    const fileStatus = data.watchers.file_watcher.status;
                    document.getElementById('fileWatcherStatus').textContent = fileStatus;
                    document.getElementById('fileWatcherStatus').className = 'status-badge ' +
                        (fileStatus === 'Active' ? 'status-active' : 'status-inactive');

                    // Update Pending Tasks
                    document.getElementById('needsActionCount').innerHTML =
                        `<div class="text-center">${data.pending_tasks.needs_action.total}</div>
                         <small class="text-muted d-block">Email: ${data.pending_tasks.needs_action.email} | Social: ${data.pending_tasks.needs_action.social} | Finance: ${data.pending_tasks.needs_action.finance}</small>`;
                    document.getElementById('pendingApprovalCount').innerHTML =
                        `<div class="text-center">${data.pending_tasks.pending_approval.total}</div>
                         <small class="text-muted d-block">Email: ${data.pending_tasks.pending_approval.email} | Social: ${data.pending_tasks.pending_approval.social} | Finance: ${data.pending_tasks.pending_approval.finance}</small>`;
                    document.getElementById('draftsCount').textContent = data.pending_tasks.drafts;

                    // Update System Health
                    const cpu = data.system_health.cpu_percent;
                    const memory = data.system_health.memory_percent;
                    const disk = data.system_health.disk_usage;

                    document.getElementById('cpuPercent').textContent = cpu + '%';
                    document.getElementById('memoryPercent').textContent = memory + '%';
                    document.getElementById('diskUsage').textContent = disk + '%';

                    // Update CPU bar
                    const cpuBar = document.getElementById('cpuBar');
                    cpuBar.style.width = cpu + '%';
                    cpuBar.className = 'progress-bar ' +
                        (cpu > 80 ? 'progress-high' : cpu > 50 ? 'progress-medium' : 'progress-low');

                    // Update Memory bar
                    const memoryBar = document.getElementById('memoryBar');
                    memoryBar.style.width = memory + '%';
                    memoryBar.className = 'progress-bar ' +
                        (memory > 80 ? 'progress-high' : memory > 50 ? 'progress-medium' : 'progress-low');

                    // Update Disk bar
                    const diskBar = document.getElementById('diskBar');
                    diskBar.style.width = disk + '%';
                    diskBar.className = 'progress-bar ' +
                        (disk > 80 ? 'progress-high' : disk > 50 ? 'progress-medium' : 'progress-low');

                    // Update Recent Invoices
                    const invoicesDiv = document.getElementById('recentInvoices');
                    if (data.recent_odoo_invoices && data.recent_odoo_invoices.length > 0) {
                        invoicesDiv.innerHTML = '';
                        data.recent_odoo_invoices.forEach(invoice => {
                            const invoiceDiv = document.createElement('div');
                            invoiceDiv.className = 'border-bottom pb-2 mb-2';
                            invoiceDiv.innerHTML = `
                                <small class="text-muted">${invoice.timestamp}</small>
                                <div><strong>Action:</strong> ${invoice.action}</div>
                                <div><strong>Status:</strong> ${invoice.status}</div>
                                <div><strong>Draft ID:</strong> ${invoice.draft_id}</div>
                            `;
                            invoicesDiv.appendChild(invoiceDiv);
                        });
                    } else {
                        invoicesDiv.innerHTML = '<div class="text-center text-muted">No recent invoices</div>';
                    }

                    // Update Social Posts
                    const socialDiv = document.getElementById('socialPosts');
                    if (data.social_posts && data.social_posts.length > 0) {
                        socialDiv.innerHTML = '';
                        data.social_posts.forEach(post => {
                            const postDiv = document.createElement('div');
                            postDiv.className = 'border-bottom pb-2 mb-2';
                            postDiv.innerHTML = `
                                <small class="text-muted">${post.timestamp}</small>
                                <div><strong>Platform:</strong> ${post.platform}</div>
                                <div><strong>Content:</strong> ${post.content_snippet}</div>
                                <div><strong>Status:</strong> ${post.status}</div>
                            `;
                            socialDiv.appendChild(postDiv);
                        });
                    } else {
                        socialDiv.innerHTML = '<div class="text-center text-muted">No recent posts</div>';
                    }

                    // Update Social Logs
                    const socialLogsDiv = document.getElementById('socialLogs');
                    if (data.live_logs.social && data.live_logs.social.length > 0) {
                        socialLogsDiv.innerHTML = '';
                        data.live_logs.social.forEach(log => {
                            const logDiv = document.createElement('div');
                            logDiv.className = 'list-group-item log-entry';
                            logDiv.textContent = log;
                            socialLogsDiv.appendChild(logDiv);
                        });
                    } else {
                        socialLogsDiv.innerHTML = '<div class="list-group-item text-center text-muted">No logs</div>';
                    }

                    // Update Odoo Logs
                    const odooLogsDiv = document.getElementById('odooLogs');
                    if (data.live_logs.odoo && data.live_logs.odoo.length > 0) {
                        odooLogsDiv.innerHTML = '';
                        data.live_logs.odoo.forEach(log => {
                            const logDiv = document.createElement('div');
                            logDiv.className = 'list-group-item log-entry';
                            logDiv.textContent = log;
                            odooLogsDiv.appendChild(logDiv);
                        });
                    } else {
                        odooLogsDiv.innerHTML = '<div class="list-group-item text-center text-muted">No logs</div>';
                    }

                    // Update Health Monitor Data
                    if (data.system_health.health_monitor_status) {
                        const healthStatus = data.system_health.health_monitor_status;
                        const currentHealth = healthStatus.current_health;

                        if (currentHealth) {
                            document.getElementById('processesCount').textContent = currentHealth.processes_count || '0';

                            // Show first load average value
                            if (currentHealth.load_average && currentHealth.load_average.length > 0) {
                                document.getElementById('loadAvg').textContent = currentHealth.load_average[0].toFixed(2);
                            }

                            // Update health badge based on system status
                            const healthBadge = document.getElementById('systemHealthBadge');
                            if (healthStatus.is_system_healthy) {
                                healthBadge.textContent = 'Healthy';
                                healthBadge.className = 'health-badge health-good';
                            } else {
                                healthBadge.textContent = 'Issues Found';
                                healthBadge.className = 'health-badge health-critical';
                            }

                            // Update alert counts
                            document.getElementById('alertsCount').textContent = healthStatus.total_alerts_count || '0';

                            // Count active issues
                            const activeIssues = healthStatus.recent_alerts ?
                                healthStatus.recent_alerts.filter(alert =>
                                    alert.severity === 'alert' || alert.severity === 'critical'
                                ).length : 0;
                            document.getElementById('issuesCount').textContent = activeIssues;
                        }

                        // Update recent alerts display
                        const alertsDiv = document.getElementById('recentAlerts');
                        if (healthStatus.recent_alerts && healthStatus.recent_alerts.length > 0) {
                            alertsDiv.innerHTML = '';
                            // Show last 5 alerts
                            const recentAlerts = healthStatus.recent_alerts.slice(-5).reverse();
                            recentAlerts.forEach(alert => {
                                const alertDiv = document.createElement('div');
                                let alertClass = 'alert-info';
                                if (alert.severity === 'warning') alertClass = 'alert-warning';
                                if (alert.severity === 'alert' || alert.severity === 'critical') alertClass = 'alert-danger';

                                alertDiv.className = `alert-item ${alertClass}`;
                                alertDiv.innerHTML = `
                                    <strong>${alert.type.replace('_', ' ').toUpperCase()}</strong>
                                    <small class="float-end">${new Date(alert.timestamp).toLocaleTimeString()}</small>
                                    <div>${alert.message}</div>
                                `;
                                alertsDiv.appendChild(alertDiv);
                            });
                        } else {
                            alertsDiv.innerHTML = '<div class="text-center text-muted py-2">No recent alerts</div>';
                        }
                    }

                    document.getElementById('refreshIndicator').style.display = 'none';
                })
                .catch(error => {
                    console.error('Error updating dashboard:', error);
                    document.getElementById('refreshIndicator').style.display = 'none';
                });
        }

        // Initial load
        updateDashboard();
        updateUserInfo();

        function updatePredictiveAnalytics() {
            fetch('/api/predictive')
                .then(response => response.json())
                .then(data => {
                    const insights = data.predictive_insights;

                    // Update revenue information
                    document.getElementById('revenueThisWeek').textContent = '$' + insights.revenue_this_week.toFixed(2);
                    document.getElementById('forecastNextWeek').textContent = '$' + insights.forecast_next_week.toFixed(2);
                    document.getElementById('bottleneckCount').textContent = insights.bottleneck_count;
                    document.getElementById('suggestionsCount').textContent = insights.suggestions.length;

                    // Update suggestions list
                    const suggestionsList = document.getElementById('suggestionsList');
                    if (insights.suggestions && insights.suggestions.length > 0) {
                        suggestionsList.innerHTML = '';
                        insights.suggestions.forEach(suggestion => {
                            const suggestionItem = document.createElement('li');
                            suggestionItem.className = 'list-group-item';
                            suggestionItem.textContent = suggestion;
                            suggestionsList.appendChild(suggestionItem);
                        });
                    } else {
                        suggestionsList.innerHTML = '<li class="list-group-item text-center text-muted">No suggestions at this time</li>';
                    }
                })
                .catch(error => {
                    console.error('Error updating predictive analytics:', error);
                });
        }

        // Initial load for predictive analytics
        updatePredictiveAnalytics();

        function updateWeeklyReport() {
            fetch('/api/weekly-report')
                .then(response => response.json())
                .then(data => {
                    const weeklyData = data.weekly_report;
                    const reportContent = document.getElementById('weeklyReportContent');

                    if (weeklyData && weeklyData.length > 0) {
                        reportContent.innerHTML = '';

                        weeklyData.forEach(day => {
                            const dayCard = document.createElement('div');
                            dayCard.className = 'card mb-3';
                            dayCard.style.borderLeft = '5px solid #667eea';

                            // Day header with summary
                            const dayHeader = `
                                <div class="card-header" style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);">
                                    <div class="row align-items-center">
                                        <div class="col-md-6">
                                            <h5 class="mb-0"><i class="fas fa-calendar-day me-2"></i>${day.day}</h5>
                                        </div>
                                        <div class="col-md-6 text-end">
                                            <span class="badge bg-primary me-1"><i class="fab fa-linkedin me-1"></i>${day.total_linkedin}</span>
                                            <span class="badge bg-info me-1"><i class="fab fa-facebook me-1"></i>${day.total_facebook}</span>
                                            <span class="badge bg-info me-1"><i class="fab fa-twitter me-1"></i>${day.total_twitter}</span>
                                            <span class="badge bg-success"><i class="fas fa-file-invoice me-1"></i>${day.total_invoices}</span>
                                        </div>
                                    </div>
                                </div>
                            `;

                            dayCard.innerHTML = dayHeader;

                            // Day body with hourly activities
                            const dayBody = document.createElement('div');
                            dayBody.className = 'card-body';

                            if (day.hourly_activities && day.hourly_activities.length > 0) {
                                day.hourly_activities.forEach(hourBlock => {
                                    const hourDiv = document.createElement('div');
                                    hourDiv.className = 'mb-3 pb-3 border-bottom';

                                    hourDiv.innerHTML = `<h6 class="text-muted"><i class="fas fa-clock me-2"></i>${hourBlock.hour}</h6>`;

                                    const activitiesList = document.createElement('div');
                                    activitiesList.className = 'ms-4';

                                    hourBlock.activities.forEach(activity => {
                                        const activityItem = document.createElement('div');
                                        activityItem.className = 'mb-2 p-2 rounded';

                                        let bgColor = '#f8f9fa';
                                        let icon = 'fa-circle';
                                        let iconColor = '#6c757d';

                                        if (activity.type === 'social') {
                                            if (activity.platform.toLowerCase().includes('linkedin')) {
                                                bgColor = '#e7f3ff';
                                                icon = 'fab fa-linkedin';
                                                iconColor = '#0077b5';
                                            } else if (activity.platform.toLowerCase().includes('facebook')) {
                                                bgColor = '#e7f3ff';
                                                icon = 'fab fa-facebook';
                                                iconColor = '#1877f2';
                                            } else if (activity.platform.toLowerCase().includes('twitter')) {
                                                bgColor = '#e7f3ff';
                                                icon = 'fab fa-twitter';
                                                iconColor = '#1da1f2';
                                            }
                                        } else if (activity.type === 'invoice') {
                                            bgColor = '#d4edda';
                                            icon = 'fa-file-invoice-dollar';
                                            iconColor = '#28a745';
                                        }

                                        activityItem.style.backgroundColor = bgColor;
                                        activityItem.innerHTML = `
                                            <div class="d-flex align-items-start">
                                                <i class="${icon} me-2" style="color: ${iconColor}; margin-top: 3px;"></i>
                                                <div class="flex-grow-1">
                                                    <strong>${activity.platform}</strong>
                                                    <div class="small text-muted">${activity.content}...</div>
                                                    <span class="badge badge-sm ${activity.status === 'completed' ? 'bg-success' : activity.status === 'pending' ? 'bg-warning' : 'bg-secondary'}">${activity.status}</span>
                                                </div>
                                            </div>
                                        `;

                                        activitiesList.appendChild(activityItem);
                                    });

                                    hourDiv.appendChild(activitiesList);
                                    dayBody.appendChild(hourDiv);
                                });
                            } else {
                                dayBody.innerHTML = '<p class="text-muted text-center">No activities recorded for this day</p>';
                            }

                            dayCard.appendChild(dayBody);
                            reportContent.appendChild(dayCard);
                        });
                    } else {
                        reportContent.innerHTML = '<div class="text-center text-muted py-4">No weekly data available</div>';
                    }
                })
                .catch(error => {
                    console.error('Error updating weekly report:', error);
                });
        }

        // Initial load for weekly report
        updateWeeklyReport();

        // Set up auto-refresh every 5 seconds for both main dashboard and predictive analytics
        refreshInterval = setInterval(function() {
            updateDashboard();
            updatePredictiveAnalytics();
            updateWeeklyReport();
        }, 5000);

        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            clearInterval(refreshInterval);
        });
    </script>
</body>
</html>"""

    template_file = templates_dir / "index.html"
    template_file.write_text(template_content)

    print("Starting Platinum Tier Dashboard on http://localhost:5000")
    app.run(host='localhost', port=5000, debug=False)