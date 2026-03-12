---
title: Weekly Business & Accounting Audit
description: Performs weekly business and accounting audit, generating CEO briefing with revenue, completed tasks, bottlenecks, and proactive suggestions
author: AI Employee
version: 1.0
tier: Gold
---

## Method: weekly_audit

Performs comprehensive weekly business and accounting audit, generating CEO briefing with revenue analysis, completed tasks, bottlenecks, and proactive suggestions.

### Parameters
- `week_date`: (string) Date to use as reference for the weekly audit (format: YYYY-MM-DD)

### Returns
- `briefing_path`: (string) Path to the generated CEO briefing file
- `revenue_data`: (object) Revenue data for the week
- `completed_tasks`: (array) List of completed tasks for the week
- `bottlenecks`: (array) List of identified bottlenecks
- `suggestions`: (array) List of proactive suggestions in dry-run mode
- `audit_log_id`: (string) ID of the audit log entry