# SKILL_RequestEmailApproval

## Description
This skill handles sending or drafting emails with human-in-the-loop approval. Instead of sending emails directly, this skill creates a pending approval file in the /Pending_Approval directory. The user must then move the file to /Approved to send the email, or to /Rejected to cancel.

## Usage
When you need to send or draft an email, use this skill instead of direct email sending. The skill will create an approval request file that requires human intervention.

## Parameters
- `action`: The email action to perform ("send_email" or "draft_email")
- `to`: Recipient email address
- `subject`: Email subject line
- `body`: Email body content

## Example Usage
```
{{skill:SKILL_RequestEmailApproval action="send_email" to="user@example.com" subject="Meeting Update" body="Hi, I wanted to let you know about the meeting update..."}}
```

## Implementation Details
- Creates a file in the format `EMAIL_{timestamp}.md` in the `vault/Pending_Approval` directory
- The file contains a YAML header with email metadata and the email body
- User must manually move file to `vault/Approved` or `vault/Rejected` to continue
- The email MCP server monitors these directories and processes accordingly