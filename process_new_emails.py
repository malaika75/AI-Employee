#!/usr/bin/env python3
"""
Script to process new emails that appear in the Needs_Action folder
"""
import os
import glob
import re
from pathlib import Path
import frontmatter  # You might need to install this: pip install python-frontmatter


def process_email_file(email_file_path):
    """Process a single email file and create plan and approval files"""
    print(f"Processing email: {email_file_path}")

    # Read the email file with frontmatter
    with open(email_file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    email_metadata = post.metadata
    email_content = post.content

    # Extract email details
    email_from = email_metadata.get('from', 'Unknown')
    email_subject = email_metadata.get('subject', 'No Subject')
    email_priority = email_metadata.get('priority', 'medium')
    email_content_text = post.content

    # Create a summary of the email
    print(f"  From: {email_from}")
    print(f"  Subject: {email_subject}")
    print(f"  Priority: {email_priority}")

    # Extract message ID from filename
    filename = Path(email_file_path).name
    match = re.search(r'EMAIL_([a-zA-Z0-9]+)\.md', filename)
    if not match:
        print(f"  Could not extract message ID from filename: {filename}")
        return
    message_id = match.group(1)

    # Create plan file
    plan_content = f"""# Plan_EMAIL_{message_id}.md

## Objective
Handle urgent email

## Summary
From: {email_from}
Subject: {email_subject}
Priority: {email_priority}
Content Preview: {email_content_text[:200]}...

## Detailed Analysis
Based on the subject and content, this email requires attention due to its {email_priority} priority level.

## Steps
- [ ] Review
- [ ] Draft reply if needed
- [ ] Get approval for sending
- [ ] Send via MCP if approved
- [ ] Log and move to Done

## Action Plan
- [ ] Review email content in detail
- [ ] Draft response if required
- [ ] Determine if escalation is needed
- [ ] Set follow-up reminder if applicable
- [ ] Archive after action completed

## Approvals needed
Yes (since email send is sensitive)

## Next Steps
1. Respond to the email appropriately
2. Complete any required follow-up tasks
3. Update status when completed
"""

    # Save plan to Plans subfolder
    plans_dir = Path("vault") / "Plans"
    plans_dir.mkdir(exist_ok=True)
    plan_file_path = plans_dir / f"Plan_EMAIL_{message_id}.md"

    with open(plan_file_path, 'w', encoding='utf-8') as f:
        f.write(plan_content)

    print(f"  Created plan: {plan_file_path}")

    # Create approval request if needed
    if email_priority.lower() in ['high', 'urgent'] or '[ ] Reply' in email_content_text:
        approval_content = f"""# APPROVAL_EMAIL_{message_id}.md

## Email Details
- From: {email_from}
- Subject: {email_subject}
- Priority: {email_priority}
- Received: {email_metadata.get('received', '')}

## Request Summary
{email_content_text[:300]}

## Approval Request
Requesting approval to draft and send a response to this email.

## Suggested Next Actions
- [ ] Approve for response drafting
- [ ] Deny and archive
- [ ] Forward to another team member
"""

        approval_dir = Path("vault") / "Pending_Approval"
        approval_dir.mkdir(exist_ok=True)
        approval_file_path = approval_dir / f"APPROVAL_EMAIL_{message_id}.md"

        with open(approval_file_path, 'w', encoding='utf-8') as f:
            f.write(approval_content)

        print(f"  Created approval request: {approval_file_path}")

    print(f"  Completed processing: {email_file_path}")


def main():
    """Main function to find and process all unprocessed emails"""
    needs_action_dir = Path("vault") / "Needs_Action"

    if not needs_action_dir.exists():
        print(f"Needs_Action directory does not exist: {needs_action_dir}")
        return

    # Find all email files in Needs_Action
    email_files = list(needs_action_dir.glob("EMAIL_*.md"))

    if not email_files:
        print("No new email files found in Needs_Action folder")
        return

    print(f"Found {len(email_files)} email files to process")

    for email_file in email_files:
        try:
            process_email_file(email_file)
        except Exception as e:
            print(f"Error processing {email_file}: {e}")

    print("Email processing complete")


if __name__ == "__main__":
    main()