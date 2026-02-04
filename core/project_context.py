"""
Klix Core - Project Context Manager
Loads and manages KLIX.md project memory files for persistent project-specific context.
Inspired by Claude Code's CLAUDE.md pattern.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class KlixFile:
    """Represents a single KLIX.md file."""
    
    path: Path
    content: str
    scope: Literal["global", "directory", "parent"]
    
    @property
    def exists(self) -> bool:
        return self.path.exists()


@dataclass
class ProjectContext:
    """
    Manages project-specific context from KLIX.md files.
    
    KLIX.md files can exist at multiple levels:
    - Global: ~/.klix/KLIX.md (user preferences)
    - Project root: <project>/KLIX.md (project standards)
    - Directory: <project>/src/KLIX.md (local overrides)
    
    Files are loaded hierarchically and merged with later files
    taking precedence for conflicting sections.
    """
    
    project_root: Path
    klix_files: list[KlixFile] = field(default_factory=list)
    _merged_context: str = ""
    _last_load_time: float = 0.0
    
    # Standard KLIX.md filename (can be overridden)
    KLIX_FILENAME = "KLIX.md"
    
    def __post_init__(self) -> None:
        """Load KLIX.md files on initialization."""
        self.reload()
    
    def reload(self) -> None:
        """Reload all KLIX.md files."""
        self.klix_files = []
        self._merged_context = ""
        
        # 1. Load global user config
        global_path = Path.home() / ".klix" / self.KLIX_FILENAME
        if global_path.exists():
            self._load_file(global_path, "global")
        
        # 2. Load project root config
        project_klix = self.project_root / self.KLIX_FILENAME
        if project_klix.exists():
            self._load_file(project_klix, "directory")
        
        # 3. Search for parent directory configs
        # (e.g., src/KLIX.md applies to all files in src/)
        self._load_parent_configs()
        
        # 4. Merge all loaded files
        self._merge_context()
        
        import time
        self._last_load_time = time.time()
        
        logger.info(f"Loaded {len(self.klix_files)} KLIX.md file(s)")
    
    def _load_file(self, path: Path, scope: Literal["global", "directory", "parent"]) -> None:
        """Load a single KLIX.md file."""
        try:
            content = path.read_text(encoding="utf-8")
            self.klix_files.append(KlixFile(path=path, content=content, scope=scope))
            logger.debug(f"Loaded {scope} KLIX.md from {path}")
        except Exception as e:
            logger.warning(f"Failed to load KLIX.md from {path}: {e}")
    
    def _load_parent_configs(self) -> None:
        """Load KLIX.md files from parent directories within the project."""
        # Walk up from project root looking for subdirectories with KLIX.md
        # This enables per-package or per-module configurations
        try:
            for subdir in self.project_root.rglob(self.KLIX_FILENAME):
                if subdir != self.project_root / self.KLIX_FILENAME:
                    # Skip already-loaded project root
                    if not any(f.path == subdir for f in self.klix_files):
                        self._load_file(subdir, "parent")
        except Exception as e:
            logger.warning(f"Error scanning for KLIX.md files: {e}")
    
    def _merge_context(self) -> None:
        """Merge all KLIX.md content into a single context string."""
        if not self.klix_files:
            self._merged_context = ""
            return
        
        sections: list[str] = []
        
        for klix_file in self.klix_files:
            scope_label = {
                "global": "User Preferences",
                "directory": "Project Context",
                "parent": f"Local Context ({klix_file.path.parent.name})"
            }.get(klix_file.scope, "Context")
            
            sections.append(f"## {scope_label}\n\n{klix_file.content}")
        
        self._merged_context = "\n\n---\n\n".join(sections)
    
    def get_context(self) -> str:
        """Get the merged context from all KLIX.md files."""
        return self._merged_context
    
    def get_context_for_directory(self, directory: Path) -> str:
        """
        Get context relevant to a specific directory.
        Includes global + project + any parent directory configs.
        """
        relevant: list[str] = []
        
        for klix_file in self.klix_files:
            # Always include global and project root
            if klix_file.scope in ("global", "directory"):
                relevant.append(klix_file.content)
            # Include parent configs only if they're ancestors of the target
            elif klix_file.scope == "parent":
                try:
                    directory.relative_to(klix_file.path.parent)
                    relevant.append(klix_file.content)
                except ValueError:
                    pass  # Not an ancestor
        
        return "\n\n".join(relevant)
    
    def has_context(self) -> bool:
        """Check if any KLIX.md files were loaded."""
        return len(self.klix_files) > 0 and bool(self._merged_context.strip())
    
    def get_system_prompt_injection(self) -> str:
        """
        Generate a system prompt section from KLIX.md content.
        This is injected into the agent's system prompt.
        """
        if not self.has_context():
            return ""
        
        return f"""
## Project Context (from KLIX.md)

The following information has been loaded from KLIX.md files in this project.
Follow these instructions and use this context to guide your responses.

{self._merged_context}

---
"""
    
    def create_template(self, path: Path | None = None) -> Path:
        """
        Create a template KLIX.md file.
        
        Args:
            path: Where to create the file. Defaults to project root.
            
        Returns:
            Path to the created file.
        """
        target = path or (self.project_root / self.KLIX_FILENAME)
        
        template = '''# KLIX.md - Project Context for Klix AI Assistant

This file provides context and instructions for Klix when working on this project.
Klix will automatically read this file and follow the guidelines below.

## Project Overview

<!-- Describe your project here -->
- Name: 
- Description: 
- Primary Language: 

## Architecture

<!-- Describe the project structure and key components -->

## Coding Standards

<!-- Define your coding conventions -->
- Use descriptive variable names
- Add docstrings to all public functions
- Follow PEP 8 for Python code

## Common Commands

<!-- Commands Klix should know about -->
```bash
# Run tests
pytest tests/ -v

# Start development server
python main.py
```

## Important Files

<!-- Key files Klix should be aware of -->
- `main.py` - Entry point
- `config.py` - Configuration management

## Preferences

<!-- Your preferences for Klix's behavior -->
- Always ask before deleting files
- Use type hints in Python code
- Prefer async/await for I/O operations

## Notes

<!-- Any additional context or notes -->
'''
        
        target.write_text(template, encoding="utf-8")
        logger.info(f"Created KLIX.md template at {target}")
        
        # Reload to include the new file
        self.reload()
        
        return target
    
    def get_summary(self) -> str:
        """Get a summary of loaded KLIX.md files."""
        if not self.klix_files:
            return "No KLIX.md files found."
        
        lines = [f"Loaded {len(self.klix_files)} KLIX.md file(s):"]
        for kf in self.klix_files:
            size = len(kf.content)
            lines.append(f"  - [{kf.scope}] {kf.path} ({size} chars)")
        
        return "\n".join(lines)


# Global project context instance (lazy-loaded)
_project_context: ProjectContext | None = None


def get_project_context(project_root: Path | None = None) -> ProjectContext:
    """
    Get or create the global ProjectContext instance.
    
    Args:
        project_root: Project root path. Uses current directory if not specified.
    """
    global _project_context
    
    if project_root is None:
        from config import get_config
        project_root = get_config().project_root
    
    if _project_context is None or _project_context.project_root != project_root:
        _project_context = ProjectContext(project_root=project_root)
    
    return _project_context


def reload_project_context() -> ProjectContext:
    """Force reload of project context."""
    global _project_context
    if _project_context:
        _project_context.reload()
    return get_project_context()
