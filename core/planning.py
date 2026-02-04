"""
Klix Core - Planning Mode
Think-before-act capability for complex tasks.
Enables the agent to create structured plans before executing actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from logging_config import get_logger

logger = get_logger(__name__)


class PlanStatus(Enum):
    """Status of a plan or step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in a plan."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    description: str = ""
    tool: str | None = None  # Tool to use (if known)
    arguments: dict[str, Any] = field(default_factory=dict)
    status: PlanStatus = PlanStatus.PENDING
    result: str | None = None
    error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "tool": self.tool,
            "arguments": self.arguments,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanStep:
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())[:8]),
            description=data.get("description", ""),
            tool=data.get("tool"),
            arguments=data.get("arguments", {}),
            status=PlanStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class Plan:
    """
    A structured plan for completing a complex task.
    
    Plans consist of multiple steps that can be executed sequentially.
    The agent creates plans in planning mode before executing actions.
    """
    
    id: str = field(default_factory=lambda: str(uuid4()))
    goal: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    steps: list[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    summary: str = ""
    
    @property
    def current_step_index(self) -> int:
        """Get the index of the current step being executed."""
        for i, step in enumerate(self.steps):
            if step.status in (PlanStatus.PENDING, PlanStatus.IN_PROGRESS):
                return i
        return len(self.steps)  # All done
    
    @property
    def current_step(self) -> PlanStep | None:
        """Get the current step being executed."""
        idx = self.current_step_index
        if idx < len(self.steps):
            return self.steps[idx]
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if all steps are complete."""
        return all(s.status in (PlanStatus.COMPLETED, PlanStatus.SKIPPED) for s in self.steps)
    
    @property
    def progress(self) -> tuple[int, int]:
        """Get progress as (completed, total)."""
        completed = sum(1 for s in self.steps if s.status in (PlanStatus.COMPLETED, PlanStatus.SKIPPED))
        return (completed, len(self.steps))
    
    def add_step(self, description: str, tool: str | None = None, **kwargs) -> PlanStep:
        """Add a new step to the plan."""
        step = PlanStep(description=description, tool=tool, arguments=kwargs)
        self.steps.append(step)
        return step
    
    def mark_step_complete(self, step_id: str, result: str | None = None) -> bool:
        """Mark a step as complete."""
        for step in self.steps:
            if step.id == step_id:
                step.status = PlanStatus.COMPLETED
                step.result = result
                return True
        return False
    
    def mark_step_failed(self, step_id: str, error: str) -> bool:
        """Mark a step as failed."""
        for step in self.steps:
            if step.id == step_id:
                step.status = PlanStatus.FAILED
                step.error = error
                return True
        return False
    
    def to_markdown(self) -> str:
        """Generate a markdown representation of the plan."""
        lines = [
            f"## Plan: {self.goal}",
            f"*Created: {self.created_at.strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]
        
        completed, total = self.progress
        lines.append(f"**Progress:** {completed}/{total} steps")
        lines.append("")
        
        for i, step in enumerate(self.steps, 1):
            status_icon = {
                PlanStatus.PENDING: "⬜",
                PlanStatus.IN_PROGRESS: "🔄",
                PlanStatus.COMPLETED: "✅",
                PlanStatus.FAILED: "❌",
                PlanStatus.SKIPPED: "⏭️",
            }.get(step.status, "⬜")
            
            tool_info = f" `{step.tool}`" if step.tool else ""
            lines.append(f"{status_icon} **Step {i}:** {step.description}{tool_info}")
            
            if step.result:
                lines.append(f"   → {step.result[:100]}...")
            if step.error:
                lines.append(f"   ⚠️ Error: {step.error}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "goal": self.goal,
            "created_at": self.created_at.isoformat(),
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "summary": self.summary,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            goal=data.get("goal", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            steps=[PlanStep.from_dict(s) for s in data.get("steps", [])],
            status=PlanStatus(data.get("status", "pending")),
            summary=data.get("summary", ""),
        )


@dataclass
class PlanningManager:
    """
    Manages planning mode and plan execution.
    
    When planning mode is enabled, the agent will:
    1. Create a plan before executing actions
    2. Show the plan to the user for approval
    3. Execute steps one at a time with progress tracking
    """
    
    enabled: bool = False
    current_plan: Plan | None = None
    plans_history: list[Plan] = field(default_factory=list)
    auto_execute: bool = False  # If True, execute plan immediately after creation
    
    def start_planning(self, goal: str) -> Plan:
        """Start a new plan for the given goal."""
        self.current_plan = Plan(goal=goal)
        self.enabled = True
        logger.info(f"Started planning for: {goal}")
        return self.current_plan
    
    def finalize_plan(self) -> Plan | None:
        """Finalize the current plan and prepare for execution."""
        if self.current_plan:
            self.current_plan.status = PlanStatus.IN_PROGRESS
            self.plans_history.append(self.current_plan)
            logger.info(f"Plan finalized: {len(self.current_plan.steps)} steps")
        return self.current_plan
    
    def cancel_plan(self) -> None:
        """Cancel the current plan."""
        self.current_plan = None
        self.enabled = False
        logger.info("Plan cancelled")
    
    def complete_plan(self, summary: str = "") -> None:
        """Mark the current plan as complete."""
        if self.current_plan:
            self.current_plan.status = PlanStatus.COMPLETED
            self.current_plan.summary = summary
            logger.info(f"Plan completed: {summary}")
        self.current_plan = None
        self.enabled = False
    
    def get_planning_prompt(self, user_input: str) -> str:
        """
        Generate a prompt to help the agent create a plan.
        
        This is injected into the system prompt when planning mode is enabled.
        """
        return f"""
## Planning Mode Active

You are in PLANNING MODE. Before taking actions, create a structured plan.

**Task:** {user_input}

**Instructions:**
1. Analyze the task and break it down into discrete steps
2. For each step, identify:
   - What needs to be done
   - Which tool might be needed (if any)
   - Any dependencies on previous steps
3. Present the plan in a clear, numbered format
4. Wait for user approval before executing

**Format your plan as:**
```
Step 1: [Description]
   Tool: [tool_name] (if applicable)
   
Step 2: [Description]
   Tool: [tool_name] (if applicable)
   
...
```

After presenting the plan, ask: "Shall I proceed with this plan?"
"""


# Global planning manager instance
_planning_manager: PlanningManager | None = None


def get_planning_manager() -> PlanningManager:
    """Get or create the global PlanningManager instance."""
    global _planning_manager
    if _planning_manager is None:
        _planning_manager = PlanningManager()
    return _planning_manager


def enable_planning_mode(goal: str = "") -> Plan:
    """Enable planning mode and optionally start a new plan."""
    manager = get_planning_manager()
    manager.enabled = True
    if goal:
        return manager.start_planning(goal)
    return manager.current_plan or Plan()


def disable_planning_mode() -> None:
    """Disable planning mode."""
    manager = get_planning_manager()
    manager.enabled = False


def is_planning_enabled() -> bool:
    """Check if planning mode is enabled."""
    return get_planning_manager().enabled
