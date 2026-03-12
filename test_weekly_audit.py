import unittest
import os
import tempfile
from datetime import datetime, timedelta
import json
import shutil
from weekly_audit import weekly_business_audit


class TestWeeklyAudit(unittest.TestCase):
    def setUp(self):
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create necessary directories
        os.makedirs("vault/Done", exist_ok=True)
        os.makedirs("vault/Logs", exist_ok=True)
        os.makedirs("vault/Briefings", exist_ok=True)
        os.makedirs("vault/Logs", exist_ok=True)

        # Create a sample Business_Goals.md
        with open("vault/Business_Goals.md", "w", encoding="utf-8") as f:
            f.write("""# Business Goals

## Mission
To provide innovative AI solutions that help businesses automate routine tasks and improve productivity.

## Current Objectives
- Achieve 99% uptime for all systems
- Maintain 95% email processing accuracy
- Improve customer satisfaction scores to 4.8/5.0
- Launch 3 new automation features per quarter

## Recent Achievements
- Processed 10,000+ emails with 98% accuracy
- Launched automated LinkedIn posting feature
- Achieved 99.2% system uptime for Q4

## Core Values
- Innovation
- Reliability
- Security
- Efficiency
- Transparency

## Upcoming Milestones
- Mobile application launch (Q2 2026)
- European market expansion (Q3 2026)
- AI model optimization (ongoing)

## Team Focus Areas
- AI/ML Development
- Natural Language Processing
- Automation Systems
""")

        # Create a sample Dashboard.md
        with open("vault/Dashboard.md", "w", encoding="utf-8") as f:
            f.write("""---
title: AI Employee Dashboard
status: active
last_updated: 2026-02-28
---

# Personal AI Employee Dashboard

## Current Status
- **AI Employee**: OPERATIONAL
- **Last Action**: Processed client payment reminder email
- **Tasks Completed Today**: 2
- **Tasks Pending**: 1

## Recent Activity
- [2026-02-28T10:20:00+05:00] Updated status of EMAIL_19ca24d5668b7315.md and EMAIL_19ca27f33e5186e9.md to completed
- [2026-02-28T10:00:00+05:00] Processed client response to payment update - moved to Done
- [2026-02-28T09:45:00+05:00] Sent response to client payment reminder email successfully
- [2026-02-28T09:20:00+05:00] Created LinkedIn post draft about AI Employee capabilities
- [2026-02-23T15:45:26Z] Completed processing meeting update request - moved to Done

## Pending Items
- LinkedIn post approval: LINKEDIN_APPROVAL_2026-02-28.md
- MCP Server running for email processing

## AI Employee Health
- **Status**: Operational
- **Memory Usage**: [N/A]
- **Response Time**: [N/A]
- **Last Check-in**: 2026-02-28T10:25:00+05:00

## Quick Actions
- [x] Review inbox items
- [x] Process pending tasks
- [x] Update logs
- [x] Generate daily report

## Today's Focus
- [x] Handle client payment reminder email
- [x] Process follow-up email
- [x] Create LinkedIn post draft

## Notes
- Successfully automated client communication workflow with proper approval for financial matters
- MCP server running for automated email sending
- LinkedIn draft created for approval and posting
- All email files in Needs_Action moved to Done with completed status

Odoo invoice 123 posted successfully for amount 750.
""")

        # Create a sample completed task file
        with open("vault/Done/SAMPLE_TASK.md", "w") as f:
            f.write("""---
from: "test@example.com"
subject: "Sample Task Completion"
received_time: "2026-02-22T10:00:00"
priority: 2
status: completed
---

This is a sample completed task for testing purposes.
""")

    def tearDown(self):
        os.chdir(self.original_cwd)
        # Clean up temp directory
        shutil.rmtree(self.temp_dir)

    def test_weekly_audit_creation(self):
        # Test that the audit creates a briefing file
        result = weekly_business_audit()

        # Check that briefing file was created
        self.assertTrue(os.path.exists(result["briefing_path"]))

        # Check that the briefing file contains expected sections
        with open(result["briefing_path"], 'r') as f:
            content = f.read()
            self.assertIn("Weekly CEO Briefing", content)
            self.assertIn("Executive Summary", content)
            self.assertIn("Revenue Analysis", content)
            self.assertIn("Completed Tasks", content)
            self.assertIn("Bottlenecks & Delays", content)
            self.assertIn("Proactive Suggestions", content)

        # Check that log was created
        self.assertTrue(os.path.exists("vault/Logs/weekly_audit.json"))

        # Check that log contains the audit entry
        with open("vault/Logs/weekly_audit.json", 'r') as f:
            logs = json.load(f)
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["action"], "weekly_audit")
            self.assertEqual(logs[0]["status"], "completed")
            self.assertIn("briefing_path", logs[0])

        # Verify return values
        self.assertIn("briefing_path", result)
        self.assertIn("revenue_data", result)
        self.assertIn("completed_tasks", result)
        self.assertIn("bottlenecks", result)
        self.assertIn("suggestions", result)
        self.assertIn("audit_log_id", result)

    def test_sunday_execution_simulation(self):
        # Test that the audit runs without error (simulating Sunday execution)
        result = weekly_business_audit()

        # Verify all components are working
        self.assertIsNotNone(result["audit_log_id"])
        self.assertTrue(len(result["suggestions"]) > 0)
        self.assertIsInstance(result["revenue_data"], dict)

        # Check dashboard was updated
        self.assertTrue(os.path.exists("vault/Dashboard.md"))

        # If dashboard exists, verify it was updated with audit info
        if os.path.exists("vault/Dashboard.md"):
            with open("vault/Dashboard.md", 'r') as f:
                content = f.read()
                self.assertIn("Weekly Audit", content)


def simulate_sunday_audit():
    """Simulate the Sunday audit process for demonstration"""
    print("Simulating Sunday weekly audit...")

    # Run the weekly audit
    result = weekly_business_audit()

    print("SUCCESS: Weekly audit completed successfully")
    print(f"SUCCESS: Briefing generated: {result['briefing_path']}")
    print(f"SUCCESS: Revenue data: ${result['revenue_data']['total_revenue']:,}")
    print(f"SUCCESS: Completed tasks: {len(result['completed_tasks'])}")
    print(f"SUCCESS: Bottlenecks identified: {len(result['bottlenecks'])}")
    print(f"SUCCESS: Proactive suggestions: {len(result['suggestions'])}")
    print(f"SUCCESS: Audit logged with ID: {result['audit_log_id']}")

    # Verify files were created
    print(f"SUCCESS: Briefing file exists: {os.path.exists(result['briefing_path'])}")
    print(f"SUCCESS: Audit log exists: {os.path.exists('vault/Logs/weekly_audit.json')}")
    print(f"SUCCESS: Dashboard updated: {os.path.exists('vault/Dashboard.md')}")

    return result


if __name__ == "__main__":
    # Run the test suite
    unittest.main(verbosity=2)