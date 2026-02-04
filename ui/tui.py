"""
Klix code - TUI Interface
Sophisticated terminal UI using the rich library, matching the "Claude Code" look exactly.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich import box
from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# prompt_toolkit for advanced input handling with key bindings
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style as PTStyle
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from config import Config, get_config


# ============================================================================
# ASCII Art (Simple rectangle with eyes - matching user's image)
# ============================================================================

ROBOT_ASCII = """\
████████████████
█              █
█   ██    ██   █
█              █
████████████████"""


@dataclass
class RecentActivity:
    """Represents a recent activity item."""
    timestamp: datetime
    action: str
    details: str = ""


@dataclass
class TUIState:
    """Manages the state of the TUI."""
    recent_activities: list[RecentActivity] = field(default_factory=list)
    is_thinking: bool = False
    current_model: str = ""
    token_usage: dict[str, int] = field(default_factory=dict)
    
    def add_activity(self, action: str, details: str = "") -> None:
        """Add a new activity to the recent list."""
        self.recent_activities.insert(0, RecentActivity(
            timestamp=datetime.now(),
            action=action,
            details=details,
        ))
        # Keep only last 5 activities
        self.recent_activities = self.recent_activities[:5]


class GeminiCodeTUI:
    """
    Main TUI class for Klix code.
    Matches the Claude Code interface exactly.
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or get_config()
        self.console = Console(force_terminal=True, color_system="truecolor")
        self.state = TUIState(current_model=self.config.current_model)
        
        # Approval mode callback (set by runtime)
        self.on_toggle_mode: callable = None
        
        # Set up prompt_toolkit session if available
        self._setup_prompt_session()
        
        # Define styles based on theme
        self._setup_styles()
    
    def _setup_prompt_session(self) -> None:
        """Set up prompt_toolkit with custom key bindings."""
        if not PROMPT_TOOLKIT_AVAILABLE:
            self.prompt_session = None
            return
        
        # Track current mode for live display
        self._current_mode_display = "suggest"
        
        # Store reference to self for use in callbacks
        tui_self = self
        
        # Create key bindings
        kb = KeyBindings()
        
        # Helper function for mode toggle
        def do_toggle_mode():
            """Toggle approval mode and return the new mode name."""
            if tui_self.on_toggle_mode:
                return tui_self.on_toggle_mode()
            return None
        
        # Primary Binding: Ctrl+T
        @kb.add('c-t', eager=True)
        def handle_ctrl_t(event):
            mode_name = do_toggle_mode()
            if mode_name:
                tui_self._current_mode_display = mode_name
                event.app.output.write(f"\r\033[K")
                event.app.output.write(f"  \u2714 Mode: \033[1;38;5;208m{mode_name}\033[0m\r\n")
                event.app.output.flush()
        
        # Create prompt session
        self.prompt_session = PromptSession(
            key_bindings=kb,
            style=PTStyle.from_dict({
                'prompt': '#ff8c00 bold',
            }),
        )
        
        # Store toggle function for use in render_input_prompt
        self._do_toggle_mode = do_toggle_mode
    
    def _setup_styles(self) -> None:
        """Set up custom styles based on theme configuration."""
        theme = self.config.theme
        
        self.styles = {
            "accent": Style(color=theme.accent_color, bold=False),
            "accent_bold": Style(color=theme.accent_color, bold=True),
            "text": Style(color=theme.text_color),
            "dim": Style(color=theme.dim_text_color),
            "success": Style(color=theme.success_color),
            "warning": Style(color=theme.warning_color),
            "error": Style(color=theme.error_color),
            "info": Style(color=theme.info_color),
            "border": Style(color=theme.accent_color),
        }
    
    def render_header(self) -> Panel:
        """
        Render the main header panel matching Claude Code layout.
        """
        theme = self.config.theme
        user_name = self.config.user_name
        cwd = str(self.config.project_root)
        
        # Build the content as a table with two columns
        main_table = Table.grid(padding=(0, 2), expand=True)
        main_table.add_column(justify="center", ratio=1)  # Left: welcome + art
        main_table.add_column(justify="left", ratio=2)    # Right: tips + activity
        
        # === LEFT COLUMN ===
        left_content = []
        
        # Welcome text
        left_content.append(Text(f"Welcome back {user_name}!", style=self.styles["text"]))
        left_content.append(Text(""))
        
        # ASCII art in orange
        for line in ROBOT_ASCII.split("\n"):
            left_content.append(Text(line, style=self.styles["accent"]))
        
        left_content.append(Text(""))
        
        # Model info
        model_text = Text()
        model_name = self.config.current_model.replace("-", " ").replace(".", " ").title()
        model_text.append(model_name, style=self.styles["text"])
        model_text.append(" · ", style=self.styles["dim"])
        model_text.append("API Usage Billing", style=self.styles["text"])
        model_text.append(" · ", style=self.styles["dim"])
        model_text.append(f"{user_name}'s", style=self.styles["text"])
        left_content.append(model_text)
        
        # Org info
        left_content.append(Text(self.config.org_name, style=self.styles["text"]))
        
        # Path
        left_content.append(Text(cwd, style=self.styles["dim"]))
        
        left_group = Group(*left_content)
        
        # === RIGHT COLUMN ===
        right_content = []
        
        # Tips header
        right_content.append(Text("Tips for getting started", style=self.styles["accent_bold"]))
        
        # Tips
        tip1 = Text("Run ", style=self.styles["text"])
        tip1.append("/init", style=self.styles["accent"])
        tip1.append(" to create a GEMINI.md file with instructions for Gemini", style=self.styles["text"])
        right_content.append(tip1)
        
        tip2 = Text("Note: ", style=self.styles["dim"])
        tip2.append("You have launched gemini in your home directory. For the best experience, launch it in a pro...", style=self.styles["dim"])
        right_content.append(tip2)
        
        right_content.append(Text(""))
        
        # Recent activity header
        right_content.append(Text("Recent activity", style=self.styles["accent_bold"]))
        
        # Activity list
        if not self.state.recent_activities:
            right_content.append(Text("No recent activity", style=self.styles["dim"]))
        else:
            for activity in self.state.recent_activities[:3]:
                activity_text = Text(activity.action, style=self.styles["text"])
                if activity.details:
                    activity_text.append(f" {activity.details}", style=self.styles["dim"])
                right_content.append(activity_text)
        
        right_group = Group(*right_content)
        
        # Add to table
        main_table.add_row(
            Align.center(left_group, vertical="middle"),
            right_group,
        )
        
        # Create panel with rounded border and title at top-left
        header_panel = Panel(
            main_table,
            border_style=theme.accent_color,
            box=box.ROUNDED,
            title=f"[{theme.accent_color}]Klix v{self.VERSION}[/]",
            title_align="left",
            padding=(1, 2),
        )
        
        return header_panel
    
    def render_input_prompt(self, placeholder: str = 'Try "fix lint errors"') -> str:
        """
        Render the input prompt at the bottom.
        Returns the user's input.
        Supports Ctrl+T to toggle approval mode.
        """
        self.console.print()
        
        try:
            # Use prompt_toolkit if available (supports key bindings)
            if PROMPT_TOOLKIT_AVAILABLE and self.prompt_session:
                # Get current mode for display with color coding
                mode_hint = ""
                if self.on_toggle_mode:
                    from core.approval import get_approval_manager
                    mgr = get_approval_manager()
                    mode_name = mgr.mode.value
                    # Color-code modes: suggest=blue, auto_edit=yellow, full_auto=orange, yolo=red
                    mode_colors = {
                        "suggest": "#5599ff",
                        "auto_edit": "#ffcc00",
                        "full_auto": "#ff8c00", 
                        "yolo": "#ff3333",
                    }
                    mode_color = mode_colors.get(mode_name, "#888888")
                    mode_hint = f' <style fg="{mode_color}" bold="true">[{mode_name}]</style>'
                
                user_input = self.prompt_session.prompt(
                    HTML(f'<style fg="#ff8c00" bold="true">&gt;</style>{mode_hint} '),
                    placeholder=HTML(f'<style fg="#666666">{placeholder}</style>')
                )
                
                # Post-process: Check if ^T (ASCII 20) was typed - fallback for Windows
                if '\x14' in user_input:
                    # Toggle mode for each ^T found
                    toggle_count = user_input.count('\x14')
                    for _ in range(toggle_count):
                        if hasattr(self, '_do_toggle_mode') and self._do_toggle_mode:
                            new_mode = self._do_toggle_mode()
                            if new_mode:
                                self._current_mode_display = new_mode
                                self.console.print(f"  [#ff8c00]\u2714 Mode: {new_mode}[/]")
                    # Remove ^T from input
                    user_input = user_input.replace('\x14', '')
                
                return user_input.strip()

            else:
                # Fallback to rich Prompt
                prompt_text = Text()
                prompt_text.append("> ", style=self.styles["accent"])
                
                user_input = Prompt.ask(
                    prompt_text,
                    console=self.console,
                    default="",
                )
                return user_input.strip()
        except (KeyboardInterrupt, EOFError):
            return ""
    
    def render_footer(self, notice: str = "") -> None:
        """Render the footer with shortcuts and notice."""
        theme = self.config.theme
        
        # Create footer table
        footer_table = Table.grid(expand=True, padding=(0, 1))
        footer_table.add_column(justify="left", width=20)
        footer_table.add_column(justify="left")
        
        # Left side: shortcuts hint with mode cycling visual
        shortcuts = Text()
        shortcuts.append("? ", style=self.styles["accent"])
        shortcuts.append("help ", style=self.styles["dim"])
        shortcuts.append("Ctrl+T ", style=self.styles["accent"])
        shortcuts.append("↻ mode", style=self.styles["dim"])
        
        # Right side: notice message with current mode
        if notice:
            notice_text = Text(notice, style=self.styles["accent"])
        else:
            # Get current mode for display
            mode_info = ""
            if self.on_toggle_mode:
                try:
                    from core.approval import get_approval_manager
                    mgr = get_approval_manager()
                    mode_info = f" | Mode: {mgr.mode.value}"
                except Exception:
                    pass
            notice_text = Text(
                f"'/help' for commands, Ctrl+T cycles modes{mode_info}",
                style=self.styles["dim"]
            )
        
        footer_table.add_row(shortcuts, notice_text)
        self.console.print(footer_table)
    
    def render_thinking_spinner(self) -> Progress:
        """Create a thinking spinner with orange dots."""
        theme = self.config.theme
        
        progress = Progress(
            SpinnerColumn(
                spinner_name="dots",
                style=theme.accent_color,
            ),
            TextColumn(
                "[{task.description}]",
                style=theme.accent_color,
            ),
            console=self.console,
            transient=True,
        )
        
        return progress
    
    async def show_thinking(self, message: str = "Thinking...") -> None:
        """Display thinking indicator."""
        self.state.is_thinking = True
        progress = self.render_thinking_spinner()
        
        with progress:
            task = progress.add_task(message, total=None)
            while self.state.is_thinking:
                await asyncio.sleep(0.1)
    
    def stop_thinking(self) -> None:
        """Stop the thinking indicator."""
        self.state.is_thinking = False
    
    def render_message(
        self,
        content: str,
        role: str = "assistant",
        title: str | None = None,
    ) -> None:
        """
        Render a chat message with Markdown support.
        """
        theme = self.config.theme
        
        # Determine styling based on role
        if role == "user":
            border_color = theme.info_color
            icon = "👤"
            default_title = "You"
        elif role == "assistant":
            border_color = theme.accent_color
            icon = "🤖"
            default_title = "Klix code"
        elif role == "tool":
            border_color = theme.success_color
            icon = "🔧"
            default_title = "Tool Result"
        else:
            border_color = theme.dim_text_color
            icon = "ℹ️"
            default_title = "System"
        
        # Try to parse JSON content
        import json
        try:
            # Check if it looks like JSON first to avoid unnecessary parsing
            stripped = content.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                data = json.loads(stripped)
                if isinstance(data, dict):
                    # Check for common message fields
                    if "message" in data:
                        content = data["message"]
                        # If there's a name, we could use it, but for now just use the message
                    elif "response" in data:
                        content = data["response"]
        except json.JSONDecodeError:
            pass  # Not JSON, use original content
        
        # Parse Markdown
        md_content = Markdown(content)
        
        # Create panel
        panel = Panel(
            md_content,
            border_style=border_color,
            title=f"{icon} {title or default_title}",
            title_align="left",
            padding=(1, 2),
        )
        
        self.console.print(panel)
    
    def render_code(
        self,
        code: str,
        language: str = "python",
        title: str | None = None,
    ) -> None:
        """Render syntax-highlighted code."""
        theme = self.config.theme
        
        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        
        panel = Panel(
            syntax,
            border_style=theme.accent_color,
            title=title or f"📝 {language.title()}",
            title_align="left",
            padding=(0, 1),
        )
        
        self.console.print(panel)
    
    def render_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: str | None = None,
    ) -> None:
        """Render a tool call and its result."""
        theme = self.config.theme
        
        # Tool call info
        args_text = Text()
        args_text.append(f"🔧 {tool_name}", style=self.styles["accent"])
        args_text.append("(", style=self.styles["dim"])
        
        arg_parts = []
        for key, value in arguments.items():
            arg_parts.append(f"{key}={repr(value)}")
        args_text.append(", ".join(arg_parts), style=self.styles["text"])
        args_text.append(")", style=self.styles["dim"])
        
        self.console.print(args_text)
        
        if result is not None:
            result_panel = Panel(
                result[:500] + "..." if len(result) > 500 else result,
                border_style=theme.success_color,
                title="Result",
                title_align="left",
                padding=(0, 1),
            )
            self.console.print(result_panel)
    
    def render_error(self, message: str, title: str = "Error") -> None:
        """Render an error message."""
        theme = self.config.theme
        
        error_panel = Panel(
            Text(message, style=self.styles["error"]),
            border_style=theme.error_color,
            title=f"❌ {title}",
            title_align="left",
            padding=(0, 1),
        )
        
        self.console.print(error_panel)
    
    def render_success(self, message: str, title: str = "Success") -> None:
        """Render a success message."""
        theme = self.config.theme
        
        success_panel = Panel(
            Text(message, style=self.styles["success"]),
            border_style=theme.success_color,
            title=f"✅ {title}",
            title_align="left",
            padding=(0, 1),
        )
        
        self.console.print(success_panel)
    
    def render_info(self, message: str, title: str = "Info") -> None:
        """Render an info message."""
        theme = self.config.theme
        
        info_panel = Panel(
            Text(message, style=self.styles["info"]),
            border_style=theme.info_color,
            title=f"ℹ️ {title}",
            title_align="left",
            padding=(0, 1),
        )
        
        self.console.print(info_panel)
    
    def clear(self) -> None:
        """Clear the console."""
        self.console.clear()
    
    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to console."""
        self.console.print(*args, **kwargs)
    
    async def stream_response(self, content_generator) -> str:
        """
        Stream a response to the console.
        """
        theme = self.config.theme
        full_content = ""
        
        with Live(console=self.console, refresh_per_second=10) as live:
            async for chunk in content_generator:
                full_content += chunk
                md = Markdown(full_content)
                panel = Panel(
                    md,
                    border_style=theme.accent_color,
                    title="🤖 Klix code",
                    title_align="left",
                    padding=(1, 2),
                )
                live.update(panel)
        
        return full_content


def create_tui(config: Config | None = None) -> GeminiCodeTUI:
    """Factory function to create a TUI instance."""
    return GeminiCodeTUI(config)


# ============================================================================
# Standalone Demo
# ============================================================================

if __name__ == "__main__":
    # Demo the TUI components
    tui = GeminiCodeTUI()
    
    # Show header
    tui.console.print(tui.render_header())
    
    # Show input placeholder
    prompt_hint = Text()
    prompt_hint.append("> ", style=tui.styles["accent"])
    prompt_hint.append('Try "fix lint errors"', style=tui.styles["dim"])
    tui.console.print()
    tui.console.print(prompt_hint)
    tui.console.print()
    
    # Show footer
    tui.render_footer()
