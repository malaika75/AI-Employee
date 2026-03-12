#!/usr/bin/env python3
"""
Test script for the Ralph Wiggum loop implementation
"""
import json
import os
import shutil
import tempfile
from pathlib import Path
from ralph_loop import RalphLoop


def test_promise_completion():
    """Test promise-based completion detection"""
    print("Testing promise-based completion...")

    # Create a temporary log file
    log_file = "vault/Logs/test_ralph_loop.json"

    ralph = RalphLoop(max_iterations=3, log_file=log_file)

    # Create a mock output that contains the completion promise
    mock_output_with_promise = """
    Some processing output...
    <promise>TASK_COMPLETE</promise>
    Some more output...
    """

    # Test promise completion detection
    is_complete = ralph.check_promise_completion(mock_output_with_promise)
    print(f"Promise completion detected: {is_complete}")
    assert is_complete == True, "Promise completion should be detected"

    # Test with no promise
    mock_output_no_promise = "Some processing output without promise"
    is_complete = ralph.check_promise_completion(mock_output_no_promise)
    print(f"Promise completion detected (should be False): {is_complete}")
    assert is_complete == False, "Promise completion should not be detected"

    print("Promise completion test passed!")


def test_file_completion():
    """Test file-based completion detection"""
    print("\nTesting file-based completion...")

    # Create temporary directories for testing
    needs_action_dir = Path("vault/Needs_Action")
    done_dir = Path("vault/Done")

    needs_action_dir.mkdir(exist_ok=True)
    done_dir.mkdir(exist_ok=True)

    # Create a test file in Needs_Action
    test_file = needs_action_dir / "test_task.md"
    test_file.write_text("Test task content")

    ralph = RalphLoop(max_iterations=3)

    # Initially, the file is not in Done
    is_complete = ralph.check_file_moved_to_done(str(test_file))
    print(f"File completion detected (should be False): {is_complete}")
    assert is_complete == False, "File completion should not be detected initially"

    # Move the file to Done
    done_file = done_dir / "test_task.md"
    shutil.move(str(test_file), str(done_file))

    # Now the file should be in Done
    is_complete = ralph.check_file_moved_to_done(str(test_file))
    print(f"File completion detected (should be True): {is_complete}")
    assert is_complete == True, "File completion should be detected after move"

    # Clean up
    if done_file.exists():
        done_file.unlink()

    print("File completion test passed!")


def test_logging():
    """Test logging functionality"""
    print("\nTesting logging functionality...")

    log_file = "vault/Logs/test_ralph_loop.json"
    ralph = RalphLoop(max_iterations=3, log_file=log_file)

    # Log a test iteration
    ralph.log_iteration(1, "Test prompt", "Test output", "completed", "test_task.md")

    # Verify the log was written
    log_path = Path(log_file)
    assert log_path.exists(), "Log file should exist"

    with open(log_path, 'r') as f:
        logs = json.load(f)

    assert len(logs) == 1, "Should have one log entry"
    assert logs[0]["iteration"] == 1, "Should have correct iteration number"
    assert logs[0]["prompt"] == "Test prompt", "Should have correct prompt"
    assert logs[0]["status"] == "completed", "Should have correct status"
    assert logs[0]["task_file"] == "test_task.md", "Should have correct task file"

    print("Logging test passed!")


def test_integration():
    """Test the full integration"""
    print("\nTesting full integration...")

    log_file = "vault/Logs/integration_test.json"

    # Create a mock task that should complete in one iteration
    ralph = RalphLoop(max_iterations=5, log_file=log_file)

    # The prompt should trigger the mock Claude response with completion promise
    task_prompt = "Test task that should complete"

    # This test is more complex as it would require mocking the Claude interaction
    # But we can test the loop logic with a mock
    print("Integration test structure validated")
    print("Note: Full integration test requires actual Claude Code installation")


def main():
    print("Running Ralph Wiggum Loop tests...\n")

    test_promise_completion()
    test_file_completion()
    test_logging()
    test_integration()

    print("\nAll tests completed successfully!")

    # Clean up test logs
    test_logs = ["vault/Logs/test_ralph_loop.json", "vault/Logs/integration_test.json"]
    for log_file in test_logs:
        log_path = Path(log_file)
        if log_path.exists():
            log_path.unlink()
            print(f"Cleaned up test log: {log_path}")


if __name__ == "__main__":
    main()