# Ralph Wiggum Loop Usage Examples

The Ralph Wiggum Loop provides autonomous multi-step task completion for the AI Employee system.

## Basic Usage

```bash
# Process all items in /Needs_Action until complete
python ralph_loop.py "Process all items in /Needs_Action folder that require action" --max-iterations 10

# Process a specific task file with file-based completion
python ralph_loop.py "Process invoice approval task" --task-file "/Needs_Action/invoice_approval.md" --max-iterations 10

# Custom log file location
python ralph_loop.py "Handle pending emails" --log-file "Logs/email_processing.json" --max-iterations 5
```

## Completion Methods

The Ralph Loop supports two completion methods:

### 1. Promise-Based Completion
Claude should output `<promise>TASK_COMPLETE</promise>` when the task is complete:

```
Some processing output...
<promise>TASK_COMPLETE</promise>
Task has been completed successfully.
```

### 2. File-Based Completion
The task file is moved to the `/Done` directory to indicate completion.

## Integration with Existing Skills

The loop automatically integrates with all existing AI Employee skills:

- Bronze Tier: Scan, Plan, Process Task, Update Dashboard
- Silver/Gold Tier: Email handling, Odoo integration, Social media
- MCP Operations: All MCP systems (Odoo, Email, Social)

## Example Workflow

For the test flow "Stuck task → iterates → completes → logs iterations":

1. Create a stuck task in `/Needs_Action`
2. Run the Ralph Loop with appropriate prompt
3. System will iterate, using skills to process the task
4. Loop continues until task is complete (promise or file movement)
5. All iterations are logged to `/Logs/ralph_loop.json`

## Integration with Existing Batch Files

You can integrate the Ralph Loop into your existing workflows. For example, you can add it to daily_claude_run.bat:

```batch
@echo off
echo [%date% %time%] Starting AI Employee Daily Run >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"

cd /d "D:\code\AI-Employee"
echo [%date% %time%] Changed to project directory: %cd% >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"

echo [%date% %time%] Running Odoo approval handler... >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"
python handle_odoo_approvals.py >> "D:\code\AI-Employee\vault\Logs\daily_log.txt" 2>&1

echo [%date% %time%] Running Ralph Loop for stuck task processing... >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"
python ralph_loop.py "Process any stuck tasks in /Needs_Action that require attention" --max-iterations 8 >> "D:\code\AI-Employee\vault\Logs\daily_log.txt" 2>&1

echo [%date% %time%] Running Claude Code now... >> "D:\code\AI-Employee\vault\Logs\daily_log.txt"
... (rest of the existing daily_claude_run.bat commands)
```

## Example Command

```bash
python ralph_loop.py "Process all items in /Needs_Action that need attention" --max-iterations 10 --log-file "Logs/ralph_loop.json"
```