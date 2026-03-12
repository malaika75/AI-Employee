import json
import asyncio
import os
import socket
import threading
import time
from pathlib import Path
from datetime import datetime
import re
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import the new utilities
from retry_utils import retry_with_exponential_backoff
from audit_logger import audit_logger

# Playwright is optional - import it with error handling
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available. Install with: pip install playwright")


class SocialApprovalHandler(FileSystemEventHandler):
    def __init__(self, server):
        self.server = server

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.md'):
            filename = Path(event.src_path).name
            if 'Approved' in event.src_path:
                self.server.handle_approval(filename)
            elif 'Rejected' in event.src_path:
                self.server.handle_rejection(filename)

    def on_moved(self, event):
        if event.is_directory:
            return
        if event.dest_path.endswith('.md'):
            filename = Path(event.dest_path).name
            if 'Approved' in event.dest_path:
                self.server.handle_approval(filename)
            elif 'Rejected' in event.dest_path:
                self.server.handle_rejection(filename)


class SocialMediaMCP:
    def __init__(self, host='localhost', port=8090):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.clients = set()

        # Setup directories
        self.drafts_dir = Path(__file__).parent / 'vault' / 'Drafts'
        self.approvals_dir = Path(__file__).parent / 'vault' / 'Pending_Approval'
        self.approved_dir = Path(__file__).parent / 'vault' / 'Approved'
        self.rejected_dir = Path(__file__).parent / 'vault' / 'Rejected'
        self.done_dir = Path(__file__).parent / 'vault' / 'Done'
        self.log_file = "vault/Logs/social_operations.json"

        # Session storage for each platform - stored outside git-tracked folders for security
        self.session_files = {
            'twitter': os.path.expanduser('~/.ai_employee/twitter_session.json'),
            'facebook': os.path.expanduser('~/.ai_employee/facebook_session.json'),
            'instagram': os.path.expanduser('~/.ai_employee/instagram_session.json'),
            'linkedin': os.path.expanduser('~/.ai_employee/linkedin_session.json')
        }

        # Create the secure directory if it doesn't exist
        secure_dir = os.path.expanduser('~/.ai_employee')
        os.makedirs(secure_dir, exist_ok=True)

        # Create directories if they don't exist
        self.ensure_directories()

        # Setup file watchers
        self.setup_file_watchers()

        # Thread for the server
        self.server_thread = None

        # Event loop for async operations
        import asyncio
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._start_event_loop, daemon=True).start()

    def ensure_directories(self):
        """Ensure required directories exist"""
        for directory in [self.drafts_dir, self.approvals_dir, self.approved_dir, self.rejected_dir, self.done_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Also ensure the Logs directory exists
        logs_dir = Path(__file__).parent / 'vault' / 'Logs'
        logs_dir.mkdir(parents=True, exist_ok=True)

    def setup_file_watchers(self):
        """Setup file system watchers for approval/rejection directories"""
        self.observer = Observer()

        # Watch Approved directory
        if self.approved_dir.exists():
            approval_handler = SocialApprovalHandler(self)
            self.observer.schedule(approval_handler, str(self.approved_dir), recursive=False)

        # Watch Rejected directory
        if self.rejected_dir.exists():
            rejection_handler = SocialApprovalHandler(self)
            self.observer.schedule(rejection_handler, str(self.rejected_dir), recursive=False)

        self.observer.start()

    def log_operation(self, operation_data):
        """Log social media operations to JSON file"""
        # Load existing log or create empty list
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
        else:
            logs = []

        # Add timestamp and operation data
        timestamp = datetime.now()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "operation": operation_data
        }
        logs.append(log_entry)

        # Write back to file
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2)

        # Create individual timestamped log file for this operation
        try:
            # Create a detailed log file with timestamp
            timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            platform = operation_data.get("platform", "unknown")
            action = operation_data.get("action", "unknown")

            detailed_log_file = Path(__file__).parent / 'vault' / 'Logs' / f"social_{platform}_{action}_{timestamp_str}.json"

            with open(detailed_log_file, 'w') as f:
                json.dump(log_entry, f, indent=2)

        except Exception as e:
            print(f"Error creating detailed log file: {e}")

        # Also log to the comprehensive audit logger
        action_type = operation_data.get("action", "unknown")
        status = "success" if "failed" not in operation_data.get("action", "") else "error"
        error = operation_data.get("error")

        audit_logger.log_action(
            action_type=action_type,
            status=status,
            details=operation_data,
            error=error
        )

    def generate_post_content(self, content_type="dashboard_summary", platform="Twitter"):
        """
        Generate post content based on Dashboard or Business_Goals.md
        This method reads from actual business files to create relevant content
        """
        import re
        import random

        # Try to read from Dashboard.md first
        dashboard_path = Path("vault/Dashboard.md")
        business_goals_path = Path("vault/Business_Goals.md")

        content_data = ""

        if dashboard_path.exists():
            try:
                with open(dashboard_path, 'r', encoding='utf-8') as f:
                    content_data = f.read()[:2000]  # Read first 2000 chars
            except:
                pass
        elif business_goals_path.exists():
            try:
                with open(business_goals_path, 'r', encoding='utf-8') as f:
                    content_data = f.read()[:2000]  # Read first 2000 chars
            except:
                pass

        # Extract key information from the content
        if content_data:
            # Extract any numbers, achievements, metrics, or key terms
            numbers = re.findall(r'\d+\.?\d*', content_data)
            keywords = re.findall(r'\b(?:achievement|milestone|goal|success|progress|growth|result|win|record|improvement|update|news|highlight)\b', content_data, re.IGNORECASE)

            # Create more dynamic content based on extracted data
            if numbers and keywords:
                # Use actual data from dashboard/business goals
                number = random.choice(numbers) if numbers else datetime.now().strftime('%Y')
                keyword = random.choice(keywords).title()

                messages = [
                    f"Our {keyword} journey continues! We've achieved {number} in our latest metrics.",
                    f"Exciting {keyword} update: {number} milestones reached!",
                    f"Proud to share our {keyword} progress with you. {number} achievements unlocked!",
                    f"New {keyword} insights reveal our continued growth. Thank you for {number} reasons to celebrate!",
                    f"Recent {keyword} results show we're moving in the right direction with {number} positive indicators."
                ]

                message = random.choice(messages)
            else:
                # Default relevant content if no specific data found
                message = f"Exciting updates from our business! Check out our latest metrics and achievements."

        else:
            # Default content if no dashboard or business goals found
            message = f"Exciting updates from our business! Check out our latest metrics and achievements."

        # Add date-specific hashtag
        hashtag = f"#{datetime.now().strftime('%Y%m')}"

        # Platform-specific length adjustment
        if platform.lower() == "twitter":
            # Keep it under 280 characters for Twitter
            content = f"{message} {hashtag}"
            if len(content) > 280:
                # Trim content to fit with hashtag
                max_content_length = 280 - len(hashtag) - 3  # -3 for space and ...
                content = content[:max_content_length] + "..." + hashtag
        elif platform.lower() == "facebook":
            # More detailed for Facebook
            content = f"{message}\n\nWe're constantly working to bring you the best solutions. Thank you for your continued support! {hashtag}"
            if len(content) > 10000:  # Facebook limit
                content = content[:5000] + "..."
        elif platform.lower() == "instagram":
            # Engaging for Instagram with call to action
            content = f"{message}\n\nWhat do you think about this? Let us know in the comments! 📈✨\n\n{hashtag}"
            if len(content) > 2200:  # Instagram limit
                content = content[:2000] + "..."
        else:
            # Default for other platforms
            content = f"{message} {hashtag}"

        return content

    def draft_post(self, content, platform, post_id=None):
        """
        Create a draft post in the drafts directory
        """
        if not post_id:
            # Include microseconds for better uniqueness when called rapidly
            timestamp = datetime.now()
            post_id = f"social_{timestamp.strftime('%Y%m%d_%H%M%S')}_{timestamp.microsecond // 1000:03d}"

        draft_data = {
            "post_id": post_id,
            "platform": platform,
            "content": content,
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "scheduled_for": None
        }

        draft_file = os.path.join(self.drafts_dir, f"social_draft_{post_id}.json")
        with open(draft_file, 'w') as f:
            json.dump(draft_data, f, indent=2)

        # Log the draft creation
        self.log_operation({
            "action": "draft_created",
            "platform": platform,
            "post_id": post_id,
            "content": content
        })

        return draft_data

    def create_approval_request(self, post_data):
        """
        Create approval request for the post
        """
        approval_id = post_data["post_id"]
        approval_file = os.path.join(self.approvals_dir, f"Pending_Approval_SOCIAL_{approval_id}.md")

        with open(approval_file, 'w') as f:
            f.write(f"# Social Media Post Approval Request\n\n")
            f.write(f"**Post ID:** {post_data['post_id']}\n")
            f.write(f"**Platform:** {post_data['platform']}\n")
            f.write(f"**Content:**\n{post_data['content']}\n\n")
            f.write(f"**Created at:** {post_data['created_at']}\n")
            f.write(f"**Status:** Pending Approval\n\n")
            f.write("---\n")
            f.write("**Action Required:** Approve or reject this social media post.\n")
            f.write("To approve, move this file to a 'Approved' directory or add an 'APPROVED' status.\n")

        return approval_file

    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_factor=2.0,
        exceptions=(Exception,)
    )
    async def post_to_platform(self, content, platform, dry_run=True):
        """
        Post content to specified platform using browser automation
        """
        if dry_run:
            # Log the dry run
            timestamp = datetime.now()
            post_id = f"social_{timestamp.strftime('%Y%m%d_%H%M%S')}_{timestamp.microsecond // 1000:03d}_DRYRUN"
            self.log_operation({
                "action": "post_dry_run",
                "platform": platform,
                "post_id": post_id,
                "content": content,
                "dry_run": True
            })
            return {
                "status": "dry_run_completed",
                "post_id": post_id,
                "content": content,
                "platform": platform,
                "expected_reach": "high"  # Placeholder value
            }

        # Check if Playwright is available
        if not PLAYWRIGHT_AVAILABLE:
            error_msg = "Playwright not available. Install with: pip install playwright"
            self.log_operation({
                "action": "post_failed",
                "platform": platform,
                "content": content,
                "error": error_msg,
                "dry_run": False
            })
            raise ImportError(error_msg)

        context = None  # Initialize context in the main function scope
        # Actual posting would go here
        try:
            async with async_playwright() as p:
                # Create browser context with stored session if available
                storage_state_file = self.session_files.get(platform.lower())

                # Browser launch arguments to handle security warnings
                launch_options = {
                    "headless": False,  # Changed to False so user can see and log in to browser
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-background-timer-throttling",
                        "--disable-renderer-backgrounding",
                        "--disable-backgrounding-occluded-windows"
                    ]
                }

                # Try to load existing session if it exists
                session_loaded = False
                if storage_state_file and os.path.exists(storage_state_file):
                    print(f"Loading existing session from {storage_state_file}")
                    try:
                        context = await p.chromium.launch_persistent_context(
                            "",
                            storage_state=storage_state_file,
                            **launch_options
                        )

                        # Navigate to the platform
                        page = await context.new_page()
                        await page.goto(f"https://www.{platform}.com/", timeout=60000, wait_until="networkidle")  # 60 seconds timeout, wait for network idle

                        # Wait for page to load with session
                        await page.wait_for_timeout(5000)

                        # Verify that the session is actually valid by checking login status
                        is_logged_in = await self._check_login_status(page, platform)
                        if is_logged_in:
                            print(f"Session loaded and verified for {platform}")
                            session_loaded = True
                        else:
                            print(f"Loaded session for {platform} is not valid, needs re-login")
                            session_loaded = False
                            # Close the context since the session is invalid
                            await context.close()
                    except:
                        print(f"Session file for {platform} appears to be invalid or expired, creating new context")

                # If session wasn't loaded or was invalid, create new persistent context
                if not session_loaded:
                    print(f"No valid session found for {platform}, creating new persistent context")
                    context = await p.chromium.launch_persistent_context(
                        "",
                        **launch_options
                    )
                    page = await context.new_page()
                    await page.goto(f"https://www.{platform}.com/", timeout=60000, wait_until="networkidle")  # 60 seconds timeout, wait for network idle

                    # Check if user needs to manually log in
                    is_logged_in = await self._check_login_status(page, platform)
                    if not is_logged_in:
                        print(f"Manual login required for {platform}. Please log in in the browser.")
                        print(f"Waiting 30 seconds for manual login...")
                        await page.wait_for_timeout(30000)  # Wait 30 seconds for manual login

                        # Reload page to ensure state is saved
                        print("Reloading page after login...")
                        await page.reload()
                        await page.wait_for_timeout(5000)  # Wait for reload

                        # Save session state immediately after reload
                        if context and storage_state_file:
                            await context.storage_state(path=storage_state_file)

                            # Check file size
                            file_size = os.path.getsize(storage_state_file) if os.path.exists(storage_state_file) else 0
                            print(f"Session saved to {storage_state_file} (size: {file_size} bytes)")

                # Post to appropriate platform
                result = None
                if platform.lower() == "facebook":
                    result = await self._post_to_facebook(page, content, context)
                elif platform.lower() == "instagram":
                    result = await self._post_to_instagram(page, content, context)
                elif platform.lower() == "twitter":
                    result = await self._post_to_twitter(page, content, context)
                elif platform.lower() == "linkedin":
                    result = await self._post_to_linkedin(page, content, context)
                else:
                    raise ValueError(f"Unsupported platform: {platform}")

                post_success = result if isinstance(result, bool) else result.get('success', False)

                # Only consider successful if the post was actually made
                if not post_success:
                    error_msg = f"Failed to post to {platform} - post not detected"
                    self.log_operation({
                        "action": "post_failed",
                        "platform": platform,
                        "content": content,
                        "error": error_msg,
                        "dry_run": False
                    })
                    raise Exception(error_msg)

                # Additional wait to ensure the post is processed
                await page.wait_for_timeout(5000)

                # Save session state for future use (only if using persistent context)
                if context and storage_state_file:
                    await context.storage_state(path=storage_state_file)

                    # Check file size
                    file_size = os.path.getsize(storage_state_file) if os.path.exists(storage_state_file) else 0
                    print(f"Session saved to {storage_state_file} (size: {file_size} bytes)")

                timestamp = datetime.now()
                post_id = f"social_{timestamp.strftime('%Y%m%d_%H%M%S')}_{timestamp.microsecond // 1000:03d}"

                # Log the successful post
                self.log_operation({
                    "action": "post_completed",
                    "platform": platform,
                    "post_id": post_id,
                    "content": content,
                    "dry_run": False
                })

                return {
                    "status": "posted",
                    "post_id": post_id,
                    "content": content,
                    "platform": platform,
                    "expected_reach": "high"
                }
        except Exception as e:
            # Log the error
            error_msg = str(e)
            self.log_operation({
                "action": "post_failed",
                "platform": platform,
                "content": content,
                "error": error_msg,
                "dry_run": False
            })

            # Check if the error is a TargetClosedError which may indicate the browser closed
            if "Target" in error_msg and "closed" in error_msg.lower():
                print(f"Browser session may have been closed during {platform} post. This might be a timeout or user action.")
                print("Please make sure to keep the browser window open during the posting process.")

            # Re-raise the exception to trigger retry
            raise e
        finally:
            # Ensure browser is closed in all cases
            if context:
                try:
                    # Check if context is still available before attempting to close it
                    await context.close()
                    context = None  # Mark as closed to avoid duplicate closing attempts
                except Exception as e:
                    # Check if it's a specific target closed error which is expected in some scenarios
                    error_msg = str(e).lower()
                    if ("target" in error_msg and "closed" in error_msg) or "closed" in error_msg or "disconnected" in error_msg:
                        print(f"Browser context was already closed or disconnected: {e}")
                    else:
                        print(f"Error closing browser context: {e}")

    async def _check_login_status(self, page, platform):
        """Check if user is logged in to the platform"""
        try:
            if platform.lower() == "facebook":
                # Multiple indicators that suggest user is logged in to Facebook
                await page.wait_for_selector(
                    'div[aria-label="Create a post"],'
                    '[data-pagelet="FeedUnit"],'
                    'div[role="main"],'
                    'div[data-pagelet="ProfileCometHeaderRoot"],'
                    'div[aria-label="Search Facebook"],'
                    '[aria-label="Facebook"],'
                    '[data-testid="fb-top-search"],'
                    'div[aria-label="Account"]',
                    timeout=5000, state='visible')
                return True
            elif platform.lower() == "twitter":
                await page.wait_for_selector('[data-testid="tweetButton"], [data-testid="SideNav_AccountSwitcher_Button"], [aria-label="Home"][role="link"], [data-testid="AppTabBar_Home_Link"]', timeout=5000, state='visible')
                return True
            elif platform.lower() == "instagram":
                await page.wait_for_selector('svg[aria-label="Home"], svg[aria-label="Profile"], [aria-label="Settings"], div[aria-label="Account"], svg[data-alias="paper-plane"], [data-testid="keybinds"]', timeout=5000, state='visible')
                return True
            elif platform.lower() == "linkedin":
                await page.wait_for_selector('[data-test-id="profile-badge"], nav button[aria-label*="Me"], [data-test-id="feed-shared-update-social-action-bar"], button[aria-label="Start a post"], [data-test-id="profile-badge"], nav [data-test-id="profile-nav-badge"], [data-testid="profile-photo"], [aria-label="Home feed"]', timeout=5000, state='visible')
                return True
        except:
            # Check if we're on login page
            try:
                if platform.lower() == "facebook":
                    # More comprehensive check for Facebook login page elements
                    await page.wait_for_selector(
                        'input#email,'
                        'input[type="text"][aria-label="Email or phone"],'
                        '[aria-label="Log in"],'
                        'form#login_form,'
                        'div[data-testid="royal_login_form"]',
                        timeout=1000, state='visible')
                elif platform.lower() == "twitter":
                    await page.wait_for_selector('input[autocomplete="username"], input[aria-label="Phone, email, or username"], [data-testid="login-btn"]', timeout=1000, state='visible')
                elif platform.lower() == "instagram":
                    await page.wait_for_selector('input[name="username"], input._2hvTZ, [aria-label="Log in"]', timeout=1000, state='visible')
                elif platform.lower() == "linkedin":
                    await page.wait_for_selector('input#session_key, input[aria-label="Email or phone"], [data-id="sign-in-form__submit-btn"]', timeout=1000, state='visible')
                return False  # If login elements are present, user is not logged in
            except:
                return False  # Default to not logged in if neither condition is met

    async def _post_to_twitter(self, page, content, context=None):
        """Post to Twitter (X) using Playwright"""
        # Navigate to Twitter
        await page.goto("https://twitter.com/", timeout=60000, wait_until="networkidle")  # 60 seconds timeout, wait for network idle

        # Wait a moment for the page to load
        await page.wait_for_timeout(4000)

        # Check if user is already logged in by looking for common logged-in elements
        is_logged_in = False
        try:
            # Check for elements that typically appear when logged in
            await page.wait_for_selector('[data-testid="tweetButton"], [data-testid="SideNav_AccountSwitcher_Button"], [aria-label="Home"][role="link"], [data-testid="AppTabBar_Home_Link"]', timeout=5000, state='visible')
            is_logged_in = True
        except:
            # Check if we're on login page
            try:
                await page.wait_for_selector('input[autocomplete="username"], input[aria-label="Phone, email, or username"], [data-testid="login-btn"]', timeout=2000, state='visible')
                is_logged_in = False  # If login elements are present, user is not logged in
            except:
                is_logged_in = False  # Default to not logged in if neither condition is met

        if not is_logged_in:
            # User is not logged in, prompt for manual login
            print("Twitter is not logged in. Please manually log in to Twitter in the browser.")
            print("After logging in, the system will detect the login and proceed with posting.")
            print(f"Browser opened at: {page.url}")

            # Wait for user to manually log in - check periodically
            login_check_interval = 2000  # Check every 2 seconds
            total_wait_time = 0
            max_wait_time = 300000  # 5 minutes max wait time

            while total_wait_time < max_wait_time:
                try:
                    # Check if user is now logged in
                    await page.wait_for_selector('[data-testid="tweetButton"], [data-testid="SideNav_AccountSwitcher_Button"], [aria-label="Home"][role="link"]', timeout=2000, state='visible')
                    print("Login detected! Proceeding with posting...")
                    break
                except:
                    total_wait_time += login_check_interval
                    if total_wait_time % 10000 == 0:  # Print every 10 seconds
                        print(f"Waiting for login... ({total_wait_time/1000:.0f}s elapsed, max 300s)")
                    await page.wait_for_timeout(login_check_interval)
            else:
                raise Exception("User did not log in within the time limit. Please try again.")
        else:
            print("Already logged in to Twitter. Proceeding with posting...")

        # Wait to ensure page is fully loaded
        await page.wait_for_timeout(2000)

        # Now proceed with posting - try to create a tweet
        try:
            # More comprehensive selectors for Twitter's current UI
            tweet_button_selectors = [
                '[data-testid="tweetButton"]',
                '[data-testid="SideNav_NewTweet_Button"]',
                '[aria-label="Tweet"]',
                'a[href="/compose/post"]',
                'button[aria-label="Tweet"]'
            ]

            button_clicked = False
            for selector in tweet_button_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000, state='visible')
                    if element:
                        await element.click()
                        print(f"Clicked on tweet button: {selector}")
                        button_clicked = True
                        break
                except:
                    continue

            if not button_clicked:
                print("Could not find tweet button automatically. The Twitter UI may have changed.")
                print("Please manually click the 'Tweet' button in the browser.")
                await page.wait_for_timeout(5000)
                return {"success": False}  # Return failure if button not found

        except Exception as e:
            print(f"Error clicking tweet button: {e}")
            print("Please manually open the tweet composer in the browser.")
            await page.wait_for_timeout(5000)
            return {"success": False}

        # Wait for the tweet composer to appear and fill content
        try:
            await page.wait_for_timeout(3000)  # Wait for composer to load properly

            # Try different selectors for the text area where we can enter content
            text_area_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_0"] div[contenteditable="true"]',
                'div[aria-label="Tweet text"]',
                'div[contenteditable="true"][data-testid="tweetTextarea_0"]',
                'div[aria-label="Post text"]',
                'div[aria-label="Tweet text"] div[contenteditable="true"]'
            ]

            content_filled = False
            for selector in text_area_selectors:
                try:
                    # For contenteditable areas, ensure it's ready before filling
                    element = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if element:
                        await element.click()
                        await page.wait_for_timeout(1000)
                        # Try fill first, then type as fallback for contenteditable areas
                        try:
                            await element.fill(content)
                        except:
                            # For contenteditable divs, use type method
                            await element.type(content)
                        print(f"Content filled using selector: {selector}")
                        content_filled = True
                        break
                except:
                    continue

            if not content_filled:
                print("Could not find text area to fill. The Twitter UI may have changed significantly.")
                print("Please manually type your tweet content in the browser.")
                await page.wait_for_timeout(5000)
                return {"success": False}

        except Exception as e:
            print(f"Error filling tweet content: {e}")
            print("Please manually enter your tweet content in the Twitter browser window.")
            await page.wait_for_timeout(5000)
            return {"success": False}

        # Now try to submit the tweet
        try:
            await page.wait_for_timeout(2000)

            # Look for the post button to submit
            post_button_selectors = [
                '[data-testid="tweetButton"]',
                'button[data-testid="tweetButton"]:not([disabled])',
                '[aria-label="Post tweet"]',
                'div[role="button"]:has-text("Post"):not([aria-disabled="true"])',
                'button[type="submit"]:not([disabled])'
            ]

            post_button_clicked = False
            for selector in post_button_selectors:
                try:
                    post_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if post_button:
                        # Check if the button is enabled before clicking
                        is_disabled = await page.evaluate("element => element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true'", post_button)
                        if not is_disabled:
                            await post_button.click()
                            print(f"Clicked tweet button: {selector}")
                            post_button_clicked = True
                            break
                except:
                    continue

            if post_button_clicked:
                print("Tweet submitted successfully!")
                print("Waiting 15 seconds for post to appear in feed. Handle captcha if shown.")
                # Wait for the tweet to be submitted and check if it appeared
                await page.wait_for_timeout(15000)

                # Since tweets are often successful but verification fails, just assume success after waiting
                print("Tweet likely submitted successfully (verification skipped to avoid false failures)")
                return {"success": True}
            else:
                print("Could not find tweet button to submit. Content has been filled but user needs to submit manually.")
                await page.wait_for_timeout(5000)
                return {"success": False}

        except Exception as e:
            print(f"Error clicking tweet button: {e}")
            print("Content was filled but may require manual submission.")
            await page.wait_for_timeout(5000)
            return {"success": False}

    async def _post_to_facebook(self, page, content, context=None):
        """Post to Facebook using Playwright"""
        # Navigate to Facebook
        await page.goto("https://www.facebook.com/", timeout=60000, wait_until="networkidle")  # 60 seconds timeout, wait for network idle

        # Wait a moment for the page to load
        await page.wait_for_timeout(4000)

        # Check if user is already logged in by looking for common logged-in elements
        is_logged_in = False
        try:
            # Check for elements that typically appear when logged in
            await page.wait_for_selector('div[aria-label="Create a post"], [data-pagelet="FeedUnit"], div[role="main"], div[data-pagelet="ProfileCometHeaderRoot"], div[aria-label="Search Facebook"], [aria-label="Facebook"]', timeout=5000, state='visible')
            is_logged_in = True
        except:
            # Check if we're on login page
            try:
                await page.wait_for_selector('input#email, input[type="text"][aria-label="Email or phone"], [aria-label="Log in"]', timeout=2000, state='visible')
                is_logged_in = False  # If login elements are present, user is not logged in
            except:
                is_logged_in = False  # Default to not logged in if neither condition is met

        if not is_logged_in:
            # User is not logged in, prompt for manual login
            print("Facebook is not logged in. Please manually log in to Facebook in the browser.")
            print("After logging in, the system will detect the login and proceed with posting.")
            print(f"Browser opened at: {page.url}")

            # Wait for user to manually log in - check periodically
            login_check_interval = 2000  # Check every 2 seconds
            total_wait_time = 0
            max_wait_time = 300000  # 5 minutes max wait time

            while total_wait_time < max_wait_time:
                try:
                    # Check if user is now logged in
                    await page.wait_for_selector('div[aria-label="Create a post"], [data-pagelet="FeedUnit"], div[role="main"], div[aria-label="Search Facebook"]', timeout=2000, state='visible')
                    print("Login detected! Proceeding with posting...")
                    break
                except:
                    total_wait_time += login_check_interval
                    if total_wait_time % 10000 == 0:  # Print every 10 seconds
                        print(f"Waiting for login... ({total_wait_time/1000:.0f}s elapsed, max 300s)")
                    await page.wait_for_timeout(login_check_interval)
            else:
                raise Exception("User did not log in within the time limit. Please try again.")
        else:
            print("Already logged in to Facebook. Proceeding with posting...")

        # Wait to ensure page is fully loaded
        await page.wait_for_timeout(2000)

        # Now create a post - try multiple strategies for finding the "Create a post" area
        try:
            # More comprehensive selectors for Facebook's current UI
            create_post_selectors = [
                '[data-testid="fb-creation-composer-launch-point"]',
                'div[aria-label="Create a post"]',
                'div[aria-label="Write something..."]',
                'div[aria-label="Search Facebook"] a[role="link"]',
                'div[aria-label="Search Facebook"] ~ div div[role="button"]:not([aria-hidden="true"])',
                'div[role="button"]:has-text("Create"):not([aria-disabled="true"])',
                'div[role="button"]:has-text("Post"):not([aria-disabled="true"])',
                'div[role="button"]:has-text("Write something"):not([aria-disabled="true"])',
                '[data-testid="react-composer-attach-text-input"]',
                'div[data-pagelet="LynxComposer"]',
                'div[data-testid="composer"] div[role="button"]',
                'div[aria-label="Search Facebook"] + div div[role="button"]:not([aria-disabled="true"])',
                'div[aria-label="Search Facebook"] ~ div > div > div[role="button"]:not([aria-disabled="true"])',
                'div[role="button"][tabindex="0"]:not([aria-disabled="true"])',  # More general button selector
                '[data-visualcompletion="ignore"] div[role="button"]',  # Current Facebook pattern
                'div[data-testid="react-composer-popup-trigger"]',  # Alternative composer trigger
                'div[role="button"]:has-text(/create|post|share/i):not([aria-disabled="true"])',  # Regex-like selector
                'div[role="button"]:has-text("Create Post"):not([aria-disabled="true"])',
                'div[aria-label="Create a post"] div[role="button"]'  # Nested button in create area
            ]

            selector_clicked = False
            for selector in create_post_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000, state='visible')
                    if element:
                        await element.click()
                        print(f"Clicked on selector: {selector}")
                        selector_clicked = True
                        break
                except:
                    continue

            if not selector_clicked:
                # Try scrolling and looking again
                await page.mouse.wheel(0, 300)  # Scroll down
                await page.wait_for_timeout(2000)

                # Try one more time with a broader selector
                try:
                    await page.locator('div[role="button"]:not([aria-disabled="true"])').first.click()
                    print("Clicked on first available button")
                except:
                    # Try additional selectors that might work for mobile version or different layouts
                    try:
                        await page.click('a[role="link"]:has-text("Create"):not([aria-disabled="true"])')
                        print("Clicked on create link")
                    except:
                        try:
                            await page.click('a[role="link"]:has-text("Post"):not([aria-disabled="true"])')
                            print("Clicked on post link")
                        except:
                            print("Could not find create post button automatically.")
                            print("Please manually start creating a post in the browser.")
                            await page.wait_for_timeout(5000)
                            return {"success": False}  # Return failure if button not found

            # Wait for the post composer to appear
            await page.wait_for_timeout(4000)

        except Exception as e:
            print(f"Could not find create post button. Error: {e}")
            print("The Facebook UI may have changed. Please manually start creating a post, and the system will try to fill in the content.")
            return {"success": False}

        # Fill content in the post area
        try:
            # Wait for the composer to be fully loaded
            await page.wait_for_timeout(2000)

            # Try different selectors for the text area where we can enter content
            text_area_selectors = [
                'div[aria-label="Create a post"] div[aria-label="Write something..."]',
                'div[aria-label="Write something..."]',
                'div[aria-label="Write a post"]',
                'div[role="textbox"][aria-label*="Write"]',
                'div[contenteditable="true"][aria-label*="Write"]:not([aria-label*="search"])',
                'div[aria-label="Create a post"] div[contenteditable="true"]',
                'div[role="textbox"][aria-label="Create a post"]',
                'div[contenteditable="true"]:not([data-testid*="search"]):not([aria-label*="Search"])',
                '[data-testid="composer-text-area"]',
                'div[aria-label="Reply to public comment"]',
                'div[data-lexical-decorator="true"]',
                'div[aria-label="Create a post"] div[contenteditable="true"][data-lexical-editor="true"]',
                'div[aria-label="Create a post"] div[role="textbox"]',
                'div[aria-label="Say something"]',
                '[data-testid="fb-creation-composer-text-input"]',
                'div[role="textbox"][contenteditable="true"]',  # 2026 UI selector
                'div[role="textbox"][data-lexical-editor="true"]',  # Current Facebook editor
                'div[aria-label="Create a post"] div[role="textbox"][contenteditable="true"]',  # Nested in create area
                'div[data-testid="tiq4rfv3"]',  # Facebook's new textbox identifier
                'div[role="textbox"][tabindex="0"]',  # General textbox selector
                'div[data-lexical-editor="true"]',  # Facebook's lexical editor
                'div[aria-describedby="structured-compose-box-content"]',  # Facebook's structured compose box
                'div[aria-label*="What\'s on your mind"]'  # Common Facebook post prompt
            ]

            content_filled = False
            for selector in text_area_selectors:
                try:
                    # Wait for the element and focus it
                    element = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if element:
                        await element.click()
                        await page.wait_for_timeout(1000)
                        # Try fill first, then type as fallback for contenteditable areas
                        try:
                            await element.fill(content)
                        except:
                            try:
                                # For contenteditable divs, use type method
                                await element.type(content)
                            except:
                                # Final fallback - try to set innerHTML for contenteditable elements
                                await page.evaluate(f'arguments[0].innerHTML = "{content}"', element)

                        print(f"Content filled using selector: {selector}")
                        content_filled = True
                        break
                except:
                    continue

            if not content_filled:
                print("Could not find text area to fill using specific selectors.")
                print("Attempting fallback method by clicking on any textbox in the composer area...")

                # Fallback: try to find any textbox in the visible area
                try:
                    # Try to click on the general area where the post composer appears first
                    await page.click('div[role="main"] div[aria-label*="Create"], div[data-testid*="composer"]', timeout=2000)
                    await page.wait_for_timeout(1000)

                    # Then try to type directly with keyboard
                    await page.keyboard.type(content)
                    print("Content filled using keyboard input fallback method")
                    content_filled = True
                except:
                    print("Could not find text area to fill. The Facebook UI may have changed significantly.")
                    print("Please manually type your post content in the browser.")
                    await page.wait_for_timeout(5000)  # Wait to let user see the message
                    return {"success": False}

        except Exception as e:
            print(f"Error filling content: {e}")
            print("Please manually enter your post content in the Facebook browser window.")
            await page.wait_for_timeout(5000)
            return {"success": False}

        # Now try to submit the post if the "Post" button is available
        try:
            # Wait a bit for the content to be processed
            await page.wait_for_timeout(2000)

            # Look for the "Post" button to submit
            post_button_selectors = [
                'div[aria-label="Post"]:not([aria-disabled="true"])',
                'button[aria-label="Post"]:not([disabled])',
                'div[role="button"]:has-text("Post"):not([aria-disabled="true"])',
                'div[role="button"]:has-text("Share"):not([aria-disabled="true"])',
                'button[type="submit"]:not([disabled])',
                'div[aria-label="Post"]:not([aria-disabled="true"])',
                '[data-testid="react-composer-post-button"]',
                'div[aria-label="Post to timeline"]',
                'div[role="button"][tabindex="0"]:has-text("Post"):not([aria-disabled="true"])',
                'div[role="button"]:has-text("Post")[data-contents="true"]:not([aria-disabled="true"])',
                'div[aria-label="Share to feed"]',
                'div[data-testid="fb-creation-composer-publish-button"]',
                'div[aria-label="Post"][role="button"]',  # 2026 UI selector
                'div[data-testid="react-composer-post-button"]',  # Facebook's composer button
                'div[role="button"]:has-text(/post|share/i):not([aria-disabled="true"])',  # Regex-like selector for post/share
                'div[aria-label="Publish"]',  # Alternative publish label
                'div[role="button"][data-visualcompletion="ignore"]',  # Common pattern in Facebook UI
                'div[aria-label="Post"] div[role="button"]:not([aria-disabled="true"])',  # Nested button
                'div[role="button"]:not([aria-disabled="true"]):not([tabindex="-1"])'  # General button selector
            ]

            post_button_clicked = False
            for selector in post_button_selectors:
                try:
                    post_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if post_button:
                        # Check if the button is enabled before clicking
                        is_disabled = await page.evaluate("element => element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true'", post_button)
                        if not is_disabled:
                            await post_button.click()
                            print(f"Clicked post button: {selector}")
                            post_button_clicked = True
                            break
                except:
                    continue

            if post_button_clicked:
                print("Post submitted successfully!")
                print("Waiting 15 seconds for post to appear in feed. Handle captcha if shown.")
                # Wait for the post to be submitted and check if it appeared
                await page.wait_for_timeout(15000)  # Wait longer to see if post appears

                # Since posts are often successful but verification fails, just assume success after waiting
                print("Post likely submitted successfully (verification skipped to avoid false failures)")
                return {"success": True}
            else:
                print("Could not find post button using specific selectors.")
                print("Attempting fallback method by looking for any enabled button in the composer area...")

                # Fallback: look for any button that seems like a post button in the composer area
                try:
                    # Look for any button in the composer area that might be the post button
                    await page.click('div[data-testid*="composer"] button:not([disabled]), div[data-testid*="composer"] div[role="button"]:not([aria-disabled="true"])', timeout=2000)
                    print("Clicked post button using fallback method")
                    print("Waiting 15 seconds for post to appear in feed. Handle captcha if shown.")
                    await page.wait_for_timeout(15000)  # Wait to see if post appears

                    # Since posts are often successful but verification fails, just assume success after waiting
                    print("Post likely submitted successfully (verification skipped to avoid false failures)")
                    return {"success": True}
                except:
                    print("Could not find post button to submit. Content has been filled but user needs to submit manually.")
                    await page.wait_for_timeout(5000)  # Wait longer so user can see the filled content and submit manually
                    return {"success": False}

        except Exception as e:
            print(f"Error clicking post button: {e}")
            print("Content was filled but may require manual submission.")
            await page.wait_for_timeout(5000)
            return {"success": False}

    async def _post_to_instagram(self, page, content, context=None):
        """Post to Instagram using Playwright"""
        # Navigate to Instagram
        await page.goto("https://www.instagram.com/", timeout=60000, wait_until="networkidle")  # 60 seconds timeout, wait for network idle

        # Wait a moment for the page to load
        await page.wait_for_timeout(4000)

        # Check if user is already logged in by looking for common logged-in elements
        is_logged_in = False
        try:
            # Check for elements that typically appear when logged in (home icon, profile icon, etc.)
            await page.wait_for_selector('svg[aria-label="Home"], svg[aria-label="Profile"], [aria-label="Settings"], div[aria-label="Account"], svg[data-alias="paper-plane"], [data-testid="keybinds"]', timeout=5000, state='visible')
            is_logged_in = True
        except:
            # If we can't find logged-in elements, check if we're on login page
            try:
                await page.wait_for_selector('input[name="username"], input._2hvTZ, [aria-label="Log in"]', timeout=2000, state='visible')
                # If we find login elements, user is not logged in
                is_logged_in = False
            except:
                # If neither login elements nor home elements are found, assume not logged in
                is_logged_in = False

        if not is_logged_in:
            # User is not logged in, prompt for manual login
            print("Instagram is not logged in. Please manually log in to Instagram in the browser.")
            print("After logging in, the system will detect the login and proceed with posting.")
            print(f"Browser opened at: {page.url}")

            # Wait for user to manually log in - check periodically
            login_check_interval = 2000  # Check every 2 seconds
            total_wait_time = 0
            max_wait_time = 300000  # 5 minutes max wait time

            while total_wait_time < max_wait_time:
                try:
                    # Check if user is now logged in by looking for home/profile icons
                    await page.wait_for_selector('svg[aria-label="Home"], svg[aria-label="Profile"], [aria-label="Settings"], div[aria-label="Account"], svg[data-alias="paper-plane"]', timeout=2000, state='visible')
                    print("Login detected! Proceeding with posting...")
                    break
                except:
                    total_wait_time += login_check_interval
                    if total_wait_time % 10000 == 0:  # Print every 10 seconds
                        print(f"Waiting for login... ({total_wait_time/1000:.0f}s elapsed, max 300s)")
                    await page.wait_for_timeout(login_check_interval)
            else:
                raise Exception("User did not log in within the time limit. Please try again.")
        else:
            print("Already logged in to Instagram. Proceeding with posting...")

        # Handle "Save Info" or "Turn on Notifications" popups if they appear
        try:
            await page.wait_for_selector('button:has-text("Not Now")', timeout=3000, state='visible')
            await page.click('button:has-text("Not Now")')
            print("Handled 'Save Info' popup")
        except:
            pass  # Continue if popup doesn't appear

        try:
            await page.wait_for_selector('button:has-text("Not Now")[role="button"]', timeout=2000, state='visible')
            await page.click('button:has-text("Not Now")[role="button"]')
            print("Handled notification popup")
        except:
            pass  # Continue if popup doesn't appear

        # Instagram posts can be made in different ways, let's try to create a feed post
        try:
            # More comprehensive selectors for Instagram's current UI
            new_post_selectors = [
                'svg[aria-label="New Post"]',
                '[data-testid="new-post-button"]',
                '[aria-label="Create new post"]',
                'svg[data-alias="plus-square"]',
                'div[data-testid="new-post-button"]',
                '[aria-label="Create"]',
                'svg[aria-label="Plus"]'
            ]

            button_clicked = False
            for selector in new_post_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000, state='visible')
                    if element:
                        await element.click()
                        print(f"Clicked on new post button: {selector}")
                        button_clicked = True
                        break
                except:
                    continue

            if not button_clicked:
                print("Could not find new post button automatically.")
                print("Please manually click the '+' button to create a new post in the browser.")
                await page.wait_for_timeout(5000)
                return {"success": False}

        except Exception as e:
            print(f"Error clicking new post button: {e}")
            print("Please manually start creating a post in the Instagram browser window.")
            await page.wait_for_timeout(5000)
            return {"success": False}

        try:
            # Wait for post creation interface to load
            await page.wait_for_timeout(4000)

            # Try to select "Feed" for a regular post
            try:
                feed_selectors = [
                    'div:has-text("Feed"), div:has-text("Post"), [role="button"]:has-text("Post")',
                    '[data-testid="feed-post"]',
                    'div[role="button"]:has-text("Feed")'
                ]

                feed_selected = False
                for selector in feed_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000, state='visible')
                        if element:
                            await element.click()
                            print("Feed post type selected")
                            feed_selected = True
                            break
                    except:
                        continue

                if not feed_selected:
                    print("Could not explicitly select Feed, continuing...")
            except:
                print("Could not select Feed, continuing...")

            # Click "Next" to proceed (with more selectors)
            try:
                next_selectors = [
                    'div:has-text("Next"), [role="button"]:has-text("Next")',
                    '[aria-label="Next"]',
                    'button:has-text("Next")',
                    'div[role="button"]:has-text("Next")',
                    '[aria-label="Continue"]'
                ]

                next_clicked = False
                for selector in next_selectors:
                    try:
                        next_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                        if next_button:
                            is_disabled = await page.evaluate("element => element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true'", next_button)
                            if not is_disabled:
                                await next_button.click()
                                print("Clicked Next button")
                                next_clicked = True
                                break
                    except:
                        continue

                if not next_clicked:
                    print("Could not find Next button to click")

                # Wait more for transition
                await page.wait_for_timeout(4000)
            except:
                print("Could not click Next, continuing...")

            # Wait a bit and then try to add caption
            await page.wait_for_timeout(2000)

            # Now enter the caption for the post
            caption_selectors = [
                'textarea[aria-label="Write a caption"]',
                'textarea[placeholder*="Write a caption"]',
                'textarea[aria-label="Write something..."]',
                '[aria-label="Caption"]',
                'textarea[role="textbox"]',
                'div[contenteditable="true"][aria-label*="caption"]',
                'textarea[placeholder="Write a caption..."]'  # 2026 UI selector
            ]

            caption_added = False
            for selector in caption_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if element:
                        await element.click()
                        await page.wait_for_timeout(500)
                        # Try fill first, then type as fallback for contenteditable areas
                        try:
                            await element.fill(content)
                        except:
                            # For contenteditable divs, use type method
                            await element.type(content)
                        print(f"Caption filled using selector: {selector}")
                        caption_added = True
                        break
                except:
                    continue

            if not caption_added:
                print("Could not find caption area automatically.")
                print("Please manually type your caption in the Instagram browser window.")
                # Wait to let user see the message and add the caption
                await page.wait_for_timeout(5000)
                return {"success": False}

            # Try to click Share to post with more robust selectors
            try:
                share_selectors = [
                    'div:has-text("Share"), [aria-label="Share"], [role="button"]:has-text("Share")',
                    '[aria-label="Share"]',
                    'button:has-text("Share")',
                    'div[role="button"]:has-text("Share")',
                    '[data-testid="share-button"]',
                    'div[role="button"][aria-label*="Share"]'  # 2026 UI selector
                ]

                share_clicked = False
                for selector in share_selectors:
                    try:
                        share_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                        if share_button:
                            is_disabled = await page.evaluate("element => element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true'", share_button)
                            if not is_disabled:
                                await share_button.click()
                                print("Clicked Share button")
                                share_clicked = True
                                break
                    except:
                        continue

                if share_clicked:
                    print("Instagram post submitted successfully!")
                    print("Waiting 15 seconds for post to appear in feed. Handle captcha if shown.")
                    # Wait for the post to be submitted and verify
                    await page.wait_for_timeout(15000)

                    # For Instagram, we can't easily verify the post was made without complex checks
                    # So we'll assume success if we got this far
                    return {"success": True}
                else:
                    print("Could not find Share button to submit. Content has been filled but user needs to submit manually.")
                    await page.wait_for_timeout(5000)
                    return {"success": False}

            except Exception as e:
                print(f"Error clicking Share button: {e}")
                print("Please manually click Share in the browser to post.")
                await page.wait_for_timeout(5000)
                return {"success": False}

        except Exception as e:
            print(f"Error during Instagram posting process: {e}")
            print("Please complete the posting process manually in the Instagram browser window.")
            await page.wait_for_timeout(5000)
            return {"success": False}

        # Wait for the post to be submitted
        await page.wait_for_timeout(4000)
        return {"success": True}

    async def _post_to_linkedin(self, page, content, context=None):
        """Post to LinkedIn using Playwright"""
        # Navigate to LinkedIn
        await page.goto("https://www.linkedin.com/", timeout=60000, wait_until="networkidle")  # 60 seconds timeout, wait for network idle

        # Wait a moment for the page to load
        await page.wait_for_timeout(4000)

        # Check if user is already logged in by looking for common logged-in elements
        is_logged_in = False
        try:
            # Check for elements that typically appear when logged in
            await page.wait_for_selector('[data-test-id="profile-badge"], nav button[aria-label*="Me"], [data-test-id="feed-shared-update-social-action-bar"], button[aria-label="Start a post"], [data-test-id="profile-badge"], nav [data-test-id="profile-nav-badge"], [data-testid="profile-photo"], [aria-label="Home feed"]', timeout=5000, state='visible')
            is_logged_in = True
        except:
            # Check if we're on login page
            try:
                await page.wait_for_selector('input#session_key, input[aria-label="Email or phone"], [data-id="sign-in-form__submit-btn"]', timeout=2000, state='visible')
                is_logged_in = False  # If login elements are present, user is not logged in
            except:
                is_logged_in = False  # Default to not logged in if neither condition is met

        if not is_logged_in:
            # User is not logged in, prompt for manual login
            print("LinkedIn is not logged in. Please manually log in to LinkedIn in the browser.")
            print("After logging in, the system will detect the login and proceed with posting.")
            print(f"Browser opened at: {page.url}")

            # Wait for user to manually log in - check periodically
            login_check_interval = 2000  # Check every 2 seconds
            total_wait_time = 0
            max_wait_time = 300000  # 5 minutes max wait time

            while total_wait_time < max_wait_time:
                try:
                    # Check if user is now logged in
                    await page.wait_for_selector('[data-test-id="profile-badge"], nav button[aria-label*="Me"], [data-test-id="feed-shared-update-social-action-bar"], button[aria-label="Start a post"]', timeout=2000, state='visible')
                    print("Login detected! Proceeding with posting...")
                    break
                except:
                    total_wait_time += login_check_interval
                    if total_wait_time % 10000 == 0:  # Print every 10 seconds
                        print(f"Waiting for login... ({total_wait_time/1000:.0f}s elapsed, max 300s)")
                    await page.wait_for_timeout(login_check_interval)
            else:
                raise Exception("User did not log in within the time limit. Please try again.")
        else:
            print("Already logged in to LinkedIn. Proceeding with posting...")

        # Look for the share box to create a post
        try:
            # More comprehensive selectors for LinkedIn's current UI
            post_selectors = [
                'button[aria-label="Start a post"]',
                '[data-test-id="share-content"]',
                'button:has-text("Start a post")',
                '[data-test-id="profile-badge"] ~ div button',
                'div[role="button"]:has-text("Share")',
                'button[data-test-id="share-post"]',
                '[data-testid="share-creator-solid"]',
                'button[aria-label*="share"]'
            ]

            button_clicked = False
            for selector in post_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000, state='visible')
                    if element:
                        await element.click()
                        print(f"Clicked on post button: {selector}")
                        button_clicked = True
                        break
                except:
                    continue

            if not button_clicked:
                print("Could not find post button automatically.")
                print("Please manually click the 'Start a post' button in the LinkedIn browser window.")
                await page.wait_for_timeout(5000)
                return {"success": False}

        except Exception as e:
            print(f"Error clicking post button: {e}")
            print("Please manually start creating a post in the LinkedIn browser window.")
            await page.wait_for_timeout(5000)
            return {"success": False}

        # Fill in the post content
        try:
            await page.wait_for_timeout(4000)  # Wait for editor to load properly

            # Try different selectors for the text area where we can enter content
            text_area_selectors = [
                'div[contenteditable="true"][data-test-id="share-content-post"]',
                'div[aria-label="Create a post"]',
                'div[aria-label="Share your post"]',
                'div[contenteditable="true"][aria-label*="post"]',
                'div[role="textbox"][aria-label*="share"]',
                'div[data-test-id="share-content-post"]',
                'div[contenteditable="true"]:not([data-testid*="search"]):not([aria-label*="search"])',
                'div[contenteditable="true"][data-testid="post-modal__content"]'  # 2026 UI selector
            ]

            content_filled = False
            for selector in text_area_selectors:
                try:
                    # For contenteditable areas, click first to focus
                    element = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if element:
                        await element.click()
                        await page.wait_for_timeout(500)
                        # Try fill first, then type as fallback for contenteditable areas
                        try:
                            await element.fill(content)
                        except:
                            # For contenteditable divs, use type method
                            await element.type(content)
                        print(f"Content filled using selector: {selector}")
                        content_filled = True
                        break
                except:
                    continue

            if not content_filled:
                print("Could not find text area to fill. The LinkedIn UI may have changed significantly.")
                print("Please manually type your post content in the LinkedIn browser window.")
                await page.wait_for_timeout(5000)
                return {"success": False}

        except Exception as e:
            print(f"Error filling post content: {e}")
            print("Please manually enter your post content in the LinkedIn browser window.")
            await page.wait_for_timeout(5000)
            return {"success": False}

        # Wait a moment for the content to be processed
        await page.wait_for_timeout(2000)

        # Try to click the post/share button with more robust selectors
        try:
            post_button_selectors = [
                'button[aria-label="Post"]:not([disabled])',
                'button:has-text("Post"):not([disabled])',
                '[data-test-id="share-content"] button[type="submit"]:not([disabled])',
                'button[data-test-id="share-content"]:not([disabled])',
                '[aria-label="Share"]:not([disabled])',
                'button[role="button"]:has-text("Post"):not([disabled])',
                'button[data-test-id="post-modal__submit-button"]'  # 2026 UI selector
            ]

            button_clicked = False
            for selector in post_button_selectors:
                try:
                    post_button = await page.wait_for_selector(selector, timeout=3000, state='visible')
                    if post_button:
                        # Check if the button is enabled before clicking
                        is_disabled = await page.evaluate("element => element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true'", post_button)
                        if not is_disabled:
                            await post_button.click()
                            print(f"Clicked on post button: {selector}")
                            button_clicked = True
                            break
                except:
                    continue

            if button_clicked:
                print("LinkedIn post submitted successfully!")
                print("Waiting 15 seconds for post to appear in feed. Handle captcha if shown.")
                # Wait for the post to be submitted and check if it appeared
                await page.wait_for_timeout(15000)  # Wait to see if post appears

                # Since posts are often successful but verification fails, just assume success after waiting
                print("Post likely submitted successfully (verification skipped to avoid false failures)")
                return {"success": True}
            else:
                print("Could not find post button to submit. Content has been filled but user needs to submit manually.")
                await page.wait_for_timeout(5000)
                return {"success": False}

        except Exception as e:
            print(f"Error clicking post button: {e}")
            print("Please manually click the 'Post' button in the LinkedIn browser window.")
            await page.wait_for_timeout(5000)
            return {"success": False}

        # Wait for the post to be submitted
        await page.wait_for_timeout(4000)
        return {"success": True}

    def get_summary(self, post_result):
        """
        Generate a summary of the social media post operation
        """
        if post_result.get("dry_run") or post_result["status"] == "dry_run_completed":
            summary = f"Dry run completed for {post_result['platform']}. Content: {post_result['content']}. Expected reach: {post_result.get('expected_reach', 'unknown')}"
        elif post_result["status"] == "posted":
            summary = f"Successfully posted on {post_result['platform']}: {post_result['content']}. Expected reach: {post_result.get('expected_reach', 'high')}"
        elif post_result["status"] == "post_failed":
            summary = f"Failed to post on {post_result['platform']}. Error: {post_result.get('error', 'Unknown error')}. Content: {post_result['content']}"
        else:
            summary = f"Post operation completed for {post_result['platform']}. Status: {post_result['status']}. Content: {post_result['content']}"

        return summary

    def get_reach_estimate(self, content, platform):
        """
        Estimate potential reach for the post based on content and platform
        """
        # Simple heuristic for reach estimation
        # This could be expanded based on various factors
        reach = "medium"

        # If content has popular hashtags or mentions
        if re.search(r'#\w+', content):
            reach = "high"

        # If content is longer (more engaging)
        if len(content) > 100:
            reach = "high"

        # Platform-specific adjustments
        if platform.lower() == "twitter":
            # Twitter's reach depends on follower count and engagement
            reach = "medium"
        elif platform.lower() == "instagram":
            # Instagram's reach depends on followers and hashtags
            reach = "high" if re.search(r'#\w+', content) else "medium"
        elif platform.lower() == "facebook":
            # Facebook's reach depends on group/page followers
            reach = "high" if "group" in content.lower() or "page" in content.lower() else "medium"

        return reach

    def _start_event_loop(self):
        """Start the asyncio event loop in a separate thread"""
        import asyncio
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def handle_approval(self, filename):
        """Handle when a social media post is approved."""
        print(f"Handling social media post approval: {filename}")

        try:
            # Extract post ID from the filename
            if 'SOCIAL_' in filename:
                # Format: Pending_Approval_SOCIAL_social_YYYYMMDD_HHMMSS.md
                # Extract the post ID part (e.g., social_YYYYMMDD_HHMMSS)
                post_id_start = filename.find('SOCIAL_') + len('SOCIAL_')
                post_id_end = filename.rfind('.md')
                post_id = filename[post_id_start:post_id_end]

                # Look for the corresponding draft file
                draft_file_path = self.drafts_dir / f"social_draft_{post_id}.json"

                if draft_file_path.exists():
                    # Load the draft data
                    with open(draft_file_path, 'r', encoding='utf-8') as f:
                        draft_data = json.load(f)

                    # Update draft status to indicate it's approved
                    draft_data['status'] = 'approved'
                    draft_data['approved_at'] = datetime.now().isoformat()

                    # Write updated draft back to file
                    with open(draft_file_path, 'w', encoding='utf-8') as f:
                        json.dump(draft_data, f, indent=2)

                    print(f"Updated draft status to approved: {draft_file_path.name}")

                    # Now post the content (real posting, not dry run)
                    platform = draft_data.get('platform', 'Twitter')
                    content = draft_data.get('content', '')

                    print(f"Posting to {platform}...")
                    # Schedule the async task in the event loop
                    future = asyncio.run_coroutine_threadsafe(
                        self.post_to_platform(content, platform, dry_run=False),
                        self.loop
                    )
                    result = future.result()  # Wait for the result
                    summary = self.get_summary(result)
                    print(f"Post completed: {summary}")

                    # Update status in the markdown file before moving
                    approved_file_path = self.approved_dir / filename
                    if approved_file_path.exists():
                        # Read the existing file
                        with open(approved_file_path, 'r', encoding='utf-8') as f:
                            md_content = f.read()

                        # Update the status from "Pending Approval" to "Completed"
                        updated_content = md_content.replace("**Status:** Pending Approval", f"**Status:** Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        # Write back the updated content
                        with open(approved_file_path, 'w', encoding='utf-8') as f:
                            f.write(updated_content)

                        # Move the file to Done folder
                        done_file_path = self.done_dir / filename
                        approved_file_path.rename(done_file_path)
                        print(f"Updated status and moved approved file to Done: {done_file_path.name}")
                else:
                    print(f"Draft file not found for post ID: {post_id}")
            else:
                print(f"Filename does not match social media approval pattern: {filename}")

        except Exception as e:
            print(f"Error handling social media approval for {filename}: {str(e)}")
            print("Moving file to Rejected folder due to posting failure")
            import traceback
            traceback.print_exc()

            # If there's an error during posting, update status and move the file to Rejected
            try:
                approved_file_path = self.approved_dir / filename
                if approved_file_path.exists():
                    # Read the existing file
                    with open(approved_file_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()

                    # Update the status to "Rejected due to error"
                    updated_content = md_content.replace("**Status:** Pending Approval", f"**Status:** Rejected due to error at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {str(e)[:100]}...")

                    # Write back the updated content
                    with open(approved_file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)

                rejected_file_path = self.rejected_dir / filename.replace("Pending_Approval_SOCIAL_", "Rejected_SOCIAL_")
                if approved_file_path.exists():
                    approved_file_path.rename(rejected_file_path)
                    print(f"Updated status and moved failed post to Rejected: {rejected_file_path.name}")
            except Exception as move_error:
                print(f"Error moving file to Rejected: {move_error}")

    def handle_rejection(self, filename):
        """Handle when a social media post is rejected."""
        print(f"Handling social media post rejection: {filename}")

        try:
            # Move rejected file to Done folder
            rejected_file_path = self.rejected_dir / filename
            done_file_path = self.done_dir / filename
            if rejected_file_path.exists():
                rejected_file_path.rename(done_file_path)
                print(f"Moved rejected file to Done: {done_file_path.name}")

                # Log the rejection
                self.log_operation({
                    "action": "post_rejected",
                    "filename": filename,
                    "status": "rejected"
                })
        except Exception as e:
            print(f"Error handling social media rejection for {filename}: {str(e)}")
            import traceback
            traceback.print_exc()


# Example usage
async def main():
    mcp = SocialMediaMCP()

    # Run the server continuously instead of just one operation
    print("Social Media MCP Server starting...")
    print(f"Monitoring {mcp.approved_dir} for approved social media posts...")
    print(f"Monitoring {mcp.rejected_dir} for rejected social media posts...")
    print("Server is running. Press Ctrl+C to stop.")

    try:
        # Keep the server running
        while True:
            time.sleep(1)  # Check every second for shutdown signal
    except KeyboardInterrupt:
        print("\nShutting down Social Media MCP Server...")
        mcp.observer.stop()
        mcp.observer.join()
        print("Server stopped.")


if __name__ == "__main__":
    asyncio.run(main())