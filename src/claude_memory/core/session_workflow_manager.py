"""
Session Workflow Manager for enforcing single coherent workflow per session.

Ensures only ONE active task per session, preventing multiple agents from
creating parallel workflows and maintaining coherent collaboration.
"""

from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass

from .context_loader import WorkflowContextLoader, WorkflowContext
from .workflow_enforcer import WorkflowPhase


@dataclass
class WorkflowSession:
    """Represents a workflow session state."""
    session_id: str
    active_task: Optional[str]
    created_at: datetime
    last_activity: datetime
    contributors: List[str]


class SessionWorkflowManager:
    """Enforces single coherent workflow per session."""

    def __init__(self, storage_path: Path, session_id: str):
        """
        Initialize session workflow manager.

        Args:
            storage_path: Base storage path for memories
            session_id: Current session ID
        """
        self.storage_path = storage_path
        self.session_id = session_id
        self.context_loader = WorkflowContextLoader(storage_path, session_id)

    def claim_workflow(self, task_name: str, agent_id: str = "Main Agent") -> Tuple[bool, str]:
        """
        Claim workflow for the session.

        Args:
            task_name: Name of the task to claim
            agent_id: Identifier of the agent claiming

        Returns:
            Tuple of (success, message)
        """
        active_task = self.context_loader.get_active_task()

        if active_task:
            if active_task == task_name:
                # Same task, allow continuation
                return True, f"Continuing existing workflow: {active_task}"
            else:
                # Different task, block
                context = self.context_loader.load_existing_context(active_task)
                return False, self._format_existing_task_error(active_task, context, task_name)
        else:
            # No active task, allow claiming
            return True, f"Claimed new workflow: {task_name}"

    def force_workflow_continuity(self, attempted_task: str, agent_id: str = "Agent") -> Tuple[str, WorkflowContext]:
        """
        Force agent to continue existing workflow instead of creating new one.

        Args:
            attempted_task: Task name the agent tried to create
            agent_id: Identifier of the agent

        Returns:
            Tuple of (actual_task_to_use, context)
        """
        active_task = self.context_loader.get_active_task()

        if not active_task:
            # No existing task, allow the new one
            return attempted_task, self.context_loader.load_existing_context(attempted_task)

        if active_task == attempted_task:
            # Same task, load context
            return active_task, self.context_loader.load_existing_context(active_task)

        # Different task attempted, force to use existing
        context = self.context_loader.load_existing_context(active_task)
        return active_task, context

    def validate_contribution(self, task_name: str, content: str, action: str) -> Tuple[bool, str]:
        """
        Validate that contribution is appropriate for current session state.

        Args:
            task_name: Task name for the contribution
            content: Content to contribute
            action: Action being performed (scratchpad, ensure, append)

        Returns:
            Tuple of (is_valid, message)
        """
        # Check if task is the active workflow
        active_task = self.context_loader.get_active_task()

        if active_task and task_name != active_task:
            context = self.context_loader.load_existing_context(active_task)
            return False, self._format_task_mismatch_error(task_name, active_task, context)

        # Load context to check for duplication
        context = self.context_loader.load_existing_context(task_name)

        if action == "scratchpad" and context.scratchpad:
            # Check for content duplication
            if self.context_loader.is_content_duplicate(content, context.scratchpad.content):
                similar_section = self.context_loader.find_similar_content(content, context.scratchpad.content)
                return False, self._format_duplication_error(similar_section, context)

        return True, "Valid contribution"

    def get_context_injection_text(self, task_name: str) -> str:
        """
        Get text to inject into agent prompts with existing context.

        Args:
            task_name: Task name to get context for

        Returns:
            Context injection text for agent prompts
        """
        context = self.context_loader.load_existing_context(task_name)

        if not context.has_existing_work():
            return ""  # No context to inject for fresh start

        injection = f"""
⚠️ CRITICAL: READ EXISTING WORK BEFORE PROCEEDING

Session Active Task: '{context.active_task}'
Current Phase: {context.current_phase.value}
Last Activity: {self._get_last_activity(context)}

"""

        # Add scratchpad context if exists
        if context.scratchpad:
            injection += f"""
=== EXISTING SCRATCHPAD FINDINGS ===
Contributors: {', '.join(context.scratchpad.contributors)}
Key Findings:
{self._format_key_findings(context.scratchpad.key_findings)}

Recent Content:
{context.scratchpad.content[-1500:]}  # Last 1500 chars

"""

        # Add plan context if exists
        if context.plan:
            injection += f"""
=== EXISTING PLAN ===
{context.plan.content}

"""

        # Add progress context if exists
        if context.progress:
            injection += f"""
=== EXISTING PROGRESS ===
{context.progress.content[-800:]}  # Last 800 chars

"""

        # Add requirements
        injection += f"""
⚠️ MANDATORY REQUIREMENTS:
1. You MUST work on task: '{context.active_task}'
2. DO NOT repeat work already done above
3. BUILD ON existing findings and progress
4. Use: claude-memory scratchpad '{context.active_task}' --content "NEW insights building on above"
5. If plan exists, FOLLOW it during implementation
6. If progress exists, CONTINUE from where it stopped

🎯 Next Suggested Action: {self.context_loader.suggest_next_work(context)}

"""

        return injection

    def _format_existing_task_error(self, active_task: str, context: WorkflowContext, attempted_task: str) -> str:
        """Format error message for attempting to create new task when one exists."""
        return f"""❌ Cannot create task '{attempted_task}'. Session already working on '{active_task}'.

📚 EXISTING WORK SUMMARY:
{context.get_summary()}

🔍 Current Phase: {context.current_phase.value}

🎯 You must continue existing workflow:
   claude-memory scratchpad '{active_task}' --content "NEW insights building on existing work"

📖 Read existing work first to understand what's already been done."""

    def _format_task_mismatch_error(self, attempted_task: str, active_task: str, context: WorkflowContext) -> str:
        """Format error message for task name mismatch."""
        return f"""❌ Task name mismatch! Session is working on '{active_task}', not '{attempted_task}'.

📚 ACTIVE WORKFLOW:
Task: {active_task}
Phase: {context.current_phase.value}
Work Done: {context.get_summary()}

🔄 Use correct task name:
   claude-memory scratchpad '{active_task}' --content "your contribution"
"""

    def _format_duplication_error(self, similar_section: str, context: WorkflowContext) -> str:
        """Format error message for duplicate content."""
        error = f"""❌ This exploration already exists in scratchpad!

📖 EXISTING SIMILAR WORK:
{similar_section}

🎯 Instead, provide NEW insights:
- Build on existing findings
- Explore different aspects
- Add missing analysis
- Continue where previous work stopped

💡 Current Phase: {context.current_phase.value}
📊 Existing Findings: {len(context.scratchpad.key_findings) if context.scratchpad else 0}
"""

        if context.current_phase == WorkflowPhase.DISCOVERY and context.scratchpad:
            if len(context.scratchpad.key_findings) >= 3:
                error += "\n🚀 Consider creating a plan: claude-memory plan 'task-name' --content 'implementation strategy'"

        return error

    def _get_last_activity(self, context: WorkflowContext) -> str:
        """Get last activity timestamp from context."""
        last_times = []

        if context.scratchpad:
            last_times.append(context.scratchpad.last_update)
        if context.plan:
            last_times.append(context.plan.last_update)
        if context.progress:
            last_times.append(context.progress.last_update)

        return max(last_times) if last_times else "Unknown"

    def _format_key_findings(self, findings: List[str]) -> str:
        """Format key findings for display."""
        if not findings:
            return "No key findings yet"

        formatted = []
        for i, finding in enumerate(findings[:5], 1):  # Show max 5
            formatted.append(f"{i}. {finding}")

        return "\n".join(formatted)

    def get_session_stats(self) -> Dict:
        """Get statistics about current session."""
        context = self.context_loader.load_existing_context()

        stats = {
            "session_id": self.session_id,
            "active_task": context.active_task,
            "current_phase": context.current_phase.value if context.active_task else "SETUP",
            "has_scratchpad": bool(context.scratchpad),
            "has_plan": bool(context.plan),
            "has_progress": bool(context.progress),
            "total_contributors": 0,
            "total_words": 0
        }

        all_contributors = set()

        if context.scratchpad:
            all_contributors.update(context.scratchpad.contributors)
            stats["total_words"] += context.scratchpad.word_count

        if context.plan:
            all_contributors.update(context.plan.contributors)
            stats["total_words"] += context.plan.word_count

        if context.progress:
            all_contributors.update(context.progress.contributors)
            stats["total_words"] += context.progress.word_count

        stats["total_contributors"] = len(all_contributors)
        stats["contributors"] = list(all_contributors)

        return stats