# Platinum Tier: Always-on Cloud + Local Executive with Synced Vault

## Overview
The Platinum Tier implements a distributed AI Employee architecture with a Cloud Executive and Local Executive working in coordination through a shared, synchronized vault system. This tier extends the Gold Tier capabilities with cloud-local separation of duties and secure synchronization.

## Architecture Components

### Cloud Executive
- **Email triage**: Categorizes incoming emails and creates draft replies
- **Social post drafts**: Generates social media content drafts and scheduling suggestions
- **Draft-only operations**: Creates drafts requiring local approval but does not execute final actions
- **Read-only access**: Can read audit logs and system status but cannot modify sensitive operations
- **Sync responsibility**: Pushes new drafts and categorized items to the shared vault

### Local Executive
- **Approvals**: Reviews and approves/rejects all pending actions
- **WhatsApp session management**: Handles WhatsApp communications and sessions
- **Payments and banking**: Processes financial transactions and banking operations
- **Final send/post actions**: Executes final email sends, social media posts, and financial operations
- **Dashboard updates**: Maintains the single-writer Dashboard.md file
- **Sync responsibility**: Pulls cloud drafts and pushes approved actions

## Vault Structure
```
vault/
├── Needs_Action/
│   ├── email/
│   ├── social/
│   ├── odoo/
│   ├── payment/
│   └── whatsapp/
├── Plans/
│   ├── email/
│   ├── social/
│   ├── odoo/
│   ├── payment/
│   └── whatsapp/
├── Pending_Approval/
│   ├── email/
│   ├── social/
│   ├── odoo/
│   ├── payment/
│   └── whatsapp/
├── In_Progress/
│   ├── cloud_exec/
│   └── local_exec/
├── Updates/
├── Signals/
├── Drafts/
├── Archive/
├── Done/
├── Approved/
├── Rejected/
├── Logs/
└── Dashboard.md
```

## Key Features

### 1. Claim-by-Move Rule
- First agent to move item from `/Needs_Action` to `/In_Progress/<agent>/` owns it
- Prevents duplicate processing of the same task
- Implemented atomically to handle concurrent access

### 2. Single-Writer Rule
- Only Local Executive can update `Dashboard.md`
- Prevents sync conflicts on dashboard updates
- Cloud Executive can read but not write to dashboard

### 3. Secret Protection
- Secrets never sync to cloud via Git exclusions
- Protected files: `.env`, tokens, sessions, banking credentials
- Configured in `VaultSyncManager` exclusions

### 4. Operation Separation
- **Cloud Operations**: email_triage, draft_reply, social_post_draft, social_post_schedule, weekly_audit_read, odoo_read
- **Local Operations**: approval, whatsapp_session, payments_banking, final_send, final_post, dashboard_write, email_send, social_post_execute, odoo_execute

## Implementation Files

### orchestrator.py
Core orchestrator that manages executive coordination:
- `VaultSyncManager`: Handles Git-based vault synchronization with exclusions
- `ExecutiveOrchestrator`: Main orchestrator class with cloud/local role management
- Cloud operations: email triage, social draft creation
- Local operations: approvals, final actions
- Sync cycle management with pull/push operations

### Deployment
- Cloud VM setup (Oracle Cloud Free Tier or AWS Free)
- Git repository configuration with proper exclusions
- Service configuration for continuous operation
- Security configuration for vault protection

## Running the System

### Cloud Executive Setup
```bash
python3 orchestrator.py --vault-path ./vault --is-cloud --remote-repo <git_repo_url>
```

### Local Executive Setup
```bash
python3 orchestrator.py --vault-path ./vault --remote-repo <git_repo_url>
```

### Service Deployment
Configure as systemd services for continuous operation on both cloud and local systems.

## Security Model

### Data Flow Security
- Cloud Executive never sees sensitive credentials
- Local Executive handles all sensitive operations
- Vault sync excludes all secret files
- All communications through the shared vault with approval workflows

### Access Control
- Cloud Executive: Read access to most data, write to drafts and categorizations
- Local Executive: Full access including sensitive operations
- All operations follow the principle of least privilege

### Audit Trail
- All operations logged in `vault/Logs/orchestrator.log`
- Dashboard updates provide system status
- Git history provides change tracking (excluding secrets)

## Benefits

1. **Availability**: Cloud Executive runs continuously, handling triage even when local is offline
2. **Security**: Sensitive operations always require local presence and approval
3. **Scalability**: Workload distributed between cloud and local systems
4. **Redundancy**: Shared vault provides backup and synchronization
5. **Compliance**: Clear separation of sensitive and non-sensitive operations