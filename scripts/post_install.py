#!/usr/bin/env python3
"""
Post-install hook for Claude Memory System.

Automatically sets up hooks, agents, and memory system when package is installed.
This runs after 'uv add git+...' to provide a seamless installation experience.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    try:
        print(f"🔧 {description}...")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True
        else:
            print(f"⚠️  {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False


def check_if_in_project():
    """Check if we're in a project directory (has common project files)."""
    cwd = Path.cwd()

    # Look for common project indicators
    project_indicators = [
        "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
        "pom.xml", "build.gradle", ".git", "requirements.txt",
        "composer.json", "Gemfile", "mix.exs"
    ]

    for indicator in project_indicators:
        if (cwd / indicator).exists():
            return True

    # Also check if there are source directories
    source_dirs = ["src", "lib", "app", "components", "pages"]
    for src_dir in source_dirs:
        if (cwd / src_dir).exists() and (cwd / src_dir).is_dir():
            return True

    return False


def install_hooks_and_agents():
    """Install hooks and agents to current project."""
    cwd = Path.cwd()

    # Create .claude directories
    claude_dir = cwd / ".claude"
    hooks_dir = claude_dir / "hooks"
    agents_dir = claude_dir / "agents"

    claude_dir.mkdir(exist_ok=True)
    hooks_dir.mkdir(exist_ok=True)
    agents_dir.mkdir(exist_ok=True)

    # Find package installation location
    try:
        result = subprocess.run([sys.executable, "-c",
            "import claude_memory; print(claude_memory.__file__)"],
            capture_output=True, text=True)
        if result.returncode == 0:
            package_init = Path(result.stdout.strip())
            package_root = package_init.parent.parent.parent  # Go up to find package root

            # Look for hooks and agents directories
            hooks_source = None
            agents_source = None

            # Try different possible locations
            possible_locations = [
                package_root,
                package_root / "claude-memory-system",
                Path(__file__).parent.parent,  # Relative to this script
            ]

            for location in possible_locations:
                if (location / "src" / "claude_memory" / "hooks").exists():
                    hooks_source = location / "src" / "claude_memory" / "hooks"
                if (location / "agents").exists():
                    agents_source = location / "agents"
                if hooks_source and agents_source:
                    break

            # Copy hooks
            if hooks_source and hooks_source.exists():
                for hook_file in hooks_source.glob("*.py"):
                    dest_file = hooks_dir / hook_file.name
                    shutil.copy2(hook_file, dest_file)
                    dest_file.chmod(0o755)  # Make executable
                print(f"✅ Installed hooks to {hooks_dir}")
            else:
                print("⚠️  Hook source directory not found")

            # Copy agents
            if agents_source and agents_source.exists():
                for agent_file in agents_source.glob("*.md"):
                    if not agent_file.name.startswith('.'):  # Skip .DS_Store etc
                        dest_file = agents_dir / agent_file.name
                        shutil.copy2(agent_file, dest_file)
                agent_count = len(list(agents_dir.glob("*.md")))
                print(f"✅ Installed {agent_count} agents to {agents_dir}")
            else:
                print("⚠️  Agents source directory not found")

    except Exception as e:
        print(f"❌ Failed to install hooks and agents: {e}")
        return False

    return True


def update_claude_settings():
    """Update Claude Code settings.json with hook configuration."""
    settings_file = Path(".claude/settings.json")

    try:
        import json

        # Read existing settings or create new
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}

        # Ensure hooks section exists
        if "hooks" not in settings:
            settings["hooks"] = {}

        # Add memory system hooks
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

        # Update settings
        for hook_type, hook_config in hook_configs.items():
            settings["hooks"][hook_type] = hook_config

        # Write updated settings
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        print(f"✅ Updated Claude Code settings at {settings_file}")
        return True

    except Exception as e:
        print(f"❌ Failed to update Claude settings: {e}")
        return False


def main():
    """Main post-install setup."""
    print("🧠 Claude Memory System - Post-Install Setup")
    print("=" * 50)

    # Check if we're in a project directory
    if not check_if_in_project():
        print("ℹ️  Not in a project directory - skipping automatic setup")
        print("💡 Run 'claude-memory init' in your project directory to set up manually")
        return

    print(f"📁 Setting up in: {Path.cwd()}")

    # Install hooks and agents
    if install_hooks_and_agents():
        print("✅ Hooks and agents installed successfully")
    else:
        print("⚠️  Some issues with hooks/agents installation")

    # Update Claude settings
    update_claude_settings()

    # Initialize memory system
    if run_command([sys.executable, "-m", "claude_memory.cli", "init"],
                   "Initializing memory system"):
        print("✅ Memory system initialized")

    # Generate project context
    if run_command([sys.executable, "-m", "claude_memory.cli", "project-context", "--refresh"],
                   "Generating project context"):
        print("✅ Project context generated")

    print("\n🎉 Claude Memory System setup complete!")
    print("🚀 Available commands:")
    print("   • claude-memory status           # Show task status")
    print("   • claude-memory scratchpad       # Start exploration")
    print("   • claude-memory plan            # Create implementation plan")
    print("   • claude-memory append          # Track progress")
    print("   • claude-memory session info    # Session details")
    print("   • claude-memory uninstall       # Remove system")

    print(f"\n🤖 {len(list(Path('.claude/agents').glob('*.md')))} specialized agents available in .claude/agents/")
    print("🔗 Memory system hooks active - restart Claude Code to enable")


if __name__ == "__main__":
    main()