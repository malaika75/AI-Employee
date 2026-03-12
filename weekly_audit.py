import os
import json
import datetime
from datetime import datetime, timedelta
import glob
from typing import Dict, List, Any


def weekly_business_audit(week_date: str = None):
    """Main function to perform weekly business audit"""
    if not week_date:
        week_date = datetime.now().strftime("%Y-%m-%d")

    # Parse the date and get the Sunday of the week
    target_date = datetime.strptime(week_date, "%Y-%m-%d")
    # Calculate Sunday of the week (assuming week starts on Sunday)
    days_since_sunday = (target_date.weekday() + 1) % 7  # weekday() returns 0 for Monday
    if days_since_sunday == 0:  # If already Sunday, keep the same date
        week_start = target_date
    else:
        week_start = target_date - timedelta(days=days_since_sunday)
    week_end = week_start + timedelta(days=6)

    # Create vault/Briefings directory if it doesn't exist
    briefings_dir = "vault/Briefings"
    os.makedirs(briefings_dir, exist_ok=True)

    # Create the briefing file path
    briefing_date = week_start.strftime("%Y-%m-%d")
    briefing_path = f"{briefings_dir}/{briefing_date}_CEO_Briefing.md"

    # Collect data for the audit
    business_goals = read_business_goals()
    completed_tasks = read_done_folder(week_start, week_end)
    revenue_data = get_weekly_revenue(week_start, week_end)
    bottlenecks = identify_bottlenecks()
    suggestions = generate_proactive_suggestions()

    # Generate the briefing content
    briefing_content = generate_ceo_briefing(
        business_goals, revenue_data, completed_tasks, bottlenecks, suggestions
    )

    # Write the briefing file
    with open(briefing_path, 'w') as f:
        f.write(briefing_content)

    # Log the audit
    audit_log_id = log_audit(briefing_path, revenue_data, completed_tasks, bottlenecks, suggestions)

    # Update dashboard with audit information
    update_dashboard(briefing_path, revenue_data, completed_tasks)

    return {
        "briefing_path": briefing_path,
        "revenue_data": revenue_data,
        "completed_tasks": completed_tasks,
        "bottlenecks": bottlenecks,
        "suggestions": suggestions,
        "audit_log_id": audit_log_id
    }


def read_business_goals():
    """Read Business_Goals.md file"""
    with open("vault/Business_Goals.md", "r") as f:
        content = f.read()
    return content


def read_done_folder(week_start: datetime, week_end: datetime):
    """Read files from vault/Done folder for the specified week"""
    done_files = glob.glob("vault/Done/*.md")
    completed_tasks = []

    for file_path in done_files:
        # Get file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))

        # Check if file was modified within the week
        if week_start <= mod_time <= week_end:
            with open(file_path, 'r') as f:
                content = f.read()
                # Extract task information from the file
                completed_tasks.append({
                    "file_path": file_path,
                    "modified_date": mod_time.isoformat(),
                    "content": content
                })

    return completed_tasks


def get_weekly_revenue(week_start: datetime, week_end: datetime):
    """Get revenue data for the specified week - placeholder for Odoo integration"""
    # Placeholder implementation - in a real implementation, this would connect to Odoo
    # to get actual revenue data for the specified date range
    return {
        "total_revenue": 12500,  # Placeholder value
        "invoice_count": 8,      # Placeholder value
        "avg_invoice_value": 1562.5  # Placeholder value
    }


def identify_bottlenecks():
    """Identify bottlenecks (delayed tasks)"""
    # Check for overdue tasks or pending items
    # This could include pending approvals, delayed invoices, etc.
    bottlenecks = []

    # Check for items in vault directories
    pending_dirs = ["vault/Pending_Approval", "vault/Needs_Action", "vault/Inbox", "vault/Drafts"]
    for pending_dir in pending_dirs:
        if os.path.exists(pending_dir):
            pending_files = os.listdir(pending_dir)
            for file in pending_files:
                if file.endswith('.md') or file.endswith('.json'):
                    bottlenecks.append({
                        "type": "pending_approval",
                        "item": file,
                        "location": pending_dir
                    })

    return bottlenecks


def generate_proactive_suggestions():
    """Generate proactive suggestions for business improvement"""
    suggestions = []

    # Example suggestions based on common business needs
    # These would be implemented as dry-run operations in appropriate MCPs
    suggestions.append({
        "type": "subscription",
        "action": "cancel_subscription",
        "description": "Cancel underperforming subscription service",
        "rationale": "Cost optimization recommendation",
        "mcp": "email",
        "status": "pending_approval"  # This will be placed in Pending_Approval for review
    })

    suggestions.append({
        "type": "follow_up",
        "action": "send_follow_up_email",
        "description": "Follow up with inactive clients",
        "rationale": "Customer retention improvement",
        "mcp": "email",
        "status": "pending_approval"
    })

    suggestions.append({
        "type": "marketing",
        "action": "create_social_media_campaign",
        "description": "Launch social media campaign for new product",
        "rationale": "Increase brand awareness and generate leads",
        "mcp": "social",
        "status": "pending_approval"
    })

    return suggestions


def generate_ceo_briefing(business_goals, revenue_data, completed_tasks, bottlenecks, suggestions):
    """Generate the CEO briefing content"""
    briefing = f"""# Weekly CEO Briefing - {datetime.now().strftime('%Y-%m-%d')}

## Executive Summary
This week's business audit covering key metrics, completed tasks, and strategic recommendations.

## Business Goals Overview
{business_goals[:500]}...  # Truncate for brevity

## Revenue Analysis
### This Week
- Total Revenue: ${revenue_data.get('total_revenue', 0):,}
- Number of Invoices: {revenue_data.get('invoice_count', 0)}
- Average Invoice Value: ${revenue_data.get('avg_invoice_value', 0):,.2f}

## Completed Tasks
### This Week
"""

    for task in completed_tasks:
        # Extract task title from content if available
        task_title = task['file_path'].split('/')[-1].replace('.md', '').replace('_', ' ').title()
        briefing += f"- {task_title} (Completed: {task['modified_date']})\n"

    if not completed_tasks:
        briefing += "- No tasks completed this week\n"

    briefing += f"""

## Bottlenecks & Delays
### Current Issues
"""

    for bottleneck in bottlenecks:
        briefing += f"- {bottleneck['type']}: {bottleneck['item']} in {bottleneck['location']}\n"

    if not bottlenecks:
        briefing += "- No bottlenecks identified this week\n"

    briefing += f"""

## Proactive Suggestions
### Recommendations for Next Week
"""

    for suggestion in suggestions:
        briefing += f"- **{suggestion['description']}** (Status: {suggestion['status']})\n"
        briefing += f"  - *Rationale*: {suggestion['rationale']}\n"
        briefing += f"  - *MCP*: {suggestion['mcp']}\n\n"

    briefing += f"""

## Next Week's Priorities
1. Address identified bottlenecks
2. Process pending approvals
3. Follow up on proactive suggestions
4. Continue alignment with business goals

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by AI Employee
"""

    return briefing


def log_audit(briefing_path, revenue_data, completed_tasks, bottlenecks, suggestions):
    """Log the audit to weekly_audit.json"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "briefing_path": briefing_path,
        "revenue_data": revenue_data,
        "completed_tasks_count": len(completed_tasks),
        "bottlenecks_count": len(bottlenecks),
        "suggestions_count": len(suggestions),
        "action": "weekly_audit",
        "status": "completed"
    }

    # Create vault/Logs directory if it doesn't exist
    logs_dir = "vault/Logs"
    os.makedirs(logs_dir, exist_ok=True)

    log_file = f"{logs_dir}/weekly_audit.json"

    # Read existing logs or create empty list
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(log_entry)

    # Write back to the log file
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

    return log_entry["timestamp"]


def update_dashboard(briefing_path, revenue_data, completed_tasks):
    """Update the dashboard with audit information"""
    # Read the current dashboard
    with open("vault/Dashboard.md", "r") as f:
        dashboard_content = f.read()

    # Add audit information to the dashboard
    audit_summary = f"\n\n## Weekly Audit\n- Latest Briefing: {briefing_path}\n- Revenue: ${revenue_data.get('total_revenue', 0):,}\n- Tasks Completed: {len(completed_tasks)}"

    # Find the appropriate place to insert the audit summary
    lines = dashboard_content.split('\n')
    updated_lines = []
    inserted = False

    for line in lines:
        updated_lines.append(line)
        if line.startswith("# Dashboard") or line.startswith("# ") and not inserted:  # After first header
            updated_lines.append(audit_summary)
            inserted = True

    # Write the updated dashboard
    with open("vault/Dashboard.md", "w") as f:
        f.write('\n'.join(updated_lines))


if __name__ == "__main__":
    # This allows the script to be run directly for testing
    result = weekly_business_audit()
    print(f"Weekly audit completed. Briefing generated at: {result['briefing_path']}")