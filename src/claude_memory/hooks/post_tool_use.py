#!/usr/bin/env python3
"""
Post-tool-use hook for Claude Code integration.

Logs memory operations and tracks tool usage.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

try:
    from claude_memory import MemoryAPI
except ImportError:
    # If package not installed, try to import from parent directory
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from claude_memory import MemoryAPI


def log_tool_usage(input_data: dict, output_data: dict) -> None:
    """
    Log tool usage for memory tracking.

    Args:
        input_data: Tool input data
        output_data: Tool output data
    """
    tool_name = input_data.get('tool_name')
    timestamp = datetime.now().isoformat()

    # Create log entry
    log_entry = {
        "timestamp": timestamp,
        "tool_name": tool_name,
        "success": output_data.get('success', True),
        "session": None
    }

    try:
        api = MemoryAPI()
        context = api.get_context_for_subagent()
        log_entry["session"] = context.get("session_id")

        # If this was a Task tool (sub-agent), log it specially
        if tool_name == 'Task':
            prompt = input_data.get('tool_input', {}).get('prompt', '')
            subagent_type = input_data.get('tool_input', {}).get('subagent_type', 'unknown')

            log_entry.update({
                "subagent_type": subagent_type,
                "prompt_length": len(prompt),
                "memory_injected": "Memory System Integration" in prompt
            })

        # Log to a special memory tracking task if configured
        if context.get("session_id"):
            try:
                # Log tool usage as progress in a special tracking task
                api.append(
                    "_tool_usage_log",
                    f"Tool: {tool_name} | Success: {log_entry['success']} | Time: {timestamp}"
                )
            except:
                # Don't fail if logging fails
                pass

    except Exception:
        # Don't fail the hook if logging fails
        pass


def main():
    """Main hook function."""
    try:
        # Read input from Claude
        input_data = json.loads(sys.stdin.read())

        # For post-tool-use, we also get the tool output
        # This would be available in the actual hook context
        output_data = input_data.get('tool_output', {})

        # Log the tool usage
        log_tool_usage(input_data, output_data)

        # Post-tool-use hooks typically don't modify anything
        # They just observe and log
        response = {
            "continue": True
        }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # If anything goes wrong, don't block
        response = {
            "continue": True,
            "error": str(e)
        }
        print(json.dumps(response))
        sys.exit(0)


if __name__ == "__main__":
    main()