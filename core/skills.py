"""
Klix Core - Skills System
Extensible skills that package prompts, tools, and behaviors.
Similar to Claude Code's skills concept.
"""

from __future__ import annotations

import importlib.util
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SkillMetadata:
    """Metadata for a skill."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Other skill names


class Skill(ABC):
    """
    Base class for Klix skills.
    
    Skills can provide:
    - System prompt sections (context injection)
    - Custom tools
    - Hooks for lifecycle events
    - Response transformations
    """
    
    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        pass
    
    def get_system_prompt(self) -> str:
        """
        Return text to inject into the system prompt.
        Override this to provide skill-specific context.
        """
        return ""
    
    def get_tools(self) -> list[dict[str, Any]]:
        """
        Return tool definitions specific to this skill.
        Override to provide custom tools.
        """
        return []
    
    def register_hooks(self, hook_manager: Any) -> None:
        """
        Register hooks with the hook manager.
        Override to respond to lifecycle events.
        """
        pass
    
    def on_activate(self) -> None:
        """Called when the skill is activated."""
        logger.info(f"Skill activated: {self.metadata.name}")
    
    def on_deactivate(self) -> None:
        """Called when the skill is deactivated."""
        logger.info(f"Skill deactivated: {self.metadata.name}")


@dataclass
class SkillRegistry:
    """Manages loading and activation of skills."""
    
    skills: dict[str, Skill] = field(default_factory=dict)
    active_skills: set[str] = field(default_factory=set)
    skills_dir: Path = field(default_factory=lambda: Path(__file__).parent / "skills")
    
    def register(self, skill: Skill) -> None:
        """Register a skill."""
        name = skill.metadata.name
        self.skills[name] = skill
        logger.info(f"Registered skill: {name}")
    
    def unregister(self, name: str) -> bool:
        """Unregister a skill by name."""
        if name in self.skills:
            if name in self.active_skills:
                self.deactivate(name)
            del self.skills[name]
            return True
        return False
    
    def activate(self, name: str) -> bool:
        """Activate a skill."""
        if name not in self.skills:
            logger.warning(f"Skill not found: {name}")
            return False
        
        if name in self.active_skills:
            return True  # Already active
        
        skill = self.skills[name]
        
        # Check dependencies
        for dep in skill.metadata.dependencies:
            if dep not in self.active_skills:
                logger.warning(f"Skill {name} requires {dep} to be active")
                return False
        
        skill.on_activate()
        self.active_skills.add(name)
        return True
    
    def deactivate(self, name: str) -> bool:
        """Deactivate a skill."""
        if name not in self.active_skills:
            return False
        
        self.skills[name].on_deactivate()
        self.active_skills.remove(name)
        return True
    
    def get_active_skills(self) -> list[Skill]:
        """Get all active skills."""
        return [self.skills[name] for name in self.active_skills if name in self.skills]
    
    def get_combined_prompt(self) -> str:
        """Get combined system prompt from all active skills."""
        prompts = []
        for skill in self.get_active_skills():
            prompt = skill.get_system_prompt()
            if prompt:
                prompts.append(f"## Skill: {skill.metadata.name}\n\n{prompt}")
        
        return "\n\n".join(prompts) if prompts else ""
    
    def get_combined_tools(self) -> list[dict[str, Any]]:
        """Get combined tools from all active skills."""
        tools = []
        for skill in self.get_active_skills():
            tools.extend(skill.get_tools())
        return tools
    
    def load_from_directory(self, directory: Path | None = None) -> int:
        """
        Load skills from a directory.
        Looks for Python files with a `skill` attribute.
        """
        search_dir = directory or self.skills_dir
        if not search_dir.exists():
            return 0
        
        loaded = 0
        for filepath in search_dir.glob("*.py"):
            if filepath.name.startswith("_"):
                continue
            
            try:
                spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "skill") and isinstance(module.skill, Skill):
                        self.register(module.skill)
                        loaded += 1
            except Exception as e:
                logger.error(f"Failed to load skill from {filepath}: {e}")
        
        return loaded
    
    def list_skills(self) -> list[dict[str, Any]]:
        """List all registered skills with their status."""
        return [
            {
                "name": skill.metadata.name,
                "description": skill.metadata.description,
                "version": skill.metadata.version,
                "active": name in self.active_skills,
                "tags": skill.metadata.tags,
            }
            for name, skill in self.skills.items()
        ]


# Built-in skills

class GitExpertSkill(Skill):
    """Built-in skill for Git operations expertise."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="git_expert",
            description="Enhanced Git operations with best practices",
            version="1.0.0",
            author="Klix",
            tags=["git", "version-control", "built-in"],
        )
    
    def get_system_prompt(self) -> str:
        return """
## Git Best Practices

When working with Git:
- Always check `git status` before making changes
- Write clear, descriptive commit messages (imperative mood)
- Use feature branches for new work
- Review changes with `git diff` before committing
- Keep commits atomic (one logical change per commit)

Common workflows:
1. **New feature:** branch → develop → commit → push → PR
2. **Quick fix:** stash → fix → commit → pop stash
3. **Undo changes:** `git checkout -- <file>` for unstaged, `git reset` for staged
"""


class CodeReviewSkill(Skill):
    """Built-in skill for code review assistance."""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="code_review",
            description="Code review assistance and best practices",
            version="1.0.0",
            author="Klix",
            tags=["review", "quality", "built-in"],
        )
    
    def get_system_prompt(self) -> str:
        return """
## Code Review Guidelines

When reviewing code, check for:
- **Correctness:** Does it do what it's supposed to?
- **Readability:** Is the code clear and well-documented?
- **Performance:** Are there any obvious inefficiencies?
- **Security:** Are there potential vulnerabilities?
- **Testing:** Are there adequate tests?
- **Style:** Does it follow project conventions?

Provide constructive feedback with specific suggestions.
"""


# Global skill registry instance
_skill_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    """Get or create the global SkillRegistry instance."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
        # Register built-in skills
        _skill_registry.register(GitExpertSkill())
        _skill_registry.register(CodeReviewSkill())
    return _skill_registry


def activate_skill(name: str) -> bool:
    """Activate a skill by name."""
    return get_skill_registry().activate(name)


def deactivate_skill(name: str) -> bool:
    """Deactivate a skill by name."""
    return get_skill_registry().deactivate(name)


def list_skills() -> list[dict[str, Any]]:
    """List all available skills."""
    return get_skill_registry().list_skills()
