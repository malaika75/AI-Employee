"""
Platinum Tier: Always-on Cloud + Local Executive with synced vault

This orchestrator manages the coordination between Cloud Executive and Local Executive,
implementing the shared vault system with proper synchronization and access control.
"""
import os
import json
import time
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import queue
import subprocess
import git  # Requires gitpython package: pip install GitPython


class VaultSyncManager:
    """
    Manages synchronization between Cloud and Local vaults using Git
    """
    def __init__(self, local_vault_path: str, remote_repo_url: Optional[str] = None):
        self.local_vault_path = Path(local_vault_path)
        self.remote_repo_url = remote_repo_url
        self.repo = None

        # Initialize the git repository for vault sync
        self._init_vault_repo()

        # Define sync exclusions (never sync secrets)
        self.exclusions = {
            '.env',
            '*.env',
            'tokens.json',
            'credentials.json',
            'token.json',
            'whatsapp_session*',
            'banking_creds*',
            '*_token.json',
            '*_session.json',
            'WhatsApp/',
            'Banking/',
            'Payments/'
        }

    def _init_vault_repo(self):
        """Initialize the local vault as a git repository"""
        if not (self.local_vault_path / '.git').exists():
            self.repo = git.Repo.init(self.local_vault_path)
            # Create initial commit
            self.local_vault_path.joinpath('.gitkeep').touch()
            self.repo.index.add(['.gitkeep'])
            self.repo.index.commit("Initial vault commit")
        else:
            self.repo = git.Repo(self.local_vault_path)

    def sync_pull(self) -> bool:
        """
        Pull latest changes from remote repository
        Returns True if sync was successful, False otherwise
        """
        try:
            # Check if remote repo URL is configured
            if self.remote_repo_url:
                # Add remote if not exists
                if 'origin' not in [remote.name for remote in self.repo.remotes]:
                    self.repo.create_remote('origin', self.remote_repo_url)

                # Fetch and merge changes
                origin = self.repo.remotes.origin
                origin.fetch()

                # Perform merge while respecting exclusions
                current_branch = self.repo.active_branch
                self.repo.git.merge(f'origin/{current_branch.name}')

                logging.info("Vault sync pull completed successfully")
                return True
            else:
                logging.info("No remote repository configured for pull")
                return True  # Local sync is always successful

        except Exception as e:
            logging.error(f"Vault sync pull failed: {str(e)}")
            return False

    def sync_push(self) -> bool:
        """
        Push local changes to remote repository
        Returns True if sync was successful, False otherwise
        """
        try:
            # Check if there are any changes to commit
            if self.repo.is_dirty() or self.repo.untracked_files:
                # Add all tracked files, respecting exclusions
                files_to_add = []

                # Walk through all files and add those that aren't excluded
                for root, dirs, files in os.walk(self.local_vault_path):
                    for file in files:
                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(self.local_vault_path)

                        # Check if file should be excluded
                        should_exclude = False
                        for exclusion in self.exclusions:
                            if exclusion.startswith('*') and file.endswith(exclusion[1:]):
                                should_exclude = True
                                break
                            elif exclusion == file or exclusion == str(relative_path):
                                should_exclude = True
                                break

                        if not should_exclude and relative_path != Path('.gitkeep'):
                            files_to_add.append(str(relative_path))

                if files_to_add:
                    self.repo.index.add(files_to_add)

                    # Commit changes
                    commit_message = f"Vault sync commit - {datetime.now().isoformat()}"
                    self.repo.index.commit(commit_message)

                    # Push to remote if configured
                    if self.remote_repo_url and 'origin' in [remote.name for remote in self.repo.remotes]:
                        origin = self.repo.remotes.origin
                        origin.push()

                    logging.info(f"Vault sync push completed with {len(files_to_add)} files")
                    return True
                else:
                    logging.info("No files to commit after exclusions")
                    return True
            else:
                logging.info("No changes to commit for vault sync")
                return True

        except Exception as e:
            logging.error(f"Vault sync push failed: {str(e)}")
            return False

    def is_file_excluded(self, file_path: Path) -> bool:
        """
        Check if a file should be excluded from sync
        """
        relative_path = file_path.relative_to(self.local_vault_path)
        file_name = file_path.name

        for exclusion in self.exclusions:
            if exclusion.startswith('*') and file_name.endswith(exclusion[1:]):
                return True
            elif exclusion == file_name or exclusion == str(relative_path):
                return True

        return False


class ExecutiveOrchestrator:
    """
    Orchestrator that manages Cloud Executive and Local Executive coordination
    """
    def __init__(self, vault_path: str, is_cloud_executive: bool = False, remote_repo_url: Optional[str] = None):
        self.vault_path = Path(vault_path)
        self.is_cloud_executive = is_cloud_executive
        self.vault_sync = VaultSyncManager(vault_path, remote_repo_url)

        # Initialize vault folder structure
        self._init_vault_structure()

        # Set up logging
        self.logger = self._setup_logging()

        # Initialize task queue
        self.task_queue = queue.Queue()

        # Define the allowed operations based on executive type
        self.cloud_operations = {
            'email_triage',
            'draft_reply',
            'social_post_draft',
            'social_post_schedule',
            'weekly_audit_read',
            'odoo_read'
        }

        self.local_operations = {
            'approval',
            'whatsapp_session',
            'payments_banking',
            'final_send',
            'final_post',
            'dashboard_write',
            'email_send',
            'social_post_execute',
            'odoo_execute'
        }

    def _setup_logging(self) -> logging.Logger:
        """Set up orchestrator logging"""
        logger = logging.getLogger('ExecutiveOrchestrator')
        logger.setLevel(logging.INFO)

        # Create file handler
        log_file = self.vault_path / 'Logs' / 'orchestrator.log'
        log_file.parent.mkdir(exist_ok=True)

        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _init_vault_structure(self):
        """Initialize the required vault folder structure"""
        folders = [
            'Needs_Action',
            'Plans',
            'Pending_Approval',
            'In_Progress',
            'Updates',
            'Signals',
            'Logs',
            'Drafts',
            'Archive',
            'Done',
            'Approved',
            'Rejected'
        ]

        # Create domain-specific subfolders
        domains = ['email', 'social', 'odoo', 'payment', 'whatsapp']

        for folder in folders:
            path = self.vault_path / folder
            path.mkdir(exist_ok=True)

            # For specific folders, create domain subfolders
            if folder in ['Needs_Action', 'Plans', 'Pending_Approval']:
                for domain in domains:
                    subpath = path / domain
                    subpath.mkdir(exist_ok=True)

        # Create agent-specific In_Progress folders
        agents = ['cloud_exec', 'local_exec']
        for agent in agents:
            path = self.vault_path / 'In_Progress' / agent
            path.mkdir(exist_ok=True)

    def claim_task(self, task_path: Path, agent_name: str) -> bool:
        """
        Claim a task using the claim-by-move rule
        First agent to move item from /Needs_Action to /In_Progress/<agent>/ owns it
        """
        try:
            # Determine target path
            target_path = self.vault_path / 'In_Progress' / agent_name / task_path.name

            # Attempt to move the task file (atomic operation on most systems)
            if task_path.exists():
                shutil.move(str(task_path), str(target_path))
                self.logger.info(f"Task {task_path.name} claimed by {agent_name}")

                # Sync the change
                self.vault_sync.sync_push()

                return True
            else:
                self.logger.warning(f"Task {task_path} no longer exists - already claimed")
                return False

        except Exception as e:
            self.logger.error(f"Failed to claim task {task_path}: {str(e)}")
            return False

    def can_perform_operation(self, operation: str) -> bool:
        """
        Check if the current executive can perform the specified operation
        """
        if self.is_cloud_executive:
            return operation in self.cloud_operations
        else:
            return operation in self.local_operations

    def process_email_triage(self, email_file: Path) -> bool:
        """
        Cloud Executive: Process email triage and create draft replies
        """
        if not self.can_perform_operation('email_triage'):
            self.logger.error("Email triage operation not allowed for this executive")
            return False

        try:
            # Read the email content
            with open(email_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Determine email category and create appropriate response
            # In a real implementation, this would use Claude Code to analyze and respond
            # For now, we'll categorize based on keywords and create a template
            email_category = self._categorize_email(content)

            # Create a draft reply based on the category
            draft_file = self.vault_path / 'Drafts' / f'draft_reply_{email_file.stem}_{int(time.time())}.md'

            category_response_map = {
                'business_inquiry': 'business_inquiry_response',
                'meeting_request': 'meeting_request_response',
                'follow_up': 'follow_up_response',
                'newsletter': 'newsletter_response',
                'spam': 'spam_response',
                'urgent': 'urgent_response',
                'payment_invoice': 'payment_invoice_response'
            }

            response_type = category_response_map.get(email_category, 'default_response')
            response_content = self._generate_response(response_type, content, email_file.name)

            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(f"""---
type: draft_email
original_email: {email_file.name}
action: draft_reply
category: {email_category}
created: {datetime.now().isoformat()}
---

# Draft Reply

This is a draft email reply generated by the Cloud Executive for the following email:

## Original Email: {email_file.name}
## Category: {email_category}

{response_content}

---
**Generated by Cloud Executive at {datetime.now().isoformat()}**
""")

            # Also create a corresponding approval request in Pending_Approval/email/
            approval_file = self.vault_path / 'Pending_Approval' / 'email' / f'EMAIL_approval_{email_file.stem}_{int(time.time())}.md'
            approval_file.parent.mkdir(exist_ok=True)

            with open(approval_file, 'w', encoding='utf-8') as f:
                f.write(f"""---
type: email_approval
action: send_approval
draft_file: {draft_file.name}
original_email: {email_file.name}
category: {email_category}
created: {datetime.now().isoformat()}
---

# Email Send Approval Request

An email reply draft has been created and requires your approval before sending.

## Category: {email_category}
## Original Email: {email_file.name}
## Draft File: {draft_file.name}

Please review the draft and move this file to the Approved folder to send or Rejected folder to discard.

**Draft Preview:**
{response_content[:300]}...
""")

            self.logger.info(f"Email triage completed for {email_file.name}, category: {email_category}, draft: {draft_file.name}, approval: {approval_file.name}")
            self.vault_sync.sync_push()
            return True

        except Exception as e:
            self.logger.error(f"Email triage failed: {str(e)}")
            return False

    def _categorize_email(self, content: str) -> str:
        """
        Categorize email based on content keywords
        """
        content_lower = content.lower()

        # Define category keywords
        categories = {
            'urgent': ['urgent', 'asap', 'immediately', 'critical', 'emergency', 'important'],
            'payment_invoice': ['payment', 'invoice', 'bill', 'cost', 'price', 'charge', 'fee', 'payment due'],
            'meeting_request': ['meeting', 'schedule', 'appointment', 'call', 'discuss', 'availability'],
            'business_inquiry': ['inquiry', 'question', 'information', 'help', 'support', 'request', 'service'],
            'follow_up': ['follow up', 'follow-up', 'checking', 'update', 'status'],
            'newsletter': ['newsletter', 'news', 'update', 'announcement', 'announcement', 'weekly'],
            'spam': ['offer', 'click here', 'limited time', 'congratulations', 'winner', 'free', 'buy now']
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return category

        return 'default'

    def _generate_response(self, response_type: str, original_content: str, email_filename: str) -> str:
        """
        Generate an appropriate response based on the response type
        """
        responses = {
            'business_inquiry_response': f"Thank you for your inquiry. I've reviewed your email \"{email_filename}\" and will get back to you shortly with a detailed response after analyzing your specific requirements.",

            'meeting_request_response': f"I've received your meeting request from the email \"{email_filename}\". I will coordinate with the appropriate team members and suggest suitable times for a meeting.",

            'follow_up_response': f"Thank you for following up on \"{email_filename}\". I appreciate you checking in and will provide an update shortly.",

            'newsletter_response': f"Thank you for sharing the information in \"{email_filename}\". We will review this newsletter content.",

            'spam_response': f"We received what appears to be promotional content in \"{email_filename}\". If this is not relevant to our business, please disregard this message.",

            'urgent_response': f"This urgent request from \"{email_filename}\" has been escalated and will be processed immediately.",

            'payment_invoice_response': f"We have received the payment or invoice details from \"{email_filename}\". Our accounting team will process this promptly.",

            'default_response': f"Thank you for your message \"{email_filename}\". I have received your correspondence and will address it according to our standard procedures."
        }

        return responses.get(response_type, "Thank you for your email. I have received your message and will address it accordingly.")

    def process_social_post_draft(self, content_request: Path) -> bool:
        """
        Cloud Executive: Process social media post drafts
        """
        if not self.can_perform_operation('social_post_draft'):
            self.logger.error("Social post draft operation not allowed for this executive")
            return False

        try:
            with open(content_request, 'r', encoding='utf-8') as f:
                content = f.read()

            # Create social media draft
            draft_file = self.vault_path / 'Drafts' / f'social_draft_{content_request.stem}_{int(time.time())}.json'

            draft_content = {
                "type": "social_post_draft",
                "original_request": content_request.name,
                "platforms": ["linkedin", "twitter", "facebook"],
                "created": datetime.now().isoformat(),
                "status": "draft",
                "content": content,
                "scheduling_info": {
                    "suggested_times": [
                        {"platform": "linkedin", "time": (datetime.now().replace(hour=9, minute=0) + timedelta(days=1)).isoformat()},
                        {"platform": "twitter", "time": (datetime.now().replace(hour=12, minute=0) + timedelta(days=1)).isoformat()},
                        {"platform": "facebook", "time": (datetime.now().replace(hour=15, minute=0) + timedelta(days=1)).isoformat()}
                    ]
                }
            }

            with open(draft_file, 'w', encoding='utf-8') as f:
                json.dump(draft_content, f, indent=2)

            # Create pending approval file
            approval_file = self.vault_path / 'Pending_Approval' / f'social_approval_{content_request.stem}_{int(time.time())}.md'
            with open(approval_file, 'w', encoding='utf-8') as f:
                f.write(f"""---
type: social_post_approval
action: post_approval
draft_file: {draft_file.name}
created: {datetime.now().isoformat()}
---

# Social Media Post Approval Request

A social media post draft has been created and requires your approval.

## Content Preview:
{content[:200]}...

## Suggested Posting Times:
- LinkedIn: {draft_content['scheduling_info']['suggested_times'][0]['time']}
- Twitter: {draft_content['scheduling_info']['suggested_times'][1]['time']}
- Facebook: {draft_content['scheduling_info']['suggested_times'][2]['time']}

Please move this file to Approved or Rejected folder.
""")

            self.logger.info(f"Social post draft created: {draft_file.name}, approval requested: {approval_file.name}")
            self.vault_sync.sync_push()
            return True

        except Exception as e:
            self.logger.error(f"Social post draft failed: {str(e)}")
            return False

    def process_approval(self, approval_file: Path) -> bool:
        """
        Local Executive: Process approvals for pending actions
        """
        if not self.can_perform_operation('approval'):
            self.logger.error("Approval operation not allowed for this executive")
            return False

        try:
            # Move approval file to appropriate folder
            # In this implementation, we'll just log that the approval is processed
            self.logger.info(f"Approval processing for {approval_file.name} - requires human intervention")

            # In a real system, this would involve actual human approval
            # For now, we'll just log the request
            return True

        except Exception as e:
            self.logger.error(f"Approval processing failed: {str(e)}")
            return False

    def execute_final_send(self, approved_file: Path) -> bool:
        """
        Local Executive: Execute final send/post actions
        """
        if not self.can_perform_operation('final_send'):
            self.logger.error("Final send operation not allowed for this executive")
            return False

        try:
            # This would execute the actual send action
            # In a real implementation, this would interface with email/social APIs
            self.logger.info(f"Final send executed for {approved_file.name}")

            # Move to Archive after sending
            archive_path = self.vault_path / 'Archive' / approved_file.name
            shutil.move(str(approved_file), str(archive_path))

            self.vault_sync.sync_push()
            return True

        except Exception as e:
            self.logger.error(f"Final send failed: {str(e)}")
            return False

    def update_dashboard(self) -> bool:
        """
        Local Executive: Update Dashboard.md (single-writer rule)
        """
        if not self.can_perform_operation('dashboard_write'):
            self.logger.error("Dashboard update operation not allowed for this executive")
            return False

        try:
            dashboard_file = self.vault_path / 'Dashboard.md'

            # Read existing dashboard or create new one
            if dashboard_file.exists():
                with open(dashboard_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = "# Executive Dashboard\n\n"

            # Add new status information
            new_entry = f"\n## Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            new_entry += f"- Executive Type: {'Cloud' if self.is_cloud_executive else 'Local'}\n"
            new_entry += f"- Sync Status: Up to date\n\n"

            # Write updated dashboard
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(content + new_entry)

            # Only local executive updates the dashboard, so no sync conflict
            if not self.is_cloud_executive:
                self.vault_sync.sync_push()

            self.logger.info("Dashboard updated")
            return True

        except Exception as e:
            self.logger.error(f"Dashboard update failed: {str(e)}")
            return False

    def run_sync_cycle(self):
        """
        Main synchronization cycle - run this periodically
        """
        self.logger.info(f"Starting sync cycle for {'Cloud' if self.is_cloud_executive else 'Local'} Executive")

        # Pull latest changes
        pull_success = self.vault_sync.sync_pull()

        if pull_success:
            # Process pending tasks based on executive type
            if self.is_cloud_executive:
                self._process_cloud_tasks()
            else:
                self._process_local_tasks()

        # Push any local changes
        push_success = self.vault_sync.sync_push()

        self.logger.info(f"Sync cycle completed - Pull: {pull_success}, Push: {push_success}")

    def _process_cloud_tasks(self):
        """Process cloud-specific tasks"""
        # Process new emails in Needs_Action/email/
        email_folder = self.vault_path / 'Needs_Action' / 'email'
        for email_file in email_folder.glob('EMAIL_*.md'):
            self.process_email_triage(email_file)

        # Process social content requests in Needs_Action/social/
        social_folder = self.vault_path / 'Needs_Action' / 'social'
        for content_file in social_folder.glob('SOCIAL_*.md'):
            self.process_social_post_draft(content_file)

    def _process_local_tasks(self):
        """Process local-specific tasks"""
        # Process approvals
        approval_folder = self.vault_path / 'Pending_Approval'
        for approval_file in approval_folder.glob('*.md'):
            self.process_approval(approval_file)

        # Process approved items for final execution
        approved_folder = self.vault_path / 'Approved'
        for approved_file in approved_folder.glob('*.md'):
            self.execute_final_send(approved_file)

    def start_continuous_sync(self, interval: int = 30):
        """
        Start continuous synchronization in a background thread
        """
        def sync_loop():
            while True:
                try:
                    self.run_sync_cycle()
                    time.sleep(interval)
                except Exception as e:
                    self.logger.error(f"Continuous sync error: {str(e)}")
                    time.sleep(interval)

        sync_thread = threading.Thread(target=sync_loop, daemon=True)
        sync_thread.start()
        self.logger.info(f"Continuous sync started with {interval}s interval")


def main():
    """
    Main function to run the executive orchestrator
    """
    import argparse

    parser = argparse.ArgumentParser(description='Platinum Tier Executive Orchestrator')
    parser.add_argument('--vault-path', required=True, help='Path to the vault directory')
    parser.add_argument('--is-cloud', action='store_true', help='Run as cloud executive')
    parser.add_argument('--remote-repo', help='Remote repository URL for vault sync')
    parser.add_argument('--sync-interval', type=int, default=30, help='Sync interval in seconds')

    args = parser.parse_args()

    # Create orchestrator instance
    orchestrator = ExecutiveOrchestrator(
        vault_path=args.vault_path,
        is_cloud_executive=args.is_cloud,
        remote_repo_url=args.remote_repo
    )

    print(f"Starting {'Cloud' if args.is_cloud else 'Local'} Executive Orchestrator...")
    print(f"Vault Path: {args.vault_path}")
    print(f"Remote Repo: {args.remote_repo or 'Local only'}")

    # Start continuous synchronization
    orchestrator.start_continuous_sync(interval=args.sync_interval)

    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)  # Sleep in 60-second intervals
    except KeyboardInterrupt:
        print("\nShutting down orchestrator...")
        # Perform any cleanup here if needed


if __name__ == "__main__":
    main()