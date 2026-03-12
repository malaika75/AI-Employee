#!/usr/bin/env python3
"""
Test script to demonstrate social media posting for different platforms
"""

import asyncio
from social_mcp import SocialMediaMCP
import os

async def test_different_platforms():
    print("Testing social media posting for different platforms...")

    # Initialize the MCP
    mcp = SocialMediaMCP()

    platforms = ["Twitter", "Facebook", "Instagram"]  # Add more platforms as needed

    for platform in platforms:
        print(f"\n--- Creating post for {platform} ---")

        # Generate content
        content = mcp.generate_post_content()
        print(f"Generated content: {content}")

        # Create draft
        draft = mcp.draft_post(content, platform)
        print(f"Draft created with ID: {draft['post_id']}")

        # Create approval request
        approval_file = mcp.create_approval_request(draft)
        print(f"Approval request created: {approval_file}")

        print(f"Successfully created {platform} post! Check vault/Pending_Approval for approval request.")

if __name__ == "__main__":
    asyncio.run(test_different_platforms())
    print("\nTo approve these posts:")
    print("1. Look in vault/Pending_Approval/ for the approval files")
    print("2. Move any file you want to approve from Pending_Approval/ to Approved/")
    print("3. The social_mcp.py server will automatically process it and post to the platform")