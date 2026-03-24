# Platinum Tier Deployment Guide

## Overview
This guide details the deployment process for the Platinum Tier of the AI Employee system, which implements an Always-on Cloud + Local Executive architecture with synced vault.

## Architecture
- **Cloud Executive**: Handles email triage, draft replies, social post drafts/scheduling (draft-only)
- **Local Executive**: Handles approvals, WhatsApp session, payments/banking, final send/post actions
- **Vault Sync**: Git-based synchronization with secret exclusion

## Requirements
- GitPython: `pip install GitPython`
- Git installed on system
- Cloud VM (Oracle Cloud Free Tier recommended, or AWS free)

## Cloud VM Setup

### Oracle Cloud Free Tier Setup

1. **Create Oracle Cloud account**
   - Go to https://www.oracle.com/cloud/
   - Sign up for a free account
   - Complete verification process

2. **Launch an Always-Free VM**
   - In Oracle Cloud Console, navigate to "Compute" > "Instances"
   - Click "Create Instance"
   - Select "Always Free Eligible" shape (e.g., VM.Standard.A1.Flex)
   - Choose Ubuntu 22.04 or similar LTS distribution
   - Configure SSH keys for access
   - Launch the instance

3. **Access the VM**
   ```bash
   ssh -i ~/.ssh/your_private_key opc@your_vm_public_ip
   ```

4. **Install dependencies on VM**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip git
   pip3 install GitPython
   ```

5. **Clone the repository**
   ```bash
   git clone <your_repo_url>
   cd AI-Employee
   pip3 install -r requirements.txt
   ```

### AWS Free Tier Setup (Alternative)

1. **Create AWS account**
   - Go to https://aws.amazon.com/
   - Sign up for a free account
   - Complete verification

2. **Launch EC2 instance**
   - Navigate to EC2 service
   - Click "Launch Instance"
   - Select "Free tier eligible" Ubuntu 22.04 AMI
   - Choose t2.micro instance type (12 months free)
   - Configure security groups and SSH access
   - Launch instance

3. **Access and configure**
   ```bash
   ssh -i ~/.ssh/your_key.pem ubuntu@your_instance_ip
   # Follow same steps as Oracle Cloud VM
   ```

## Vault Sync Configuration

### Git Repository Setup

1. **Create a Git repository** (GitHub, GitLab, or self-hosted)
2. **Configure the repository to exclude sensitive files** using .gitignore:
   ```
   .env
   tokens.json
   credentials.json
   whatsapp_session*
   banking_creds*
   *token.json
   *session.json
   WhatsApp/
   Banking/
   Payments/
   ```

3. **Initialize the vault for sync**:
   ```bash
   cd vault
   git init
   git remote add origin <your_repo_url>
   ```

## Running the Executives

### Cloud Executive
```bash
python3 orchestrator.py --vault-path ./vault --is-cloud --remote-repo <your_repo_url>
```

### Local Executive
```bash
python3 orchestrator.py --vault-path ./vault --remote-repo <your_repo_url>
```

## Folder Structure
The system implements the following folder structure:
- `/Needs_Action/<domain>/` - Tasks needing attention (email, social, etc.)
- `/Plans/<domain>/` - Strategic plans and approaches
- `/Pending_Approval/<domain>/` - Items awaiting approval
- `/In_Progress/<agent>/` - Tasks currently being processed
- `/Updates/` - Status updates and reports
- `/Signals/` - Critical alerts and notifications

## Security Features

### Claim-by-Move Rule
- First agent to move item from `/Needs_Action` to `/In_Progress/<agent>/` owns it
- Implemented in `ExecutiveOrchestrator.claim_task()`

### Single-Writer Rule
- Only Local Executive can update Dashboard.md
- Implemented in `ExecutiveOrchestrator.update_dashboard()`

### Secret Protection
- Secrets never sync to cloud via Git exclusions
- Implemented in `VaultSyncManager.is_file_excluded()`
- Protected files include: .env, tokens, sessions, banking credentials

## Service Setup

### Running as a Service on Cloud VM

1. **Create a systemd service file** (`/etc/systemd/system/ai-executive.service`):
   ```ini
   [Unit]
   Description=AI Executive Orchestrator - Cloud
   After=network.target

   [Service]
   Type=simple
   User=opc
   WorkingDirectory=/home/opc/AI-Employee
   ExecStart=/usr/bin/python3 /home/opc/AI-Employee/orchestrator.py --vault-path /home/opc/AI-Employee/vault --is-cloud
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ai-executive
   sudo systemctl start ai-executive
   ```

3. **Check service status**:
   ```bash
   sudo systemctl status ai-executive
   ```

## Monitoring and Maintenance

### Log Files
- Cloud Executive logs: `vault/Logs/orchestrator.log`
- Sync cycle logs are recorded in orchestrator log file

### Common Issues
1. **Git sync conflicts**: Usually due to concurrent modifications on both cloud and local
2. **Permission errors**: Ensure proper file permissions on vault directory
3. **Network issues**: Configure proper firewall rules for Git operations

## Troubleshooting

1. **If sync fails**: Check network connectivity and Git remote URL
2. **If tasks are not processed**: Verify the executives are running and have proper permissions
3. **If vault structure is missing**: Run the orchestrator to initialize the structure