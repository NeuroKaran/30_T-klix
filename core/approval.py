"""
Klix Core - Approval Modes
Manages tool execution approval based on risk levels and user preferences.
Inspired by Claude Code's approval modes (Suggest, Auto-Edit, Full Auto).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from logging_config import get_logger

logger = get_logger(__name__)


class ApprovalMode(Enum):
    """
    Approval modes for tool execution.
    
    SUGGEST: Always ask for approval before any action.
    AUTO_EDIT: Auto-approve low-risk actions, ask for medium/high.
    FULL_AUTO: Auto-approve all except high-risk destructive actions.
    YOLO: No approval needed (dangerous, for experienced users).
    """
    SUGGEST = "suggest"
    AUTO_EDIT = "auto_edit"
    FULL_AUTO = "full_auto"
    YOLO = "yolo"


class RiskLevel(Enum):
    """Risk levels for tool operations."""
    LOW = "low"           # Read-only, informational
    MEDIUM = "medium"     # Writes/modifies files, but reversible
    HIGH = "high"         # Potentially destructive, harder to undo
    CRITICAL = "critical" # System-level, external effects, irreversible


@dataclass
class ToolRiskProfile:
    """Defines the risk profile for a tool."""
    tool_name: str
    base_risk: RiskLevel
    description: str = ""
    requires_confirmation: bool = False  # Always requires confirmation regardless of mode
    
    def get_effective_risk(self, arguments: dict[str, Any] | None = None) -> RiskLevel:
        """
        Get effective risk level based on arguments.
        Can be overridden for dynamic risk assessment.
        """
        return self.base_risk


# Default risk profiles for built-in tools
DEFAULT_RISK_PROFILES: dict[str, ToolRiskProfile] = {
    # Read-only tools (LOW risk)
    "ls": ToolRiskProfile("ls", RiskLevel.LOW, "List directory contents"),
    "cat": ToolRiskProfile("cat", RiskLevel.LOW, "Read file contents"),
    "get_project_structure": ToolRiskProfile("get_project_structure", RiskLevel.LOW, "View project structure"),
    "web_search": ToolRiskProfile("web_search", RiskLevel.LOW, "Search the web"),
    "search_web": ToolRiskProfile("search_web", RiskLevel.LOW, "Search the web"),
    "git_status": ToolRiskProfile("git_status", RiskLevel.LOW, "View git status"),
    "git_diff": ToolRiskProfile("git_diff", RiskLevel.LOW, "View git differences"),
    "git_log": ToolRiskProfile("git_log", RiskLevel.LOW, "View git history"),
    "git_branch": ToolRiskProfile("git_branch", RiskLevel.LOW, "List git branches"),
    "dns_lookup": ToolRiskProfile("dns_lookup", RiskLevel.LOW, "DNS lookup"),
    "whois_lookup": ToolRiskProfile("whois_lookup", RiskLevel.LOW, "WHOIS lookup"),
    "http_headers": ToolRiskProfile("http_headers", RiskLevel.LOW, "Fetch HTTP headers"),
    
    # Write tools (MEDIUM risk)
    "write_file": ToolRiskProfile("write_file", RiskLevel.MEDIUM, "Create or modify files"),
    "append_file": ToolRiskProfile("append_file", RiskLevel.MEDIUM, "Append to files"),
    "git_commit": ToolRiskProfile("git_commit", RiskLevel.MEDIUM, "Create git commits"),
    
    # Destructive tools (HIGH risk)
    "delete_file": ToolRiskProfile("delete_file", RiskLevel.HIGH, "Delete files"),
    "run_command": ToolRiskProfile("run_command", RiskLevel.HIGH, "Execute shell commands"),
    "port_scan": ToolRiskProfile("port_scan", RiskLevel.HIGH, "Scan network ports"),
}


@dataclass
class ApprovalManager:
    """
    Manages tool execution approval workflow.
    
    Determines whether a tool call requires user approval based on:
    - Current approval mode
    - Tool's risk profile
    - Specific arguments being used
    """
    
    mode: ApprovalMode = ApprovalMode.AUTO_EDIT
    risk_profiles: dict[str, ToolRiskProfile] = field(default_factory=lambda: DEFAULT_RISK_PROFILES.copy())
    
    # Callbacks for UI integration
    on_approval_needed: Callable[[str, dict, RiskLevel], bool] | None = None
    
    def get_risk_profile(self, tool_name: str) -> ToolRiskProfile:
        """Get risk profile for a tool, defaulting to MEDIUM if unknown."""
        return self.risk_profiles.get(
            tool_name,
            ToolRiskProfile(tool_name, RiskLevel.MEDIUM, "Unknown tool")
        )
    
    def register_risk_profile(self, profile: ToolRiskProfile) -> None:
        """Register or update a tool's risk profile."""
        self.risk_profiles[profile.tool_name] = profile
    
    def needs_approval(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None
    ) -> tuple[bool, RiskLevel, str]:
        """
        Check if a tool call needs user approval.
        
        Returns:
            Tuple of (needs_approval, risk_level, reason)
        """
        profile = self.get_risk_profile(tool_name)
        effective_risk = profile.get_effective_risk(arguments)
        
        # Critical actions always need approval (except YOLO mode)
        if effective_risk == RiskLevel.CRITICAL:
            if self.mode == ApprovalMode.YOLO:
                return (False, effective_risk, "YOLO mode - no approval needed")
            return (True, effective_risk, f"Critical action: {profile.description}")
        
        # Tools marked as requiring confirmation always need it
        if profile.requires_confirmation and self.mode != ApprovalMode.YOLO:
            return (True, effective_risk, f"Confirmation required: {profile.description}")
        
        # Apply mode-based rules
        if self.mode == ApprovalMode.SUGGEST:
            # Always ask for approval
            return (True, effective_risk, f"Suggest mode: {profile.description}")
        
        elif self.mode == ApprovalMode.AUTO_EDIT:
            # Auto-approve LOW risk, ask for MEDIUM and above
            if effective_risk == RiskLevel.LOW:
                return (False, effective_risk, "Low risk - auto-approved")
            return (True, effective_risk, f"{effective_risk.value.title()} risk: {profile.description}")
        
        elif self.mode == ApprovalMode.FULL_AUTO:
            # Auto-approve LOW and MEDIUM, ask for HIGH and above
            if effective_risk in (RiskLevel.LOW, RiskLevel.MEDIUM):
                return (False, effective_risk, "Auto-approved in full-auto mode")
            return (True, effective_risk, f"High risk action: {profile.description}")
        
        elif self.mode == ApprovalMode.YOLO:
            # Never ask for approval
            return (False, effective_risk, "YOLO mode - no approval needed")
        
        # Default to requiring approval
        return (True, effective_risk, "Unknown mode - requiring approval")
    
    async def request_approval(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        risk_level: RiskLevel,
        reason: str,
    ) -> bool:
        """
        Request approval from the user.
        
        Returns True if approved, False if denied.
        Uses the on_approval_needed callback if set.
        """
        if self.on_approval_needed:
            return self.on_approval_needed(tool_name, arguments, risk_level)
        
        # Default: log and approve (for testing)
        logger.warning(
            f"Approval needed for {tool_name} ({risk_level.value}): {reason}"
        )
        return True  # Default approve if no callback
    
    def set_mode(self, mode: ApprovalMode | str) -> None:
        """Set the approval mode."""
        if isinstance(mode, str):
            mode = ApprovalMode(mode.lower())
        self.mode = mode
        logger.info(f"Approval mode set to: {mode.value}")
    
    def get_mode_description(self) -> str:
        """Get a human-readable description of the current mode."""
        descriptions = {
            ApprovalMode.SUGGEST: "All actions require approval",
            ApprovalMode.AUTO_EDIT: "Low-risk actions auto-approved, others need approval",
            ApprovalMode.FULL_AUTO: "Low and medium-risk auto-approved, high-risk needs approval",
            ApprovalMode.YOLO: "All actions auto-approved (dangerous!)",
        }
        return descriptions.get(self.mode, "Unknown mode")


# Global approval manager instance
_approval_manager: ApprovalManager | None = None


def get_approval_manager() -> ApprovalManager:
    """Get or create the global ApprovalManager instance."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager


def set_approval_mode(mode: ApprovalMode | str) -> None:
    """Set the global approval mode."""
    get_approval_manager().set_mode(mode)


def check_approval(
    tool_name: str,
    arguments: dict[str, Any] | None = None
) -> tuple[bool, RiskLevel, str]:
    """
    Check if a tool call needs approval.
    
    Convenience function that uses the global manager.
    """
    return get_approval_manager().needs_approval(tool_name, arguments)
