# CLAUDE.md - Development Instructions

## 🧠 THREE-FILE WORKFLOW SYSTEM

### 1. MEMORY MANAGEMENT - THREE PHASES, THREE FILES
```bash
# Phase 1: Discovery (Scratchpad - MUTABLE)
claude-memory scratchpad "your-task" --content "exploration, research, thinking, questions"
# Use for: exploration, research, thinking, questions

# Phase 2: Planning (Plan - WRITE-ONCE)
claude-memory plan "your-task" --content "formal plan from scratchpad insights"
# Create formal plan from scratchpad insights, then lock

# Phase 3: Execution (Progress - APPEND-ONLY)
claude-memory append "your-task" "progress update"
# Track implementation progress and results
```

**Three-File System:**
- **Scratchpad**: `taskname-sessionid-scratchpad.md` (MUTABLE during discovery)
- **Plan**: `taskname-sessionid-plan.md` (WRITE-ONCE, then immutable)
- **Progress**: `taskname-sessionid-progress.md` (APPEND-ONLY during execution)

**Phase Transitions:**
- Discovery → Planning: Convert scratchpad insights into concrete plan
- Planning → Execution: Lock plan, begin progress tracking
- Each phase must complete before next begins

### 2. SUB-AGENT DELEGATION - MEMORY COORDINATION
```bash
# Sub-agents automatically receive memory context via hooks
# Use the claude-memory CLI for all memory operations:

# Phase 1: Discovery in sub-agent
claude-memory scratchpad "task-name" --content "sub-agent exploration findings"

# Phase 2: Planning in sub-agent (if creating plan)
claude-memory plan "task-name" --content "implementation strategy"

# Phase 3: Progress tracking in sub-agent
claude-memory append "task-name" "Sub-agent completed: specific work done"

# Check current status and context
claude-memory status "task-name"
claude-memory context  # Shows session info for sub-agents
```

**Key Points:**
- Memory context automatically injected into sub-agent prompts
- All agents use same claude-memory CLI commands
- Session coordination across main and sub-agents
- Persistent memory across Task tool delegations

### 3. DEVELOPMENT STANDARDS
- **Search before creating**: Use `rg "pattern"` to find existing code
- **DRY principle**: Reuse existing functions/classes, don't duplicate
- **Use `uv`**: For all Python commands (`uv run python`, `uv add package`)
- **Type hints**: Required for all functions
- **File limits**: <500 lines per file, <50 lines per function

---

## 📋 AUTHENTIC THREE-PHASE WORKFLOW

### ✅ AUTHENTIC USAGE PATTERNS

#### Phase 1: Discovery (Scratchpad) - Real Exploration
```bash
claude-memory scratchpad "fix-auth-bug" --content "Initial investigation..."

# AUTHENTIC Scratchpad - messy, iterative discovery:
Users complaining about auth failures... not sure what's happening

Let me check auth.py... hmm, this validation logic on line 45 looks weird
Tried testing login flow manually - works initially but fails after exactly 1 hour
Is this a token expiry issue? Let me investigate...

Checking middleware.py... found token validation but no refresh mechanism?
Why was this designed this way?

Testing with curl:
- POST /login → 200 OK, get token
- GET /protected (immediate) → 200 OK
- GET /protected (after 1hr) → 401 Unauthorized

DISCOVERY: Users get abrupt logouts with no warning!
This isn't just "fix auth" - it's a UX problem

Actually found the real issue: no graceful token refresh system
Need to solve user experience, not just technical auth logic
```

#### Phase 2: Planning (Plan File) - Transform Discoveries
```bash
claude-memory plan "fix-auth-bug" --content "Implementation plan based on discoveries..."

# Plan MUST reference scratchpad discoveries:
## Problem Statement
Based on scratchpad investigation (line 12-18), users experience abrupt logouts due to 1-hour token expiry with no refresh mechanism.

## Root Cause (from scratchpad findings)
- No refresh token system (discovered in middleware.py analysis)
- No user warnings before expiry (found through curl testing)
- Poor error handling leads to sudden logouts (line 15 discovery)

## Solution Approach
The scratchpad testing revealed this is a UX problem requiring:
1. Implement refresh token endpoint (addresses scratchpad line 8 finding)
2. Add client-side expiry warnings (solves UX issue from line 15)
3. Graceful degradation when tokens expire

## Implementation Steps
[Concrete steps that solve the discovered problems...]
```

#### Phase 3: Execution (Progress File) - Reality vs Plan
```bash
claude-memory append "fix-auth-bug" "Progress update with reality vs plan comparison..."

# Progress MUST compare reality vs plan:
## Progress Update 1: Refresh Token Implementation
**Plan Expected**: Simple endpoint addition
**Reality**: Found existing token table needs schema changes
**Deviation**: Plan didn't anticipate database migration needed
**Solution**: Added migration step, extends timeline by 1 day

## Progress Update 2: Client Warnings
**Plan Expected**: Frontend warning 5min before expiry
**Reality**: Frontend doesn't track token timestamps
**New Discovery**: Need to modify auth response to include expiry
**Course Correction**: Updated API contract, client implementation
```

### ❌ ANTI-PATTERNS TO AVOID

**Bad Scratchpad (too structured):**
```
### Initial Questions:
- What's the bug?
- How to reproduce?
### Analysis Plan:
- Check code
- Run tests
```

**Bad Plan (no scratchpad references):**
```
## Implementation Steps:
1. Fix authentication
2. Add error handling
3. Write tests
```

### 🔒 PHASE VALIDATION RULES

**Scratchpad Requirements:**
- Show genuine uncertainty → discovery progression
- Include failed attempts and dead ends
- Ask questions that emerge from investigation
- Multiple exploration attempts before planning

**Plan Requirements:**
- Must reference specific scratchpad discoveries
- Explain how exploration led to chosen approach
- Transform messy findings into clear strategy

**Progress Requirements:**
- Compare actual vs planned outcomes
- Document plan deviations and reasons
- Capture emergent complexity not anticipated

### Sub-Agent Coordination (Simplified)
```bash
# Main agent creates task structure
claude-memory plan "implement-feature" --content "Feature implementation plan"

# Sub-agent receives simple instructions and memory context is auto-injected
Task(prompt="""
Task: Implement the authentication module

Memory operations (use these commands):
1. claude-memory scratchpad "implement-feature" --content "exploration findings"
2. claude-memory append "implement-feature" "Auth module implementation progress"
3. claude-memory status "implement-feature"  # Check current state
""")
```

---

## 📚 ESSENTIAL DEVELOPMENT COMMANDS

### Memory Management
```bash
# Check session status
claude-memory session info

# Initialize memory system
claude-memory init

# Task operations
claude-memory scratchpad "your-task" --content "exploration notes"
claude-memory plan "your-task" --content "implementation plan"
claude-memory append "your-task" "progress update"

# Status and context
claude-memory status "your-task"   # Specific task status
claude-memory status               # All tasks
claude-memory context              # Sub-agent context
```