# SKILL_TriageEmail.md

## Description
This skill processes new email files in the /Needs_Action folder, summarizes the email content, and creates a plan for handling the email.

## Parameters
- `email_file`: Path to the EMAIL_*.md file to process

## Process
1. Read the email file from /Needs_Action
2. Extract email metadata (from, subject, snippet, priority)
3. Summarize the email content
4. Create a plan based on email content and priority
5. For low priority emails, suggest auto-archiving
6. Create Plan_EMAIL_*.md with action steps

## Implementation

```python
import os
import re
import json
from pathlib import Path
import frontmatter  # Requires python-frontmatter package

def triage_email(email_file_path):
    """Process an email file and create a plan for handling it."""

    # Read the email file with frontmatter
    with open(email_file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    email_metadata = post.metadata
    email_content = post.content

    # Extract email details
    email_from = email_metadata.get('from', 'Unknown')
    email_subject = email_metadata.get('subject', 'No Subject')
    email_snippet = email_metadata.get('snippet', '')
    email_priority = email_metadata.get('priority', 'medium')

    # Create a summary of the email
    summary = f"""
## Email Summary
- From: {email_from}
- Subject: {email_subject}
- Priority: {email_priority}
- Content Preview: {email_snippet[:200]}...
    """.strip()

    # Determine actions based on priority and content
    if email_priority.lower() == 'low':
        suggested_actions = [
            "Archive email (low priority)",
            "No immediate action required"
        ]
        plan_content = f"""
# Plan_EMAIL_{Path(email_file_path).stem[6:]}.md

## Summary
{summary}

## Priority Assessment
This email has been classified as low priority. Consider archiving without immediate action.

## Recommended Actions
{create_action_list(suggested_actions)}

## Outcome
Email can be archived after review.
        """.strip()
    else:
        # For medium/high priority emails, create a more detailed plan
        suggested_actions = [
            "Review email content in detail",
            "Draft response if required",
            "Determine if escalation is needed",
            "Set follow-up reminder if applicable",
            "Archive after action completed"
        ]

        plan_content = f"""
# Plan_EMAIL_{Path(email_file_path).stem[6:]}.md

## Summary
{summary}

## Detailed Analysis
Based on the subject and content, this email requires attention due to its {email_priority} priority level.

## Action Plan
{create_action_list(suggested_actions)}

## Next Steps
1. Respond to the email appropriately
2. Complete any required follow-up tasks
3. Update status when completed
        """.strip()

    # Write the plan file to Needs_Action folder
    plan_file_path = Path(email_file_path).parent / f"Plan_EMAIL_{Path(email_file_path).stem[6:]}.md"

    with open(plan_file_path, 'w', encoding='utf-8') as f:
        f.write(plan_content)

    return str(plan_file_path)

def create_action_list(actions):
    """Create a markdown checklist from a list of actions."""
    checklist = []
    for action in actions:
        checklist.append(f"- [ ] {action}")
    return "\n".join(checklist)

# Example usage:
# triage_email("Needs_Action/EMAIL_abc123.md")
```

## Usage
1. The skill automatically runs when an EMAIL_*.md file is detected in /Needs_Action
2. Reads the email metadata and content
3. Creates a Plan_EMAIL_*.md file with appropriate action steps
4. For low priority emails, suggests auto-archiving

## Error Handling
- If the email file cannot be parsed, log an error and skip
- If the plan file cannot be created, log an error and continue
- Validate that required fields exist before processing

## Dependencies
- python-frontmatter package for parsing markdown with frontmatter