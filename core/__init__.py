"""
Klix Core Package
Contains the core logic for the agent (Soul), session management, tools, and project context.
"""

from core.agent import KlixAgent
from core.session import Session
from core.project_context import ProjectContext, get_project_context, reload_project_context
from core.approval import ApprovalManager, ApprovalMode, RiskLevel, get_approval_manager
from core.planning import Plan, PlanStep, PlanningManager, get_planning_manager
from core.hooks import HookEvent, HookManager, get_hook_manager
from core.skills import Skill, SkillRegistry, get_skill_registry

__all__ = [
    "KlixAgent",
    "Session", 
    "ProjectContext",
    "get_project_context",
    "reload_project_context",
    # Approval
    "ApprovalManager",
    "ApprovalMode", 
    "RiskLevel",
    "get_approval_manager",
    # Planning
    "Plan",
    "PlanStep",
    "PlanningManager",
    "get_planning_manager",
    # Hooks
    "HookEvent",
    "HookManager",
    "get_hook_manager",
    # Skills
    "Skill",
    "SkillRegistry",
    "get_skill_registry",
]
