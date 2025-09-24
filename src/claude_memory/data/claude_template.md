# CLAUDE.md - Project Instructions

## 🧠 Claude Memory System

### Three-Phase Workflow System
The Claude Memory System uses a structured three-phase approach for all tasks:

#### Phase 1: Discovery (Scratchpad - MUTABLE)
```bash
claude-memory scratchpad "task-name" --content "exploration, research, questions"
```
- Use for exploration, research, thinking, and questions
- Content is mutable during discovery phase
- Capture uncertainties, failed attempts, and learning

#### Phase 2: Planning (Plan - WRITE-ONCE)
```bash
claude-memory plan "task-name" --content "implementation strategy based on discoveries"
```
- Create formal plan from scratchpad insights
- Write-once, then immutable
- Transform messy findings into clear strategy

#### Phase 3: Execution (Progress - APPEND-ONLY)
```bash
claude-memory append "task-name" "progress update with specific details"
```
- Track implementation progress and results
- Append-only during execution
- Document reality vs plan deviations

### Sub-Agent Coordination
**CRITICAL:** All sub-agents must use the same claude-memory CLI commands.

```bash
# Sub-agents automatically receive memory context via hooks
# Use these commands in all sub-agents:

# Discovery phase
claude-memory scratchpad "existing-task" --content "sub-agent exploration findings"

# Planning phase (when creating plans)
claude-memory plan "existing-task" --content "sub-agent implementation strategy"

# Execution phase
claude-memory append "existing-task" "Sub-agent progress: specific work completed"

# Check status and context
claude-memory status "existing-task"
claude-memory context
```

### Key Memory Commands
```bash
claude-memory status                    # Show all tasks
claude-memory session info             # Session details
claude-memory project-context refresh  # Update project context
```

### Three-File System
Each task creates three coordinated files:
- **Scratchpad**: `taskname-sessionid-scratchpad.md` (MUTABLE)
- **Plan**: `taskname-sessionid-plan.md` (WRITE-ONCE)
- **Progress**: `taskname-sessionid-progress.md` (APPEND-ONLY)

**Phase Transitions:**
- Discovery → Planning: Convert scratchpad insights into concrete plan
- Planning → Execution: Lock plan, begin progress tracking
- Each phase must complete before moving to next

### Usage Guidelines
1. **Always start with scratchpad** for exploration and research
2. **Create plan only after thorough discovery**
3. **Use append for all execution updates**
4. **Sub-agents coordinate through same session**
5. **Memory context automatically injected into sub-agent prompts**