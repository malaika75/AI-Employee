# Gold Tier Architecture Documentation

## System Overview

The AI Employee system is designed with a modular architecture that enables robust automation of business processes with human-in-the-loop oversight. This Gold Tier system implements comprehensive error recovery, graceful degradation, and comprehensive logging.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AI EMPLOYEE SYSTEM                         │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Claude Code   │  │   MCP Servers   │  │  File System    │     │
│  │   Integration   │  │                 │  │   Watchers      │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│         │                       │                      │            │
│         ▼                       ▼                      ▼            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Process       │  │   Email MCP     │  │  File System    │     │
│  │   Management    │  │   Server        │  │   Handlers      │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│         │                       │                      │            │
│         ▼                       ▼                      ▼            │
│  ┌─────────────────────────────────────────────────────────────────┤
│  │              VAULT DIRECTORY (Core Data)                      │ │
│  │  ┌─────────────┬─────────────┬─────────────┬─────────────────┐ │ │
│  │  │   Needs     │   Done      │   Pending   │   Drafts        │ │ │
│  │  │   Action    │             │   Approval  │                 │ │ │
│  │  └─────────────┴─────────────┴─────────────┴─────────────────┘ │ │
│  │  ┌─────────────┬─────────────┬─────────────┬─────────────────┐ │ │
│  │  │  Approved   │  Rejected   │   Inbox     │   Archive       │ │ │
│  │  │             │             │             │                 │ │ │
│  │  └─────────────┴─────────────┴─────────────┴─────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┤
│                             │                                       │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┤
│  │                    LOGGING SYSTEM                             │ │
│  │  ┌─────────────────┬─────────────────┬─────────────────┐      │ │
│  │  │  Operations     │    Errors       │   Full Audit    │      │ │
│  │  │     Logs        │     Logs        │     Trail       │      │ │
│  │  └─────────────────┴─────────────────┴─────────────────┘      │ │
│  └─────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MCP Servers (Model Context Protocol)
- **Email MCP**: Handles email operations via Gmail API with approval workflow
- **Odoo MCP**: Manages ERP operations (invoices, payments) with draft approval system
- **Social MCP**: Manages social media posts with human approval

### 2. File System Watchers
- Monitors directories for file changes
- Triggers actions based on file movements
- Implements human-in-the-loop approval system

### 3. Vault Directory Structure
All business data is stored in a structured vault directory:
```
vault/
├── Needs_Action/     # Tasks requiring processing
├── Done/            # Completed tasks
├── Pending_Approval/ # Operations awaiting approval
├── Drafts/          # Draft content
├── Approved/        # Approved operations
├── Rejected/        # Rejected operations
├── Inbox/           # Incoming items
├── Archive/         # Archived items
├── Logs/            # All system logs
│   ├── email_operations.json
│   ├── odoo_operations.json
│   ├── social_operations.json
│   ├── errors.json
│   └── full_audit.jsonl
└── Briefings/       # CEO briefings
```

## Error Recovery & Graceful Degradation

### Retry Mechanisms
- **Exponential Backoff**: All API calls implement exponential backoff retries
- **Connection Recovery**: MCP servers automatically reconnect when connections fail
- **Operation Queuing**: Failed operations are queued for later retry
- **Graceful Failures**: System continues operating even when individual components fail

### Fallback Strategies
- If MCP server fails, tasks are queued in appropriate directories
- If watcher fails, file system continues to function manually
- If API unavailable, operations remain in draft/approval status
- If credentials expire, system logs issue and awaits manual intervention

## Comprehensive Logging System

### JSONL Format (full_audit.jsonl)
Each operation is logged as a single JSON line for efficient processing:

```
{"timestamp": "2026-03-04T08:32:09.906955", "action_type": "email_sent", "status": "success", "details": {"to": "user@example.com", "subject": "Weekly Report", "message_id": "1a2b3c"}, "user_id": "system"}
{"timestamp": "2026-03-04T08:32:15.123456", "action_type": "odoo_invoice_draft", "status": "pending", "details": {"partner_id": 123, "amount": 1500.00}, "error": null, "user_id": "system"}
```

### Log Categories
- **Operations Logs**: Track successful operations
- **Error Logs**: Capture failures and issues
- **Audit Trail**: Complete system activity tracking
- **Performance Logs**: Monitor system metrics

## Implementation Features

### 1. Weekly Business & Accounting Audit
- Runs every Sunday automatically
- Generates CEO briefing with revenue, completed tasks, bottlenecks
- Creates proactive suggestions requiring approval
- Updates dashboard and dashboard metrics

### 2. MCP Integration
- All MCPs use consistent directory structure
- Human approval required for all sensitive operations
- Dry-run capabilities for all operations
- Comprehensive error handling

### 3. Process Monitoring
- File system watchers monitor activity
- Process managers ensure service availability
- Automatic restart on failures
- Health checks and monitoring

## Security & Compliance

### Human-in-the-Loop
- All sensitive operations require human approval
- Draft system prevents accidental execution
- Audit trail for all actions
- Granular permission controls

### Data Protection
- All sensitive data in vault directory
- Encrypted credentials and tokens
- Audit trail for all data access
- Secure API communication

## Lessons Learned

### 1. Modular Design Benefits
- MCP servers can be independently updated
- File system approach enables offline operations
- Human-in-the-loop prevents automation errors
- Directory-based workflow is resilient to system failures

### 2. Error Handling Best Practices
- Always implement retry mechanisms with exponential backoff
- Log all operations for debugging and auditing
- Queue operations when systems are unavailable
- Implement graceful degradation, not hard failures

### 3. Scalability Considerations
- File-based architecture scales well with proper directory structure
- MCP servers can run independently
- Vault directory enables consistent state management
- JSON logging enables easy analysis and processing

### 4. Operational Insights
- Weekly audits help identify patterns and bottlenecks
- Comprehensive logging enables proactive issue resolution
- Human approval prevents costly automation errors
- File system approach provides natural audit trail

## Setup Guide

### Prerequisites
- Python 3.8+
- Claude Code CLI
- MCP server support enabled
- Appropriate API credentials (Gmail, Odoo, Social Media)

### Installation Steps
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up MCP server configurations
4. Configure API credentials in vault directory
5. Start process managers and MCP servers
6. Verify all services are running

### Configuration
- MCP endpoints configured in mcp.json
- Vault directory structure created automatically
- Logging paths configured in audit_logger.py
- Cron/scheduler set up for weekly audit

## Troubleshooting

### Common Issues
- API credentials expiration - refresh tokens regularly
- MCP server connection failures - check network and credentials
- File system permission errors - verify vault directory permissions
- Process monitoring failures - check process manager logs

### Recovery Procedures
- Failed operations remain in appropriate directories for manual processing
- System can be restarted without data loss
- Audit logs provide complete operation history
- MCP servers can be restarted independently