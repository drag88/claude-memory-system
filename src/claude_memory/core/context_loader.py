"""
Workflow Context Loader for mandatory context reading.

Forces all agents to read and understand existing work before contributing,
preventing duplication and ensuring coherent collaboration.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass

from .workflow_enforcer import WorkflowEnforcer, WorkflowPhase, FileType


@dataclass
class ExistingWork:
    """Represents existing work in a file."""
    content: str
    last_update: str
    contributors: List[str]
    key_findings: List[str]
    word_count: int


@dataclass
class WorkflowContext:
    """Complete context of existing workflow."""
    active_task: str
    session_id: str
    current_phase: WorkflowPhase
    scratchpad: Optional[ExistingWork]
    plan: Optional[ExistingWork]
    progress: Optional[ExistingWork]

    def has_existing_work(self) -> bool:
        """Check if there's any existing work."""
        return bool(self.scratchpad or self.plan or self.progress)

    def get_summary(self) -> str:
        """Get concise summary of existing work."""
        summary = []

        if self.scratchpad:
            summary.append(f"Scratchpad: {len(self.scratchpad.key_findings)} findings, {self.scratchpad.word_count} words")

        if self.plan:
            summary.append(f"Plan: {self.plan.word_count} words")

        if self.progress:
            summary.append(f"Progress: {self.progress.word_count} words")

        return " | ".join(summary) if summary else "No existing work"


class WorkflowContextLoader:
    """Forces agents to read existing work before contributing."""

    def __init__(self, storage_path: Path, session_id: str):
        """
        Initialize context loader.

        Args:
            storage_path: Base storage path for memories
            session_id: Current session ID
        """
        self.storage_path = storage_path
        self.session_id = session_id
        self._context_cache = {}

    def get_active_task(self) -> Optional[str]:
        """
        Get the currently active task in this session.

        Returns:
            Active task name or None if no active task
        """
        # System directories that should not be considered as tasks
        system_dirs = {'.context', 'sessions', '.git', '.DS_Store'}

        if not self.storage_path.exists():
            return None

        # Look for task directories with files for this session
        for task_dir in self.storage_path.iterdir():
            if task_dir.is_dir() and task_dir.name not in system_dirs:
                # Check if this task has any files for current session
                session_files = list(task_dir.glob(f"*{self.session_id}*"))
                if session_files:
                    return task_dir.name

        return None

    def load_existing_context(self, task_name: Optional[str] = None) -> WorkflowContext:
        """
        Load complete context of existing work in session.

        Args:
            task_name: Specific task name, or None to auto-detect

        Returns:
            Complete workflow context
        """
        # Use provided task name or auto-detect active task
        active_task = task_name or self.get_active_task()

        if not active_task:
            # Return empty context for fresh session
            return WorkflowContext(
                active_task="",
                session_id=self.session_id,
                current_phase=WorkflowPhase.SETUP,
                scratchpad=None,
                plan=None,
                progress=None
            )

        # Check cache first
        cache_key = f"{active_task}-{self.session_id}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        # Load task files
        enforcer = WorkflowEnforcer(self.storage_path, self.session_id)
        files = enforcer.get_task_files(active_task)
        current_phase, _ = enforcer.get_workflow_phase(active_task)

        # Load each file's content
        scratchpad_work = self._load_file_work(files[FileType.SCRATCHPAD]) if files[FileType.SCRATCHPAD] else None
        plan_work = self._load_file_work(files[FileType.PLAN]) if files[FileType.PLAN] else None
        progress_work = self._load_file_work(files[FileType.PROGRESS]) if files[FileType.PROGRESS] else None

        context = WorkflowContext(
            active_task=active_task,
            session_id=self.session_id,
            current_phase=current_phase,
            scratchpad=scratchpad_work,
            plan=plan_work,
            progress=progress_work
        )

        # Cache the context
        self._context_cache[cache_key] = context
        return context

    def _load_file_work(self, file_path: Path) -> ExistingWork:
        """
        Load and analyze work from a file.

        Args:
            file_path: Path to the file

        Returns:
            ExistingWork object with analyzed content
        """
        if not file_path or not file_path.exists():
            return None

        content = file_path.read_text()

        # Extract contributors from content
        contributors = self._extract_contributors(content)

        # Extract key findings from scratchpad content
        key_findings = self._extract_key_findings(content)

        # Get last modification time
        last_update = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        # Count words (rough estimate)
        word_count = len(content.split())

        return ExistingWork(
            content=content,
            last_update=last_update,
            contributors=contributors,
            key_findings=key_findings,
            word_count=word_count
        )

    def _extract_contributors(self, content: str) -> List[str]:
        """Extract contributor names from file content."""
        contributors = set()

        # Look for agent contribution patterns
        patterns = [
            r"## (.+?) - \d{4}-\d{2}-\d{2}",
            r"## (.+?) Contribution",
            r"### Revised - (.+?) -",
            r"## Progress Update - (.+?) -"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            contributors.update(matches)

        return list(contributors)

    def _extract_key_findings(self, content: str) -> List[str]:
        """Extract key findings from scratchpad content."""
        findings = []

        # Look for common finding patterns
        patterns = [
            r"DISCOVERY:(.+?)(?=\n\n|\nNext|\n##|$)",
            r"FINDING:(.+?)(?=\n\n|\nNext|\n##|$)",
            r"ISSUE:(.+?)(?=\n\n|\nNext|\n##|$)",
            r"FOUND:(.+?)(?=\n\n|\nNext|\n##|$)"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            findings.extend([match.strip()[:200] for match in matches])

        # Also extract items from bullet lists
        bullet_pattern = r"^[-*•]\s+(.+)$"
        bullet_matches = re.findall(bullet_pattern, content, re.MULTILINE)
        findings.extend([match.strip()[:100] for match in bullet_matches[:5]])  # First 5 bullets

        return findings[:10]  # Return max 10 findings

    def is_content_duplicate(self, new_content: str, existing_content: str) -> bool:
        """
        Check if new content is similar to existing content.

        Args:
            new_content: New content to check
            existing_content: Existing content to compare against

        Returns:
            True if content appears to be duplicate
        """
        if not existing_content or not new_content:
            return False

        # Normalize content for comparison
        def normalize(text):
            return re.sub(r'\s+', ' ', text.lower().strip())

        new_norm = normalize(new_content)
        existing_norm = normalize(existing_content)

        # Check for substantial overlap (simple approach)
        if len(new_norm) < 20:  # Too short to be meaningful
            return False

        # Check if new content is substantially contained in existing
        words_new = set(new_norm.split())
        words_existing = set(existing_norm.split())

        if len(words_new) == 0:
            return False

        overlap = len(words_new.intersection(words_existing))
        overlap_ratio = overlap / len(words_new)

        return overlap_ratio > 0.7  # 70% word overlap threshold

    def find_similar_content(self, new_content: str, existing_content: str) -> Optional[str]:
        """
        Find the most similar section in existing content.

        Args:
            new_content: New content to match
            existing_content: Existing content to search in

        Returns:
            Most similar section or None
        """
        if not self.is_content_duplicate(new_content, existing_content):
            return None

        # Split existing content into paragraphs
        paragraphs = [p.strip() for p in existing_content.split('\n\n') if p.strip()]

        new_words = set(new_content.lower().split())
        best_match = None
        best_score = 0

        for para in paragraphs:
            para_words = set(para.lower().split())
            if len(para_words) == 0:
                continue

            overlap = len(new_words.intersection(para_words))
            score = overlap / len(para_words)

            if score > best_score and score > 0.5:
                best_score = score
                best_match = para

        return best_match[:300] + "..." if best_match and len(best_match) > 300 else best_match

    def suggest_next_work(self, context: WorkflowContext) -> str:
        """
        Suggest what work should be done next based on existing context.

        Args:
            context: Current workflow context

        Returns:
            Suggestion for next work
        """
        if not context.has_existing_work():
            return "Start with exploration in scratchpad"

        suggestions = []

        # Analyze current phase and suggest next steps
        if context.current_phase == WorkflowPhase.DISCOVERY:
            if context.scratchpad:
                findings_count = len(context.scratchpad.key_findings)
                if findings_count < 3:
                    suggestions.append("Continue exploration - need more findings")
                else:
                    suggestions.append("Sufficient exploration done - create plan")

        elif context.current_phase == WorkflowPhase.PLANNING:
            suggestions.append("Review and refine plan, or start execution")

        elif context.current_phase == WorkflowPhase.EXECUTION:
            suggestions.append("Continue implementation following the plan")

        return "; ".join(suggestions) if suggestions else "Continue current phase"

    def invalidate_cache(self, task_name: str = None):
        """Invalidate context cache."""
        if task_name:
            cache_key = f"{task_name}-{self.session_id}"
            self._context_cache.pop(cache_key, None)
        else:
            self._context_cache.clear()