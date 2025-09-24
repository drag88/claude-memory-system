#!/bin/bash
# Installation script for Claude Memory System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is required but not installed."
        echo "Install uv from: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    print_status "Found uv: $(uv --version)"
}

# Install the package globally
install_package() {
    print_step "Installing Claude Memory System globally with uv..."

    # Check if we're in the package directory
    if [ ! -f "pyproject.toml" ]; then
        print_error "pyproject.toml not found. Run this script from the claude-memory-system directory."
        exit 1
    fi

    # Install as a tool
    uv tool install . --force
    print_status "Package installed successfully"
}

# Verify installation
verify_installation() {
    print_step "Verifying installation..."

    if command -v claude-memory &> /dev/null; then
        print_status "claude-memory CLI is available"
        claude-memory version
    else
        print_error "claude-memory command not found in PATH"
        print_warning "You may need to add ~/.local/bin to your PATH"
        exit 1
    fi
}

# Setup project hooks (optional)
setup_project_hooks() {
    print_step "Setting up hooks for current project (optional)..."

    # Check if we're in a Claude Code project
    if [ ! -d ".claude" ]; then
        print_warning "No .claude directory found. Creating minimal structure..."
        mkdir -p .claude/hooks
    fi

    HOOKS_DIR=".claude/hooks"
    PACKAGE_HOOKS_DIR="src/claude_memory/hooks"

    # Copy hook scripts
    for hook in pre_tool_use.py post_tool_use.py session_start.py subagent_stop.py; do
        if [ -f "$PACKAGE_HOOKS_DIR/$hook" ]; then
            cp "$PACKAGE_HOOKS_DIR/$hook" "$HOOKS_DIR/"
            chmod +x "$HOOKS_DIR/$hook"
            print_status "Copied $hook to $HOOKS_DIR/"
        fi
    done

    # Update .claude/settings.json if it exists
    if [ -f ".claude/settings.json" ]; then
        print_step "Updating .claude/settings.json with hook configuration..."
        python3 scripts/setup_hooks.py
    else
        print_warning ".claude/settings.json not found. You'll need to configure hooks manually."
        print_status "Example hook configuration:"
        cat << 'EOF'
{
  "hooks": {
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
}
EOF
    fi
}

# Initialize memory system for current project
initialize_memory() {
    print_step "Initializing memory system for current project..."
    claude-memory init
    print_status "Memory system initialized"
}

# Show usage information
show_usage() {
    print_status "Installation complete! 🎉"
    echo
    echo "Available commands:"
    echo "  claude-memory init                    # Initialize for project"
    echo "  claude-memory scratchpad 'task-name' # Start exploration"
    echo "  claude-memory plan 'task-name'       # Create plan"
    echo "  claude-memory append 'task-name' ... # Track progress"
    echo "  claude-memory status                 # Show all tasks"
    echo "  claude-memory session info           # Session details"
    echo
    echo "Documentation: claude-memory --help"
    echo
    print_status "The memory system is now ready for use across all your projects!"
}

# Main installation process
main() {
    echo "🧠 Claude Memory System Installer"
    echo "=================================="
    echo

    check_uv
    install_package
    verify_installation

    # Ask if user wants to setup hooks for current project
    if [ -t 0 ]; then  # Check if running interactively
        echo
        read -p "Setup hooks for current project? (y/N): " setup_hooks
        if [[ $setup_hooks =~ ^[Yy]$ ]]; then
            setup_project_hooks
            initialize_memory
        fi
    else
        print_warning "Non-interactive mode: skipping project setup"
    fi

    show_usage
}

# Run main function
main "$@"