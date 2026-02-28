# SKILL_ProcessEmailForResponse

## Description
Process an email from /Needs_Action and generate an appropriate response by determining if it requires approval or can be sent directly.

## Parameters
- `email_file`: Path to the email file in /Needs_Action
- `claude_context`: The email content, sender, and subject to analyze

## Process
1. Read the email file from /Needs_Action
2. Analyze the email content, sender, and subject
3. Determine sensitivity level:
   - HIGH: Contains keywords like "payment", "invoice", "urgent", "confidential", "financial", "salary", "contract"
   - NORMAL: Simple inquiries, meeting requests, informational emails
   - NONE: Spam, newsletters, notifications that don't require response
4. For HIGH sensitivity: Create file in /Pending_Approval with Claude's drafted response
5. For NORMAL: Create file in /Archived with Claude's response (MCP will send)
6. For NONE: Move email file to /Done with note "No response needed"

## Output
- Creates appropriate response files in the correct directories
- Moves original email file to appropriate final location
- Logs the action in /Logs

## Example Usage
```
{{skill:SKILL_ProcessEmailForResponse email_file="EMAIL_abc123.md"}}
```