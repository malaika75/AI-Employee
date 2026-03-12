# Ralph Wiggum Loop Implementation - Gold Tier

## Overview
The Ralph Wiggum Loop is an autonomous multi-step task completion system that iterates until a task is complete. Named after the character who keeps trying until he gets it right, this implementation provides a wrapper script that enables Claude to work autonomously on complex tasks.

## Features Implemented

### 1. Wrapper Script
- **File**: `ralph_loop.py`
- **Function**: Provides autonomous iteration until task completion
- **Usage**: Command-line interface with configurable parameters

### 2. Completion Detection
- **Promise-based**: Claude outputs `<promise>TASK_COMPLETE</promise>` when done
- **File-based**: Monitors for task files moved to `/Done` directory
- **Flexible**: Supports both methods simultaneously

### 3. Iteration Control
- **Max iterations**: Configurable limit (default 10) to prevent infinite loops
- **Iteration logging**: Each iteration is fully logged with prompt, output, and status
- **Progress tracking**: Real-time monitoring of task progress

### 4. Comprehensive Logging
- **Log location**: `/Logs/ralph_loop.json`
- **Log contents**: Timestamp, iteration number, prompt, output, status, task file
- **JSON format**: Structured logging for analysis and monitoring

### 5. Skills Integration
Fully integrated with all existing AI Employee skills:
- Bronze Tier Skills: Scan, Plan, Process Task, Update Dashboard
- Silver/Gold Tier Skills: Email handling, Odoo integration, Social media
- MCP Operations: All MCP systems (Odoo, Email, Social) with approval workflows

## Command Line Usage

```bash
# Basic usage
python ralph_loop.py "Process all items in /Needs_Action" --max-iterations 10

# With specific task file
python ralph_loop.py "Process invoice approval task" --task-file "vault/Needs_Action/invoice_approval.md" --max-iterations 10

# Custom log file
python ralph_loop.py "Handle pending emails" --log-file "Logs/email_processing.json" --max-iterations 5
```

## Example Usage Pattern

For the test flow "Stuck task → iterates → completes → logs iterations":

1. **Stuck Task**: Place a task file in `/Needs_Action` that requires complex processing
2. **Iterates**: Ralph Loop calls Claude iteratively, using appropriate skills
3. **Completes**: Task is marked complete via promise or file movement
4. **Logs**: All iterations logged to `/Logs/ralph_loop.json`

## Implementation Details

### Core Components

1. **RalphLoop Class**:
   - Manages the iteration loop
   - Handles completion detection
   - Manages logging
   - Controls max iteration limit

2. **Completion Detection**:
   - `check_promise_completion()`: Regex pattern matching for `<promise>TASK_COMPLETE</promise>`
   - `check_file_moved_to_done()`: File system monitoring for task completion

3. **Integration Layer**:
   - Comprehensive prompt engineering to guide Claude
   - Skill system integration with all existing capabilities
   - MCP operation support with approval workflows

### Safety Features

- **Max Iterations**: Prevents infinite loops with configurable limit
- **Timeout Handling**: Claude execution timeouts to prevent hanging
- **Error Handling**: Comprehensive exception handling
- **Log Preservation**: All iterations preserved for analysis

## Integration Examples

The Ralph Loop can be integrated into existing workflows by adding it to `daily_claude_run.bat`:

```batch
echo [%date% %time%] Running Ralph Loop for stuck task processing...
python ralph_loop.py "Process any stuck tasks in /Needs_Action that require attention" --max-iterations 8 >> "D:\code\AI-Employee\vault\Logs\daily_log.txt" 2>&1
```

## Architecture

The Ralph Loop follows the existing AI Employee architecture:
- Uses existing skill system (`SKILL_*.md` files)
- Follows directory-based workflow (Needs_Action → Done)
- Supports approval workflows for sensitive operations
- Integrates with all MCP systems

## Testing

All functionality has been thoroughly tested:
- Promise completion detection
- File-based completion detection
- Logging functionality
- Integration with existing skills
- Max iteration limit enforcement

## Benefits

- **Autonomous Operation**: Tasks run without human intervention until completion
- **Robust Processing**: Complex multi-step tasks handled systematically
- **Monitoring**: Full visibility into task progress and iterations
- **Integration**: Works seamlessly with existing AI Employee infrastructure
- **Safety**: Built-in limits and error handling

The Ralph Wiggum Loop completes the Gold Tier requirements by providing an autonomous, iterative system that persists until complex tasks are completed while maintaining full logging and safety features.