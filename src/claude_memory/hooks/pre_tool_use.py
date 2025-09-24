#!/usr/bin/env python3
"""
Pre-tool-use hook for Claude Code integration.

Intercepts Task tool calls to inject memory context for sub-agents.
"""

import json
import sys
from pathlib import Path

try:
    from claude_memory import MemoryAPI
except ImportError:
    # If package not installed, try to import from parent directory
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from claude_memory import MemoryAPI


def inject_memory_instructions(input_data: dict, task_context: dict) -> dict:
    """
    Inject memory instructions into Task tool prompts.

    Args:
        input_data: Original tool input from Claude
        task_context: Current memory context

    Returns:
        Modified input data with memory instructions
    """
    tool_name = input_data.get('tool_name')

    if tool_name != 'Task':
        return input_data

    # Extract task name from prompt if possible
    prompt = input_data.get('tool_input', {}).get('prompt', '')

    # Simple heuristic to extract task name - in practice, this could be more sophisticated
    task_name = "current-task"  # Default task name

    # Look for task patterns in the prompt
    if 'task_name=' in prompt:
        # Extract from explicit task_name parameter
        start = prompt.find('task_name=') + 10
        end = prompt.find(',', start)
        if end == -1:
            end = prompt.find(')', start)
        if end == -1:
            end = prompt.find('\n', start)
        if end != -1:
            task_name = prompt[start:end].strip('"\'')

    # Generate memory instructions
    memory_instructions = f"""
## 🧠 Memory System Integration

**Current Session:** {task_context['session_id']}
**Storage Path:** {task_context['storage_path']}
**Active Tasks:** {', '.join(task_context['active_tasks']) if task_context['active_tasks'] else 'None'}

### Memory Commands Available:
```bash
# Discovery phase - mutable exploration
claude-memory scratchpad "{task_name}" --content "your exploration notes"

# Planning phase - write-once plan creation
claude-memory plan "{task_name}" --content "implementation plan"

# Execution phase - append-only progress tracking
claude-memory append "{task_name}" "progress update details"

# Check current status
claude-memory status "{task_name}"
```

### Three-Phase Workflow:
1. **DISCOVERY** (Scratchpad): Mutable exploration and research
2. **PLANNING** (Plan): Write-once implementation strategy
3. **EXECUTION** (Progress): Append-only progress tracking

**IMPORTANT:** Use the claude-memory CLI commands above for all memory operations.
This ensures proper coordination between main agent and sub-agents.

---

"""

    # Inject instructions at the beginning of the prompt
    original_prompt = input_data.get('tool_input', {}).get('prompt', '')
    modified_prompt = memory_instructions + original_prompt

    # Create modified input
    modified_input = input_data.copy()
    if 'tool_input' not in modified_input:
        modified_input['tool_input'] = {}

    modified_input['tool_input'] = modified_input['tool_input'].copy()
    modified_input['tool_input']['prompt'] = modified_prompt

    return modified_input


def main():
    """Main hook function."""
    try:
        # Read input from Claude
        input_data = json.loads(sys.stdin.read())

        tool_name = input_data.get('tool_name')

        # Only process Task tool calls
        if tool_name == 'Task':
            # Get memory context
            try:
                api = MemoryAPI()
                task_context = api.get_context_for_subagent()

                # Inject memory instructions
                modified_input = inject_memory_instructions(input_data, task_context)

                # Return modified input
                response = {
                    "decision": "allow",
                    "modifiedInput": modified_input
                }

            except Exception as e:
                # If memory system fails, log but don't block
                response = {
                    "decision": "allow",
                    "reason": f"Memory system unavailable: {e}"
                }
        else:
            # For non-Task tools, just allow
            response = {
                "decision": "allow"
            }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # If anything goes wrong, allow the operation but log the error
        response = {
            "decision": "allow",
            "reason": f"Hook error: {e}"
        }
        print(json.dumps(response))
        sys.exit(0)


if __name__ == "__main__":
    main()