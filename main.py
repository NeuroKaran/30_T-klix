"""
Klix - Main Entry Point (The Body)
Manages the Runtime, TUI, and Slash Commands.
Connects the user to the Agent (The Soul).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path to ensure local modules are discoverable
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
from dataclasses import dataclass
from typing import Any

import typer

from config import Config, ModelProvider, get_config
from logging_config import setup_logging, get_logger
from core.agent import KlixAgent
from core.tools import get_tool_descriptions, get_project_structure
from ui.tui import GeminiCodeTUI, create_tui
from llm_client import get_client  # Needed for switching providers in runtime

logger = get_logger(__name__)


# ============================================================================
# Slash Command Handler
# ============================================================================

@dataclass
class SlashCommand:
    """Represents a slash command."""
    name: str
    description: str
    handler: Any  # Callable


class SlashCommandHandler:
    """Handles slash commands for the Runtime."""
    
    def __init__(self, runtime: KlixRuntime) -> None:
        self.runtime = runtime
        self._commands: dict[str, SlashCommand] = {}
        self._register_default_commands()
    
    def _register_default_commands(self) -> None:
        """Register the default slash commands."""
        self.register("init", "Initialize project context", self._cmd_init)
        self.register("config", "View or change configuration", self._cmd_config)
        self.register("clear", "Clear conversation context", self._cmd_clear)
        self.register("help", "Show available commands", self._cmd_help)
        self.register("tools", "Show available tools", self._cmd_tools)
        self.register("model", "Switch model (gemini/ollama)", self._cmd_model)
        self.register("mode", "Switch approval mode (suggest/auto/full/yolo)", self._cmd_mode)
        self.register("plan", "Toggle planning mode or view current plan", self._cmd_plan)
        self.register("skill", "Manage skills (list/activate/deactivate)", self._cmd_skill)
        self.register("status", "Show current status", self._cmd_status)
        self.register("memory", "View and search memories", self._cmd_memory)
        self.register("forget", "Delete a memory", self._cmd_forget)
        self.register("remember", "Manually add a memory", self._cmd_remember)
        # Session persistence commands
        self.register("save", "Save current session", self._cmd_save)
        self.register("load", "Load a saved session", self._cmd_load)
        self.register("sessions", "List saved sessions", self._cmd_sessions)
        self.register("quit", "Exit Klix", self._cmd_quit)
        self.register("exit", "Exit Klix", self._cmd_quit)
    
    def register(self, name: str, description: str, handler: Any) -> None:
        """Register a new slash command."""
        self._commands[name] = SlashCommand(name, description, handler)
    
    def is_command(self, text: str) -> bool:
        """Check if text is a slash command."""
        return text.strip().startswith("/")
    
    async def execute(self, text: str) -> bool:
        """Execute a slash command. Returns True if handled."""
        if not self.is_command(text):
            return False
        
        parts = text.strip()[1:].split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd_name not in self._commands:
            self.runtime.tui.render_error(
                f"Unknown command: /{cmd_name}\nUse /help to see available commands."
            )
            return True
        
        command = self._commands[cmd_name]
        try:
            await command.handler(args)
        except Exception as e:
            self.runtime.tui.render_error(f"Error executing /{cmd_name}: {e}")
        return True
    
    # --- Command Implementations ---
    
    async def _cmd_init(self, args: str) -> None:
        """Initialize project context and reload KLIX.md files."""
        from pathlib import Path
        project_path = Path(args.strip()) if args.strip() else Path.cwd()
        
        if not project_path.exists():
            self.runtime.tui.render_error(f"Path does not exist: {project_path}")
            return
        
        self.runtime.config.project_root = project_path.resolve()
        
        # Reload project context from KLIX.md files
        context_summary = self.runtime.agent.reload_project_context()
        
        # Get project structure
        structure = get_project_structure(max_depth=2)
        
        # Inject project structure into session
        from llm_client import Message
        context_message = Message(
            role="system",
            content=f"Project initialized at: {project_path.resolve()}\n\nStructure:\n{structure}"
        )
        self.runtime.agent.session.add_message(context_message)
        
        # Report what was loaded
        has_klix = self.runtime.agent.project_context.has_context()
        
        if has_klix:
            self.runtime.tui.render_success(
                f"✓ Project initialized at: {project_path.resolve()}\n"
                f"✓ {context_summary}"
            )
        else:
            self.runtime.tui.render_success(
                f"✓ Project initialized at: {project_path.resolve()}\n"
                f"ℹ No KLIX.md found. Create one with /init --create-template"
            )
        
        # Handle --create-template flag
        if "--create-template" in args:
            template_path = self.runtime.agent.project_context.create_template()
            self.runtime.tui.render_success(f"✓ Created KLIX.md template at: {template_path}")
        
        self.runtime.tui.state.add_activity("Initialized project", str(project_path))

    async def _cmd_config(self, args: str) -> None:
        """Show or update configuration."""
        config = self.runtime.config
        if not args:
            info = [
                f"**Provider:** {config.default_provider.value}",
                f"**Model:** {config.current_model}",
                f"**User:** {config.user_name}",
                f"**Org:** {config.org_name}",
                f"**Project Root:** {config.project_root}",
            ]
            self.runtime.tui.render_info("\n".join(info), title="Configuration")
        else:
            parts = args.split("=", 1)
            if len(parts) != 2:
                self.runtime.tui.render_error("Usage: /config KEY=VALUE")
                return
            key, value = parts[0].strip(), parts[1].strip()
            
            if key == "model":
                config.switch_model(value)
                # Re-init client in agent
                self.runtime.agent.client = get_client(config=config)
                self.runtime.tui.render_success(f"Switched model to: {value}")
            elif key == "provider":
                try:
                    config.switch_provider(value)
                    self.runtime.agent.client = get_client(config=config)
                    self.runtime.tui.render_success(f"Switched provider to: {value}")
                except ValueError:
                    self.runtime.tui.render_error(f"Invalid provider: {value}")
            else:
                self.runtime.tui.render_error(f"Unknown config key: {key}")

    async def _cmd_clear(self, args: str) -> None:
        """Clear conversation context."""
        self.runtime.agent.session.clear()
        self.runtime.tui.clear()
        self.runtime.tui.console.print(self.runtime.tui.render_header())
        self.runtime.tui.render_success("Conversation context cleared.")
        self.runtime.tui.state.add_activity("Cleared context")

    async def _cmd_help(self, args: str) -> None:
        """Show help."""
        help_lines = ["**Available Commands:**\n"]
        for cmd in sorted(self._commands.values(), key=lambda c: c.name):
            help_lines.append(f"• **/{cmd.name}** - {cmd.description}")
        self.runtime.tui.render_info("\n".join(help_lines), title="Help")

    async def _cmd_tools(self, args: str) -> None:
        """Show tools."""
        tools_desc = get_tool_descriptions()
        self.runtime.tui.render_info(tools_desc, title="Available Tools")

    async def _cmd_model(self, args: str) -> None:
        """Switch models."""
        # Reuse logic from config command for simplicity or expand here
        self.runtime.tui.render_info("Use /config model=NAME to switch models.")

    async def _cmd_mode(self, args: str) -> None:
        """Switch approval mode."""
        from core.approval import ApprovalMode
        
        mode_arg = args.strip().lower()
        
        if not mode_arg:
            # Show current mode
            current_mode = self.runtime.agent.approval_manager.mode
            description = self.runtime.agent.approval_manager.get_mode_description()
            
            lines = [
                f"**Current Mode:** {current_mode.value}",
                f"{description}",
                "",
                "**Available Modes:**",
                "• **suggest** - All actions require approval",
                "• **auto** (auto_edit) - Low-risk auto-approved, others need approval",
                "• **full** (full_auto) - Low/medium-risk auto-approved",
                "• **yolo** - All auto-approved (dangerous!)",
                "",
                "Usage: `/mode <mode_name>`"
            ]
            self.runtime.tui.render_info("\n".join(lines), title="Approval Mode")
            return
        
        # Map shortcuts
        mode_map = {
            "suggest": "suggest",
            "auto": "auto_edit",
            "auto_edit": "auto_edit",
            "full": "full_auto",
            "full_auto": "full_auto",
            "yolo": "yolo",
        }
        
        if mode_arg not in mode_map:
            self.runtime.tui.render_error(
                f"Unknown mode: {mode_arg}\n"
                f"Valid modes: suggest, auto, full, yolo"
            )
            return
        
        try:
            self.runtime.agent.approval_manager.set_mode(mode_map[mode_arg])
            new_mode = self.runtime.agent.approval_manager.mode
            description = self.runtime.agent.approval_manager.get_mode_description()
            
            self.runtime.tui.render_success(
                f"✓ Switched to {new_mode.value} mode\n"
                f"{description}"
            )
            self.runtime.tui.state.add_activity("Changed mode", new_mode.value)
        except ValueError as e:
            self.runtime.tui.render_error(f"Invalid mode: {e}")

    async def _cmd_plan(self, args: str) -> None:
        """Toggle planning mode or view current plan."""
        from core.planning import get_planning_manager, enable_planning_mode, disable_planning_mode
        
        manager = get_planning_manager()
        action = args.strip().lower()
        
        if not action:
            # Show current state
            if manager.enabled:
                if manager.current_plan:
                    plan_md = manager.current_plan.to_markdown()
                    self.runtime.tui.render_info(plan_md, title="Current Plan")
                else:
                    self.runtime.tui.render_info(
                        "Planning mode is **enabled** but no plan created yet.\n"
                        "The agent will create a plan before taking actions."
                    )
            else:
                self.runtime.tui.render_info(
                    "Planning mode is **disabled**.\n\n"
                    "**Commands:**\n"
                    "• `/plan on` - Enable planning mode\n"
                    "• `/plan off` - Disable planning mode\n"
                    "• `/plan new <goal>` - Start a new plan\n"
                    "• `/plan cancel` - Cancel current plan",
                    title="Plan Mode"
                )
            return
        
        if action == "on":
            enable_planning_mode()
            self.runtime.tui.render_success(
                "✓ Planning mode enabled\n"
                "The agent will now create a plan before taking actions."
            )
            self.runtime.tui.state.add_activity("Enabled planning mode")
        
        elif action == "off":
            disable_planning_mode()
            self.runtime.tui.render_success("✓ Planning mode disabled")
            self.runtime.tui.state.add_activity("Disabled planning mode")
        
        elif action.startswith("new "):
            goal = args[4:].strip()
            if not goal:
                self.runtime.tui.render_error("Usage: /plan new <goal description>")
                return
            plan = enable_planning_mode(goal)
            self.runtime.tui.render_success(
                f"✓ Started new plan: {goal}\n"
                "Planning mode is now active."
            )
            self.runtime.tui.state.add_activity("Started plan", goal[:50])
        
        elif action == "cancel":
            if manager.current_plan:
                manager.cancel_plan()
                self.runtime.tui.render_success("✓ Plan cancelled")
                self.runtime.tui.state.add_activity("Cancelled plan")
            else:
                self.runtime.tui.render_info("No active plan to cancel.")
        
        elif action == "history":
            if not manager.plans_history:
                self.runtime.tui.render_info("No plan history.")
                return
            
            lines = ["**Plan History:**\n"]
            for p in manager.plans_history[-5:]:  # Last 5
                completed, total = p.progress
                status_icon = "✅" if p.is_complete else "📋"
                lines.append(f"{status_icon} {p.goal[:40]}... ({completed}/{total} steps)")
            self.runtime.tui.render_info("\n".join(lines), title="Plan History")
        
        else:
            self.runtime.tui.render_error(
                f"Unknown plan action: {action}\n"
                "Valid actions: on, off, new <goal>, cancel, history"
            )

    async def _cmd_skill(self, args: str) -> None:
        """Manage skills."""
        from core.skills import get_skill_registry, activate_skill, deactivate_skill
        
        registry = get_skill_registry()
        parts = args.strip().split(maxsplit=1)
        action = parts[0].lower() if parts else ""
        skill_name = parts[1] if len(parts) > 1 else ""
        
        if not action or action == "list":
            # List all skills
            skills = registry.list_skills()
            if not skills:
                self.runtime.tui.render_info("No skills available.")
                return
            
            lines = ["**Available Skills:**\n"]
            for s in skills:
                status = "✅ Active" if s["active"] else "⬜ Inactive"
                lines.append(f"{status} **{s['name']}** - {s['description']}")
                if s["tags"]:
                    lines.append(f"   Tags: {', '.join(s['tags'])}")
            
            lines.extend([
                "",
                "**Commands:**",
                "• `/skill list` - List all skills",
                "• `/skill activate <name>` - Activate a skill",
                "• `/skill deactivate <name>` - Deactivate a skill",
            ])
            self.runtime.tui.render_info("\n".join(lines), title="Skills")
        
        elif action == "activate":
            if not skill_name:
                self.runtime.tui.render_error("Usage: /skill activate <skill_name>")
                return
            
            if activate_skill(skill_name):
                self.runtime.tui.render_success(f"✓ Activated skill: {skill_name}")
                self.runtime.tui.state.add_activity("Activated skill", skill_name)
            else:
                self.runtime.tui.render_error(f"Failed to activate skill: {skill_name}")
        
        elif action == "deactivate":
            if not skill_name:
                self.runtime.tui.render_error("Usage: /skill deactivate <skill_name>")
                return
            
            if deactivate_skill(skill_name):
                self.runtime.tui.render_success(f"✓ Deactivated skill: {skill_name}")
                self.runtime.tui.state.add_activity("Deactivated skill", skill_name)
            else:
                self.runtime.tui.render_error(f"Skill not active: {skill_name}")
        
        else:
            self.runtime.tui.render_error(
                f"Unknown skill action: {action}\n"
                "Valid actions: list, activate, deactivate"
            )

    async def _cmd_status(self, args: str) -> None:
        """Show status."""
        session_summary = self.runtime.agent.session.get_context_summary()
        mem_stats = self.runtime.agent.memory_service.get_stats()
        mem_status = f"{mem_stats.get('total_memories', 0)} memories" if mem_stats.get("enabled") else "Disabled"
        
        info = [
            f"**Model:** {self.runtime.config.current_model}",
            f"**Context:** {session_summary}",
            f"**Memory:** {mem_status}",
        ]
        self.runtime.tui.render_info("\n".join(info), title="Status")

    async def _cmd_memory(self, args: str) -> None:
        """Search memories."""
        service = self.runtime.agent.memory_service
        if not service.is_enabled:
            msg = getattr(service, "init_error", None) or "Memory service disabled."
            self.runtime.tui.render_error(msg)
            return
        
        if args.strip().startswith("search "):
            query = args.strip()[7:]
            memories = service.search(query, limit=10)
            title = f"Search: {query}"
        else:
            memories = service.get_all(limit=20)
            title = "Recent Memories"
        
        if not memories:
            self.runtime.tui.render_info("No memories found.", title=title)
            return
            
        lines = []
        for mem in memories:
            icon = "🧠"  # Simplify icon for now
            lines.append(f"{icon} `{mem.id[:8]}` {mem.content[:100]}...")
        self.runtime.tui.render_info("\n".join(lines), title=title)

    async def _cmd_forget(self, args: str) -> None:
        """Forget memory."""
        # Simplified implementation for brevity
        self.runtime.tui.render_info("Use /forget <id> to delete.")

    async def _cmd_remember(self, args: str) -> None:
        """Remember text."""
        service = self.runtime.agent.memory_service
        if not service.is_enabled:
            msg = getattr(service, "init_error", None) or "Memory service disabled."
            self.runtime.tui.render_error(msg)
            return
        
        if service.add_text(args.strip()):
            self.runtime.tui.render_success(f"Remembered: {args.strip()}")
        else:
            self.runtime.tui.render_error("Failed to remember.")

    async def _cmd_save(self, args: str) -> None:
        """Save current session."""
        from pathlib import Path
        from core.session import Session
        
        # Use project root for sessions directory
        sessions_dir = self.runtime.config.project_root / ".klix_sessions"
        Session.sessions_dir = sessions_dir
        
        name = args.strip() if args.strip() else None
        
        try:
            filepath = self.runtime.agent.session.save(name=name, sessions_dir=sessions_dir)
            session_name = self.runtime.agent.session.name or self.runtime.agent.session.id[:8]
            self.runtime.tui.render_success(
                f"✓ Session saved: {session_name}\n"
                f"  Path: {filepath}"
            )
            self.runtime.tui.state.add_activity("Saved session", session_name)
        except Exception as e:
            self.runtime.tui.render_error(f"Failed to save session: {e}")

    async def _cmd_load(self, args: str) -> None:
        """Load a saved session."""
        from pathlib import Path
        from core.session import Session
        
        if not args.strip():
            self.runtime.tui.render_error("Usage: /load <session_name>")
            return
        
        sessions_dir = self.runtime.config.project_root / ".klix_sessions"
        
        try:
            loaded_session = Session.load(args.strip(), sessions_dir=sessions_dir)
            
            # Replace current session with loaded one
            self.runtime.agent.session = loaded_session
            
            # Reinitialize system message with current context
            self.runtime.agent._initialize_system_message()
            
            self.runtime.tui.render_success(
                f"✓ Session loaded: {loaded_session.name or loaded_session.id[:8]}\n"
                f"  Messages: {len(loaded_session.messages)}\n"
                f"  Created: {loaded_session.created_at.strftime('%Y-%m-%d %H:%M')}"
            )
            self.runtime.tui.state.add_activity("Loaded session", loaded_session.name or loaded_session.id[:8])
        except FileNotFoundError:
            self.runtime.tui.render_error(f"Session not found: {args.strip()}")
        except Exception as e:
            self.runtime.tui.render_error(f"Failed to load session: {e}")

    async def _cmd_sessions(self, args: str) -> None:
        """List saved sessions."""
        from core.session import Session
        
        sessions_dir = self.runtime.config.project_root / ".klix_sessions"
        sessions = Session.list_sessions(sessions_dir=sessions_dir)
        
        if not sessions:
            self.runtime.tui.render_info(
                "No saved sessions found.\n"
                "Use /save [name] to save the current session."
            )
            return
        
        lines = ["**Saved Sessions:**\n"]
        for s in sessions[:10]:  # Show max 10
            name = s.get("name", "")
            msg_count = s.get("message_count", 0)
            updated = s.get("updated_at", "")[:10]  # Just date
            lines.append(f"• **{name}** - {msg_count} messages (updated: {updated})")
        
        if len(sessions) > 10:
            lines.append(f"\n...and {len(sessions) - 10} more")
        
        lines.append("\nUse `/load <name>` to load a session.")
        self.runtime.tui.render_info("\n".join(lines), title="Sessions")

    async def _cmd_quit(self, args: str) -> None:
        """Exit."""
        self.runtime.tui.render_info("Goodbye!")
        self.runtime.running = False



# ============================================================================
# Runtime Loop (The Body)
# ============================================================================

class KlixRuntime:
    """
    Main runtime environment.
    Orchestrates the TUI and the Agent.
    """
    
    def __init__(self, config: Config | None = None, use_local: bool = False) -> None:
        self.config = config or get_config()
        if use_local:
            self.config.switch_provider(ModelProvider.OLLAMA)
            
        self.tui = create_tui(self.config)
        self.agent = KlixAgent(config=self.config)
        self.commands = SlashCommandHandler(self)
        self.running = False
        
        # Connect TUI mode toggle to agent approval manager
        self.tui.on_toggle_mode = self._toggle_approval_mode
    
    def _toggle_approval_mode(self) -> str:
        """
        Cycle through approval modes on Shift+Tab.
        Returns the new mode name for display.
        """
        from core.approval import ApprovalMode
        
        mode_order = [
            ApprovalMode.SUGGEST,
            ApprovalMode.AUTO_EDIT,
            ApprovalMode.FULL_AUTO,
            ApprovalMode.YOLO,
        ]
        
        current = self.agent.approval_manager.mode
        try:
            current_idx = mode_order.index(current)
            next_idx = (current_idx + 1) % len(mode_order)
        except ValueError:
            next_idx = 0
        
        new_mode = mode_order[next_idx]
        self.agent.approval_manager.set_mode(new_mode)
        self.tui.state.add_activity("Mode", new_mode.value)
        return new_mode.value
        
    async def cleanup(self) -> None:
        await self.agent.close()
        
    async def run(self) -> None:
        """Main loop."""
        self.running = True
        self.tui.clear()
        self.tui.console.print(self.tui.render_header())
        
        # Validation checks...
        
        while self.running:
            try:
                self.tui.render_footer()
                user_input = self.tui.render_input_prompt()
                
                if not user_input:
                    continue
                
                if await self.commands.execute(user_input):
                    continue
                
                # Render user message
                self.tui.render_message(user_input, role="user")
                
                # Chat with Agent (The Soul)
                # Consume events from the generator
                async for event in self.agent.step(user_input):
                    etype = event["type"]
                    data = event["data"]
                    
                    if etype == "thinking":
                        # If previously thinking, this updates the message mechanism in TUI requires logic
                        # Simplified: Just show thinking
                        asyncio.create_task(self.tui.show_thinking(data))
                        
                    elif etype == "response":
                        self.tui.stop_thinking()
                        await asyncio.sleep(0.1) # Clear spinner
                        self.tui.render_message(data, role="assistant")
                        
                    elif etype == "tool_call":
                        # Render tool call details
                        self.tui.stop_thinking() # Stop thinking to show tool
                        await asyncio.sleep(0.1)
                        self.tui.render_tool_call(data.get("name"), data.get("arguments", {}))
                        
                    elif etype == "tool_result":
                        # Render tool result 
                        # Note: TUI.render_tool_call can update? No, it's print based.
                        # We just print the result panel.
                        # TUI method signature: render_tool_call(name, args, result)
                        # We called it above with just args. Now we call it with result?
                        # It might duplicate print. TUI logic prints immediately.
                        # Let's just print the result panel.
                        # Actually render_tool_call logic checks if result is None.
                        # So we can call it again with result.
                        self.tui.render_tool_call(data["name"], {}, result=data["result"])
                        
                    elif etype == "error":
                        self.tui.stop_thinking()
                        self.tui.render_error(data)
                
                self.tui.stop_thinking()
                
            except KeyboardInterrupt:
                self.tui.render_info("Use /quit to exit.")
            except Exception as e:
                self.tui.render_error(f"Runtime Exception: {e}")
        
        await self.cleanup()


# ============================================================================
# CLI Entry Point
# ============================================================================

app = typer.Typer(
    name="klix-code",
    help="Klix code - AI-powered coding assistant",
    add_completion=False,
)

@app.command()
def main(
    local: bool = typer.Option(False, "--local", "-l", help="Use local Ollama models"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Start the Klix coding assistant."""
    setup_logging(verbose=verbose)
    
    # Initialize implementation
    runtime = KlixRuntime(use_local=local)
    
    try:
        asyncio.run(runtime.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")

def run_cli():
    """Entry point for the console script."""
    app()

if __name__ == "__main__":
    app()
