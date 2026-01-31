"""
Klix Code - Reasoning Logger
Captures and stores agent reasoning traces, tool calls, and LLM responses.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config, get_config
from logging_config import get_logger

logger = get_logger(__name__)

class ReasoningLogger:
    """
    Handles logging of agent 'reasoning traces' - the sequence of thoughts,
    tool calls, and results for each session.
    """
    
    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or get_config()
        self.traces_dir = self.config.traces_dir
        self.is_enabled = self.config.enable_traces
        
        self.session_id: Optional[str] = None
        self.current_trace_file: Optional[Path] = None
        self.events: List[Dict[str, Any]] = []
        
        if self.is_enabled:
            self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure the traces directory exists."""
        try:
            self.traces_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create traces directory {self.traces_dir}: {e}")
            self.is_enabled = False

    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start a new reasoning trace session."""
        if not self.is_enabled:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"trace_{timestamp}"
        self.current_trace_file = self.traces_dir / f"{self.session_id}.json"
        self.events = []
        
        # Log session start event
        start_event = {
            "event": "session_start",
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "config": {
                "model": self.config.current_model,
                "provider": self.config.default_provider.value,
            }
        }
        self.log_event(start_event)
        logger.debug(f"Started reasoning trace session: {self.session_id}")

    def log_event(self, event_data: Dict[str, Any]) -> None:
        """Log a specific event to the current trace."""
        if not self.is_enabled or not self.current_trace_file:
            return
            
        if "timestamp" not in event_data:
            event_data["timestamp"] = datetime.now().isoformat()
            
        self.events.append(event_data)
        self._flush()

    def log_user_message(self, content: str) -> None:
        """Convenience method to log a user message."""
        self.log_event({
            "event": "user_message",
            "content": content
        })

    def log_llm_response(self, content: str, tool_calls: List[Dict[str, Any]], usage: Optional[Dict[str, Any]] = None) -> None:
        """Convenience method to log an LLM response."""
        self.log_event({
            "event": "llm_response",
            "content": content,
            "tool_calls": tool_calls,
            "usage": usage or {}
        })

    def log_tool_result(self, tool_name: str, arguments: Dict[str, Any], result: str) -> None:
        """Convenience method to log a tool result."""
        self.log_event({
            "event": "tool_result",
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result
        })

    def _flush(self) -> None:
        """Flush the current trace to disk."""
        if not self.current_trace_file:
            return
            
        try:
            with open(self.current_trace_file, "w", encoding="utf-8") as f:
                json.dump({
                    "session_id": self.session_id,
                    "total_events": len(self.events),
                    "events": self.events
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to flush reasoning trace to {self.current_trace_file}: {e}")

_logger_instance: Optional[ReasoningLogger] = None

def get_reasoning_logger(config: Optional[Config] = None) -> ReasoningLogger:
    """Get or create the global ReasoningLogger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ReasoningLogger(config)
    return _logger_instance
