import asyncio
import os
from social_mcp import SocialMediaMCP


async def test_social_posting_flow():
    """
    Test the complete social media posting flow:
    Generate post → draft → approval → post → summary
    """
    print("Starting social media posting test flow...")

    # Initialize the MCP
    mcp = SocialMediaMCP()

    print("\n1. Generating post content...")
    content = mcp.generate_post_content(content_type="dashboard_summary")
    print(f"Generated content: {content}")

    print("\n2. Creating draft post...")
    draft = mcp.draft_post(content, "Twitter")
    print(f"Draft created with ID: {draft['post_id']}")

    print("\n3. Creating approval request...")
    approval_file = mcp.create_approval_request(draft)
    print(f"Approval request created: {approval_file}")

    print("\n4. Performing dry run (default behavior)...")
    result = await mcp.post_to_platform(content, "Twitter", dry_run=True)
    print(f"Dry run result: {result}")

    print("\n5. Getting summary...")
    summary = mcp.get_summary(result)
    print(f"Summary: {summary}")

    print("\n6. Checking log file...")
    if os.path.exists(mcp.log_file):
        with open(mcp.log_file, 'r') as f:
            import json
            logs = json.load(f)
            print(f"Log contains {len(logs)} entries")
            for log in logs:
                print(f"  - {log['timestamp']}: {log['operation']['action']}")

    print("\n7. Testing with different platforms...")
    platforms = ["Facebook", "Instagram", "Twitter"]

    for platform in platforms:
        print(f"\nTesting {platform}...")
        content = mcp.generate_post_content()
        draft = mcp.draft_post(content, platform)
        approval_file = mcp.create_approval_request(draft)
        result = await mcp.post_to_platform(content, platform, dry_run=True)
        summary = mcp.get_summary(result)
        print(f"  {platform} summary: {summary}")

    print("\nTest completed successfully!")


async def test_real_posting():
    """
    Test the real posting flow (requires approval)
    This is commented out to prevent accidental real posting
    """
    # Uncomment these lines when you want to test real posting with approval
    """
    print("Testing real posting flow (with approval)...")

    mcp = SocialMediaMCP()

    # For real posting, you would need to implement an approval verification system
    # This is a simplified example:

    content = mcp.generate_post_content()
    draft = mcp.draft_post(content, "Twitter")

    # Here you would check for approval (e.g., by checking if approval file has been approved)
    # For this test, we'll assume it's approved
    print("Simulating approval...")

    print("Performing real post (not actually posting, just showing the flow)...")

    # In a real scenario, you would check for approval status before real posting
    # result = await mcp.post_to_platform(content, "Twitter", dry_run=False)  # Real post
    # summary = mcp.get_summary(result)
    # print(f"Real posting summary: {summary}")
    """
    print("Real posting test is commented out to prevent accidental posts. Uncomment when ready.")


if __name__ == "__main__":
    asyncio.run(test_social_posting_flow())
    print("\n" + "="*50)
    asyncio.run(test_real_posting())