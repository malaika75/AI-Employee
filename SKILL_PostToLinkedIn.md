# SKILL_PostToLinkedIn

## Description
Generate and post professional LinkedIn updates about business activities, achievements, or insights. This skill creates a draft LinkedIn post based on business goals, recent activities, or specified content, which requires approval before posting.

## Parameters
- `post_type`: Type of post to create (announcement, weekly_update, sales_pitch, insight, achievement)
- `topic`: Main topic or subject for the post
- `context`: Additional context or details to include in the post
- `tone`: Desired tone (professional, casual, promotional, inspirational)

## Process
1. Read Business_Goals.md to understand company direction and objectives
2. Scan recent activity in the vault (Logs, Completed tasks, recent notes)
3. Generate a LinkedIn-appropriate post based on the specified type and topic
4. Save draft to /Drafts/LinkedIn_post.md for review and approval
5. Create approval request in /Pending_Approval for final review

## Output
- Creates LinkedIn_post_YYYYMMDD.md in the Drafts directory
- Creates approval request in Pending_Approval directory
- Logs the action in /Logs

## LinkedIn Post Guidelines Applied
- Professional tone maintaining corporate identity
- 2-3 relevant hashtags
- Engagement-focused content
- Compliance with LinkedIn's posting policies
- Appropriate length for visibility (100-1500 characters recommended)

## Example Usage
```
{{skill:SKILL_PostToLinkedIn post_type="weekly_update" topic="Team Achievement" context="Completed major milestone in Q1 project" tone="professional"}}
```

## Generated Content Includes
- Compelling opening line
- Key achievement or update
- Call-to-action (optional)
- Relevant hashtags
- Professional closing