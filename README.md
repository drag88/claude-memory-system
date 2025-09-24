# Claude Memory System 🧠

[![PyPI version](https://badge.fury.io/py/claude-memory-system.svg)](https://badge.fury.io/py/claude-memory-system)
[![Python Support](https://img.shields.io/pypi/pyversions/claude-memory-system.svg)](https://pypi.org/project/claude-memory-system/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A portable, file-based memory system for Claude Code that implements a three-phase workflow pattern with sub-agent coordination. Transform messy exploration into structured implementation plans with persistent memory across sessions.

## ✨ Key Features

- **🧠 Three-Phase Workflow**: Scratchpad → Plan → Progress methodology
- **🔒 File Immutability**: Write-once plans, append-only progress tracking
- **🌐 Cross-Platform**: Works seamlessly on Windows, macOS, and Linux
- **📦 Portable**: Single global installation works across all your projects
- **🤖 Sub-Agent Ready**: Automatic integration with Claude Code Task tool
- **🔧 Hook Integration**: Seamless Claude Code integration via custom hooks
- **⚡ Session Management**: Multiple concurrent sessions with coordination
- **🎯 Project Context**: Automatic project detection and context injection

## 🚀 Quick Installation

### Option 1: Install from GitHub (Recommended)

```bash
# Using uv (fastest)
uv add git+https://github.com/drag88/claude-memory-system.git

# Using pip
pip install git+https://github.com/drag88/claude-memory-system.git
```

### Option 2: Development Installation

```bash
git clone https://github.com/drag88/claude-memory-system.git
cd claude-memory-system
uv pip install -e .
# or
pip install -e .
```

### Option 3: From PyPI (Coming Soon)

```bash
uv add claude-memory-system
# or
pip install claude-memory-system
```

## 🏁 Quick Start

```bash
# Initialize memory system for your project
claude-memory init

# Start exploration phase
claude-memory scratchpad "implement-auth" --content "Need to add user authentication system..."

# Create implementation plan
claude-memory plan "implement-auth" --content "## Implementation Plan
1. Create User model with email/password
2. Add JWT token generation
3. Create login/logout endpoints
4. Add middleware for protected routes"

# Track your progress
claude-memory append "implement-auth" "✅ Completed User model with password hashing"
claude-memory append "implement-auth" "✅ Added JWT token generation and validation"

# Check status anytime
claude-memory status "implement-auth"
```

## 📋 Three-Phase Workflow System

The memory system enforces a proven three-phase development workflow:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   DISCOVERY     │───▶│    PLANNING     │───▶│   EXECUTION     │
│                 │    │                 │    │                 │
│ • Exploration   │    │ • Concrete Plan │    │ • Progress Log  │
│ • Questions     │    │ • Write-Once    │    │ • Append-Only   │
│ • Dead Ends     │    │ • Immutable     │    │ • Real Results  │
│ • Learning      │    │ • Strategy      │    │ • Course Cor.   │
│                 │    │                 │    │                 │
│ (Scratchpad)    │    │    (Plan)       │    │   (Progress)    │
│   MUTABLE       │    │  IMMUTABLE      │    │ APPEND-ONLY     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Phase 1: Discovery (Scratchpad) 🔍

**Purpose**: Messy exploration, questions, research, and learning
**Behavior**: Mutable and overwritable - change it as much as you need

```bash
# Start exploring
claude-memory scratchpad "my-task" --content "Looking into authentication options..."

# Update as you learn
claude-memory scratchpad "my-task" --content "Found three options:
1. JWT tokens - simple but stateless
2. Sessions - server state required
3. OAuth - complex setup

Questions: Do we need social login? What about refresh tokens?"

# Open in your editor for longer exploration
claude-memory scratchpad "my-task" --edit
```

### Phase 2: Planning (Plan) 📝

**Purpose**: Transform discoveries into concrete implementation strategy
**Behavior**: Write-once, then immutable - think before you write

```bash
# Create your implementation plan (locks after creation)
claude-memory plan "my-task" --content "## Authentication Implementation

### Approach
Based on scratchpad research, using JWT tokens for simplicity.

### Implementation Steps
1. Install PyJWT and bcrypt dependencies
2. Create User model with password hashing
3. Add /login endpoint that returns JWT
4. Add JWT validation middleware
5. Protect existing API endpoints
6. Add logout functionality (token blacklist)

### Testing Strategy
- Unit tests for password hashing
- Integration tests for login flow
- End-to-end test for protected routes"
```

### Phase 3: Execution (Progress) ⚡

**Purpose**: Track implementation progress and real results
**Behavior**: Append-only - build a chronological record

```bash
# Log your progress as you work
claude-memory append "my-task" "Started implementation:
✅ Added PyJWT and bcrypt to requirements
✅ Created User model with password_hash field
🔄 Working on login endpoint..."

# Continue logging results
claude-memory append "my-task" "Login endpoint complete:
✅ POST /login validates credentials
✅ Returns JWT token on success
✅ Proper error handling for invalid login
⚠️  Need to add rate limiting"

# Document deviations from plan
claude-memory append "my-task" "Plan deviation:
❌ JWT blacklist too complex for MVP
✅ Using shorter token expiry (1 hour) instead
✅ Will add refresh tokens in phase 2"
```

## 🤖 Sub-Agent Integration

The memory system automatically integrates with Claude Code's Task tool through hooks:

### Automatic Context Injection

When Claude uses the Task tool, memory context is automatically injected into sub-agent prompts:

```markdown
## 🧠 Memory System Integration
**Current Session:** abc123-def456
**Storage Path:** /Users/you/project/.claude-memories
**Active Tasks:** implement-auth, add-testing, fix-performance

### 📝 Task Status:
- **implement-auth**: Plan phase (locked) → Progress tracking active
- **add-testing**: Discovery phase → Scratchpad being updated
- **fix-performance**: Planning phase → Ready to lock plan

### 💡 Memory Commands Available:
```bash
# Continue exploration
claude-memory scratchpad "task-name" --content "new findings..."

# Create implementation plan
claude-memory plan "task-name" --content "concrete strategy..."

# Track implementation progress
claude-memory append "task-name" "progress update..."

# Check current status
claude-memory status "task-name"
```

### Sub-Agent Workflow

```python
# Sub-agents automatically get memory context and can:
# 1. Continue discovery in existing scratchpads
# 2. Create plans when ready to move from discovery
# 3. Log progress during implementation
# 4. Coordinate across multiple tasks

# Example sub-agent usage:
api = MemoryAPI()
api.append_progress("implement-auth", "Sub-agent completed: JWT validation middleware")
```

## 🛠️ CLI Reference

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize memory system | `claude-memory init` |
| `scratchpad` | Create/update exploration notes | `claude-memory scratchpad "task" --content "notes"` |
| `plan` | Create implementation plan (write-once) | `claude-memory plan "task" --content "strategy"` |
| `append` | Add progress update | `claude-memory append "task" "completed X"` |
| `status` | Show task status | `claude-memory status "task"` |

### Session Management

| Command | Description | Example |
|---------|-------------|---------|
| `session start` | Start new session | `claude-memory session start --name "feature-work"` |
| `session info` | Show current session | `claude-memory session info` |
| `session list` | List all sessions | `claude-memory session list` |
| `session switch` | Switch to session | `claude-memory session switch abc123` |

### Project Context

| Command | Description | Example |
|---------|-------------|---------|
| `project-info` | Show project details | `claude-memory project-info` |
| `project-context` | Show/refresh context | `claude-memory project-context --refresh` |
| `context` | Sub-agent context info | `claude-memory context` |

### Utility Commands

| Command | Description | Example |
|---------|-------------|---------|
| `cleanup` | Clean old sessions/locks | `claude-memory cleanup --days 30` |
| `export` | Export task data | `claude-memory export "task" --format json` |
| `version` | Show version info | `claude-memory version` |

## 🐍 Python API

Use the memory system programmatically in your Python projects:

### Basic Usage

```python
from claude_memory import MemoryAPI

# Initialize API
api = MemoryAPI()

# Three-phase workflow
# 1. Discovery phase
api.create_scratchpad("implement-cache", """
Initial research on caching options:
- Redis: Fast, but another service to manage
- In-memory: Simple, but data lost on restart
- File-based: Persistent, but slower I/O
- Database: Already have it, but might be overkill

Questions: What's the expected cache hit rate? Size limits?
""")

# Update scratchpad as you explore
api.update_scratchpad("implement-cache", """
After testing, in-memory + Redis hybrid seems best:
- Use in-memory for hot data (LRU cache)
- Redis for persistence and sharing across instances
- File-based as backup for critical data

Found library 'cachetools' for in-memory part.
""")

# 2. Planning phase (locks the plan)
api.create_plan("implement-cache", """
## Caching Implementation Plan

### Architecture
- L1: In-memory LRU cache (cachetools) - 1000 items
- L2: Redis cache - 1 hour TTL
- L3: Database fallback

### Implementation Steps
1. Add cachetools and redis dependencies
2. Create CacheManager class with get/set/delete
3. Implement cache-aside pattern in service layer
4. Add cache warming on application start
5. Add metrics for cache hit/miss rates
6. Add admin endpoint for cache clearing

### Success Metrics
- 80%+ cache hit rate for user data
- <10ms average response time for cached items
- Memory usage stays under 100MB
""")

# 3. Execution phase
api.append_progress("implement-cache", "Started implementation:")
api.append_progress("implement-cache", """
✅ Added dependencies: cachetools==5.3.2, redis==5.0.1
✅ Created CacheManager class with L1/L2 support
✅ Implemented get/set/delete with fallthrough logic
🔄 Working on cache warming strategy...
""")

api.append_progress("implement-cache", """
Cache warming complete:
✅ Added startup task to pre-load user profiles
✅ Background job refreshes popular items every 30min
📊 Initial results: 75% hit rate, 8ms avg response time
⚠️  Memory usage at 120MB - need to tune LRU size
""")

# Check status
status = api.get_task_status("implement-cache")
print(f"Task: {status.task_name}")
print(f"Phase: {status.current_phase}")
print(f"Files: {len(status.files)} files")
```

### Advanced API Usage

```python
from claude_memory import MemoryAPI, SessionManager
from claude_memory.core import WorkflowEnforcer

# Session management
session_mgr = SessionManager()
current_session = session_mgr.get_current_session()
print(f"Working in session: {current_session.session_id}")

# Switch to different session
session_mgr.switch_to_session("other-session-id")

# Workflow enforcement
api = MemoryAPI()
enforcer = WorkflowEnforcer(api.memory_manager)

# Check what phase a task is in
phase = enforcer.get_current_phase("my-task")
if phase == "discovery":
    print("Still exploring - scratchpad is mutable")
elif phase == "planning":
    print("Plan created - now immutable")
elif phase == "execution":
    print("Tracking progress - append-only")

# Get all tasks in current session
tasks = api.list_tasks()
for task in tasks:
    print(f"{task.name}: {task.current_phase} ({task.file_count} files)")

# Export task data
task_data = api.export_task("my-task", format="json")
print(json.dumps(task_data, indent=2))
```

### Integration Patterns

```python
# Integration with existing projects
class MyService:
    def __init__(self):
        self.memory = MemoryAPI()

    def start_feature(self, feature_name: str):
        """Start working on a new feature"""
        self.memory.create_scratchpad(feature_name,
            f"Starting work on {feature_name}...")
        return f"Memory initialized for {feature_name}"

    def log_progress(self, feature_name: str, progress: str):
        """Log progress on a feature"""
        self.memory.append_progress(feature_name, progress)

    def complete_feature(self, feature_name: str):
        """Mark feature as complete"""
        self.memory.append_progress(feature_name,
            "🎉 Feature implementation complete!")

# Usage in your application
service = MyService()
service.start_feature("user-notifications")
service.log_progress("user-notifications", "Added email templates")
service.log_progress("user-notifications", "Implemented notification queue")
service.complete_feature("user-notifications")
```

## ⚙️ Configuration

### File Structure

The memory system creates this structure in your project:

```
your-project/
├── .claude-memories/           # Memory storage directory
│   ├── sessions/              # Session data
│   │   └── abc123-def456/     # Session ID
│   │       ├── tasks/         # Task files by name
│   │       │   ├── implement-auth-abc123-scratchpad.md
│   │       │   ├── implement-auth-abc123-plan.md
│   │       │   └── implement-auth-abc123-progress.md
│   │       └── session.json   # Session metadata
│   ├── project-context.json   # Project detection cache
│   └── config.json           # Local configuration
└── your code files...
```

### Claude Code Integration

The memory system automatically installs hooks for Claude Code integration:

```bash
# Hook files (automatically installed)
~/.claude/hooks/
├── pre_tool_use.py           # Injects context before sub-agents
├── post_tool_use.py          # Updates memory after tool use
├── session_start.py          # Initializes session
└── subagent_stop.py          # Coordinates sub-agent completion
```

### Customization

```python
# Customize storage location
from claude_memory import MemoryAPI

api = MemoryAPI(storage_path="/custom/path/.memories")

# Customize file naming
api.memory_manager.set_file_pattern("{task}-{timestamp}-{phase}.md")

# Add custom project context
api.context_manager.add_custom_context({
    "framework": "FastAPI",
    "database": "PostgreSQL",
    "deployment": "Docker + AWS"
})
```

## 🔧 Troubleshooting

### Common Issues

**Q: `claude-memory` command not found**
```bash
# Ensure the package is installed
which claude-memory

# If using uv, make sure it's in your PATH
uv tool list
export PATH="$HOME/.local/bin:$PATH"

# Reinstall if needed
uv add --force git+https://github.com/drag88/claude-memory-system.git
```

**Q: Permission errors with memory files**
```bash
# Check file permissions
ls -la .claude-memories/

# Fix permissions if needed
chmod -R 755 .claude-memories/
```

**Q: Session conflicts between multiple Claude instances**
```bash
# Check active sessions
claude-memory session list

# Switch to a specific session
claude-memory session switch abc123-def456

# Start a new session if needed
claude-memory session start --name "my-work"
```

**Q: Memory files getting too large**
```bash
# Clean up old sessions
claude-memory cleanup --days 30

# Export important data before cleanup
claude-memory export "important-task" --format json > backup.json
```

**Q: Claude Code hooks not working**
```bash
# Check hook installation
ls -la ~/.claude/hooks/

# Reinstall hooks
python scripts/setup_hooks.py

# Check Claude Code settings
cat ~/.claude/claude_desktop_config.json
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Set debug environment variable
export CLAUDE_MEMORY_DEBUG=1
claude-memory status

# Or use debug flag
claude-memory --debug status "my-task"
```

## 🏗️ Architecture

### Core Components

```
┌─────────────────────┐
│    Memory API       │ ← High-level Python interface
├─────────────────────┤
│   CLI Interface     │ ← Command-line tool (typer)
├─────────────────────┤
│  Memory Manager     │ ← Core orchestration
├─────────────────────┤
│ Workflow Enforcer   │ ← Phase transition rules
├─────────────────────┤
│ Session Manager     │ ← Session lifecycle
├─────────────────────┤
│ Context Manager     │ ← Project context detection
├─────────────────────┤
│   File Lock         │ ← Concurrent access control
└─────────────────────┘
```

### Data Flow

```
User/Claude → CLI/API → MemoryManager → WorkflowEnforcer
                                     ↓
                              SessionManager → FileSystem
                                     ↓
                              ContextManager → ProjectContext
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/drag88/claude-memory-system.git
cd claude-memory-system

# Install in development mode
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Format code
uv run black src/
uv run ruff check src/

# Type check
uv run mypy src/
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=claude_memory

# Run specific test file
uv run pytest tests/test_memory_manager.py

# Run integration tests
uv run pytest tests/integration/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the [Claude Code](https://claude.ai/code) ecosystem
- Inspired by proven software development workflows
- Uses modern Python packaging with [uv](https://github.com/astral-sh/uv)

---

**Made with ❤️ for developers who want structured thinking in their AI-assisted development workflow.**

For issues, feature requests, or questions, please visit our [GitHub Issues](https://github.com/drag88/claude-memory-system/issues) page.