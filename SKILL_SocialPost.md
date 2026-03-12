# Social Post Generation Skill

This skill helps generate engaging social media posts for Facebook, Instagram, and Twitter (X) based on your business metrics, goals, or dashboard updates.

## Components

1. **Content Analysis**: Analyzes Dashboard.md or Business_Goals.md to extract key points for social sharing
2. **Platform-Optimized Content**: Creates content tailored to each platform's best practices
3. **Approval Workflow**: Generates a draft that requires approval before posting

## Usage

When you want to create a social media post:
1. The skill will read relevant data from Dashboard.md or Business_Goals.md
2. Generate an engaging post with appropriate hashtags and tone
3. Create a draft in the /Drafts directory
4. Generate an approval request in Pending_Approvals

## Content Creation Guidelines

### For Dashboard Summaries:
- Extract key metrics and achievements
- Use positive, engaging language
- Include relevant hashtags (#BusinessUpdate, #Achievement, #Growth)
- Keep Twitter posts under 280 characters
- Optimize Instagram posts with visual appeal in mind
- Format Facebook posts for readability

### For Business Goals:
- Highlight progress toward goals
- Celebrate milestones
- Encourage engagement (questions, calls to action)

## Example Post Structure:

> "Exciting news! 🚀 We've achieved [key metric] this month. Big thanks to our amazing team for making this possible! #BusinessUpdate #TeamWork #Growth"

## Required Inputs

- Source: Dashboard.md or Business_Goals.md (or custom input)
- Platform: Facebook, Instagram, or Twitter
- Tone: Professional, Casual, or Enthusiastic

## Output

- Generated post content
- Draft file with post ID
- Approval request file (Pending_Approval_SOCIAL_{id}.md)

## Implementation

The skill uses the SocialMediaMCP class to handle the actual posting workflow through browser automation with Playwright.