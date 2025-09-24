#!/usr/bin/env python3
"""
Hook setup automation for Claude Code integration.

Updates .claude/settings.json with memory system hooks.
"""

import json
import sys
from pathlib import Path


def update_claude_settings():
    """Update Claude Code settings with memory system hooks."""
    settings_file = Path(".claude/settings.json")

    if not settings_file.exists():
        print("❌ .claude/settings.json not found")
        return False

    try:
        # Read existing settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        # Ensure hooks section exists
        if "hooks" not in settings:
            settings["hooks"] = {}

        # Define hook configurations
        hook_configs = {
            "PreToolUse": [
                {
                    "matcher": "Task",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 .claude/hooks/pre_tool_use.py"
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": ".*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 .claude/hooks/post_tool_use.py"
                        }
                    ]
                }
            ],
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 .claude/hooks/session_start.py"
                        }
                    ]
                }
            ],
            "SubagentStop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 .claude/hooks/subagent_stop.py"
                        }
                    ]
                }
            ]
        }

        # Update hooks, preserving existing non-memory hooks
        for hook_type, hook_config in hook_configs.items():
            if hook_type not in settings["hooks"]:
                settings["hooks"][hook_type] = []

            # Remove existing memory system hooks
            existing_hooks = settings["hooks"][hook_type]
            filtered_hooks = []

            for hook_entry in existing_hooks:
                # Skip if it's a memory system hook
                if isinstance(hook_entry, dict) and "hooks" in hook_entry:
                    hooks_list = hook_entry["hooks"]
                    if isinstance(hooks_list, list):
                        memory_hook = any(
                            isinstance(h, dict) and
                            h.get("command", "").endswith(("pre_tool_use.py", "post_tool_use.py", "session_start.py", "subagent_stop.py"))
                            for h in hooks_list
                        )
                        if not memory_hook:
                            filtered_hooks.append(hook_entry)
                    else:
                        filtered_hooks.append(hook_entry)
                else:
                    filtered_hooks.append(hook_entry)

            # Add new memory system hooks
            settings["hooks"][hook_type] = filtered_hooks + hook_config

        # Create backup
        backup_file = settings_file.with_suffix('.json.backup')
        with open(backup_file, 'w') as f:
            json.dump(settings, f, indent=2)

        # Write updated settings
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        print("✅ Updated .claude/settings.json with memory system hooks")
        print(f"📁 Backup saved as {backup_file}")
        return True

    except Exception as e:
        print(f"❌ Failed to update settings: {e}")
        return False


def verify_hook_files():
    """Verify that hook files exist and are executable."""
    hooks_dir = Path(".claude/hooks")
    hook_files = [
        "pre_tool_use.py",
        "post_tool_use.py",
        "session_start.py",
        "subagent_stop.py"
    ]

    missing_files = []
    for hook_file in hook_files:
        hook_path = hooks_dir / hook_file
        if not hook_path.exists():
            missing_files.append(hook_file)
        elif not hook_path.is_file():
            print(f"⚠️  {hook_file} exists but is not a file")
        elif not (hook_path.stat().st_mode & 0o111):
            # Make executable if not already
            hook_path.chmod(hook_path.stat().st_mode | 0o755)
            print(f"✅ Made {hook_file} executable")

    if missing_files:
        print(f"❌ Missing hook files: {', '.join(missing_files)}")
        print("Run the install script to copy hook files.")
        return False

    print("✅ All hook files are present and executable")
    return True


def verify_agent_files():
    """Verify that agent files are properly installed."""
    agents_dir = Path(".claude/agents")

    if not agents_dir.exists():
        print("⚠️  .claude/agents directory not found")
        return False

    # Count agent files
    agent_files = list(agents_dir.glob("*.md"))

    if not agent_files:
        print("⚠️  No agent files found in .claude/agents/")
        return False

    print(f"✅ Found {len(agent_files)} specialized agents:")
    for agent_file in sorted(agent_files):
        agent_name = agent_file.stem.replace("-", " ").title()
        print(f"   • {agent_name}")

    return True


def main():
    """Main setup function."""
    print("🔧 Setting up Claude Memory System hooks and agents...")

    # Verify we're in a Claude Code project
    if not Path(".claude").exists():
        print("❌ Not in a Claude Code project (.claude directory not found)")
        sys.exit(1)

    # Verify hook files
    if not verify_hook_files():
        sys.exit(1)

    # Verify agent files (non-fatal if missing)
    agents_available = verify_agent_files()

    # Update settings
    if not update_claude_settings():
        sys.exit(1)

    print("\n🎉 Hook setup complete!")
    print("\nThe memory system will now:")
    print("  • Inject memory context into sub-agent (Task) calls")
    print("  • Log tool usage for tracking")
    print("  • Initialize memory on session start")
    print("  • Sync memory when sub-agents complete")

    if agents_available:
        print("\n🤖 Specialized agents are available:")
        print("  • Use Task tool with agent names (e.g., 'backend-architect')")
        print("  • Agents have memory system integration built-in")
        print("  • Each agent follows specific domain expertise patterns")

    print("\nRestart Claude Code to activate the hooks.")


if __name__ == "__main__":
    main()