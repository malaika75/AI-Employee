# SKILL_MoveApprovedToArchived

## Description
Move an approved email from /Approved to /Archived so that MCP server can send it. This is for emails that required human approval.

## Parameters
- `approval_file`: Path to the approval file in /Approved that has been reviewed by human

## Process
1. Read the approval file from /Approved directory
2. Verify that it has been approved by checking its status/headers or contents if needed
3. Move the file to /Archived directory where MCP server monitors and sends emails
4. The file should already contain Claude's crafted contextual response ready to send
5. Optional: Create a log in /Logs about the approval and movement

## Output
- Moves the approval file from /Approved to /Archived
- MCP server will automatically detect and send the email
- Original email file can then be moved to /Done by Claude after sending is confirmed

## Example Usage
```
{{skill:SKILL_MoveApprovedToArchived approval_file="EMAIL_xyz789.md"}}
```