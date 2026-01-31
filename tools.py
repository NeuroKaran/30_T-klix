"""
Gemini Code - Tools Registry and Implementations
Decorator-based tool registry for file system operations and web search.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

# Try to import duckduckgo_search, fallback to stub if not available
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

from config import get_config
from logging_config import get_logger

logger = get_logger(__name__)


# Type variable for tool functions
F = TypeVar("F", bound=Callable[..., str])


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    """Represents a registered tool."""
    name: str
    description: str
    function: Callable[..., str]
    parameters: list[ToolParameter] = field(default_factory=list)
    
    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema format for LLM function calling."""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    
    def execute(self, **kwargs: Any) -> str:
        """Execute the tool with given arguments."""
        return self.function(**kwargs)


class ToolRegistry:
    """
    Registry for all available tools.
    Tools are registered using the @tool decorator.
    """
    
    _instance: ToolRegistry | None = None
    
    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance
    
    def __init__(self) -> None:
        if not hasattr(self, "_tools"):
            self._tools: dict[str, Tool] = {}
    
    def register(
        self,
        name: str,
        description: str,
        parameters: list[ToolParameter] | None = None,
    ) -> Callable[[F], F]:
        """
        Decorator to register a tool.
        
        Usage:
            @registry.register("tool_name", "Tool description", [params])
            def my_tool(arg1: str) -> str:
                return "result"
        """
        def decorator(func: F) -> F:
            tool = Tool(
                name=name,
                description=description,
                function=func,
                parameters=parameters or [],
            )
            self._tools[name] = tool
            
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> str:
                return func(*args, **kwargs)
            
            return wrapper  # type: ignore
        
        return decorator
    
    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def execute(self, name: str, **kwargs: Any) -> str:
        """Execute a tool by name."""
        logger.debug(f"Executing tool: {name} with args: {list(kwargs.keys())}")
        tool = self.get(name)
        if tool is None:
            logger.warning(f"Tool not found: {name}")
            return f"Error: Tool '{name}' not found."
        
        try:
            result = tool.execute(**kwargs)
            logger.debug(f"Tool {name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool '{name}' execution failed: {e}")
            return f"Error executing '{name}': {str(e)}"
    
    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def get_tools_for_llm(self) -> list[dict[str, Any]]:
        """Get tools in format suitable for LLM function calling."""
        from llm_client import ToolDefinition
        
        return [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.to_json_schema(),
                function=tool.function,
            )
            for tool in self._tools.values()
        ]
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


# Global registry instance
registry = ToolRegistry()


# ============================================================================
# Helper function for the decorator shorthand
# ============================================================================

def tool(
    name: str,
    description: str,
    parameters: list[ToolParameter] | None = None,
) -> Callable[[F], F]:
    """
    Shorthand decorator for registering tools.
    
    Usage:
        @tool("ls", "List files in a directory")
        def list_files(path: str = ".") -> str:
            ...
    """
    return registry.register(name, description, parameters)


# ============================================================================
# File System Tools
# ============================================================================

@tool(
    "ls",
    "List files and directories in the specified path. Returns a formatted list of contents.",
    [
        ToolParameter(
            name="path",
            type="string",
            description="The directory path to list. Defaults to current directory.",
            required=False,
            default=".",
        ),
        ToolParameter(
            name="show_hidden",
            type="boolean",
            description="Whether to show hidden files (starting with .)",
            required=False,
            default=False,
        ),
    ],
)
def list_files(path: str = ".", show_hidden: bool = False) -> str:
    """List files in a directory."""
    try:
        config = get_config()
        target_path = Path(path)
        
        # Make relative paths relative to project root
        if not target_path.is_absolute():
            target_path = config.project_root / target_path
        
        if not target_path.exists():
            return f"Error: Path '{path}' does not exist."
        
        if not target_path.is_dir():
            return f"Error: '{path}' is not a directory."
        
        entries = []
        for entry in sorted(target_path.iterdir()):
            # Skip hidden files unless requested
            if not show_hidden and entry.name.startswith("."):
                continue
            
            entry_type = "📁" if entry.is_dir() else "📄"
            size = ""
            if entry.is_file():
                size_bytes = entry.stat().st_size
                if size_bytes < 1024:
                    size = f" ({size_bytes}B)"
                elif size_bytes < 1024 * 1024:
                    size = f" ({size_bytes // 1024}KB)"
                else:
                    size = f" ({size_bytes // (1024 * 1024)}MB)"
            
            entries.append(f"{entry_type} {entry.name}{size}")
        
        if not entries:
            return f"Directory '{path}' is empty."
        
        result = f"Contents of '{target_path}':\n\n"
        result += "\n".join(entries)
        return result
    
    except PermissionError:
        return f"Error: Permission denied to access '{path}'."
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool(
    "read_file",
    "Read the contents of a file. Returns the file content as text.",
    [
        ToolParameter(
            name="filepath",
            type="string",
            description="The path to the file to read.",
            required=True,
        ),
        ToolParameter(
            name="start_line",
            type="integer",
            description="Starting line number (1-indexed). If not specified, reads from beginning.",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="end_line",
            type="integer",
            description="Ending line number (1-indexed, inclusive). If not specified, reads to end.",
            required=False,
            default=None,
        ),
    ],
)
def read_file(
    filepath: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read the contents of a file."""
    try:
        config = get_config()
        target_path = Path(filepath)
        
        # Make relative paths relative to project root
        if not target_path.is_absolute():
            target_path = config.project_root / target_path
        
        if not target_path.exists():
            return f"Error: File '{filepath}' does not exist."
        
        if not target_path.is_file():
            return f"Error: '{filepath}' is not a file."
        
        # Read the file
        content = target_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        
        # Apply line range if specified
        if start_line is not None or end_line is not None:
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            
            if start_idx < 0:
                start_idx = 0
            if end_idx > len(lines):
                end_idx = len(lines)
            
            lines = lines[start_idx:end_idx]
            
            # Add line numbers
            numbered_lines = []
            for i, line in enumerate(lines, start=start_idx + 1):
                numbered_lines.append(f"{i:4d} | {line.rstrip()}")
            content = "\n".join(numbered_lines)
        
        # Truncate if too long
        max_length = 10000
        if len(content) > max_length:
            content = content[:max_length] + f"\n\n... (truncated, {len(content)} total characters)"
        
        return f"File: {target_path}\n\n{content}"
    
    except UnicodeDecodeError:
        return f"Error: '{filepath}' appears to be a binary file and cannot be read as text."
    except PermissionError:
        return f"Error: Permission denied to read '{filepath}'."
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool(
    "write_file",
    "Create or overwrite a file with the specified content.",
    [
        ToolParameter(
            name="filepath",
            type="string",
            description="The path to the file to create/write.",
            required=True,
        ),
        ToolParameter(
            name="content",
            type="string",
            description="The content to write to the file.",
            required=True,
        ),
        ToolParameter(
            name="create_dirs",
            type="boolean",
            description="Whether to create parent directories if they don't exist.",
            required=False,
            default=True,
        ),
    ],
)
def write_file(
    filepath: str,
    content: str,
    create_dirs: bool = True,
) -> str:
    """Create or overwrite a file with content."""
    try:
        config = get_config()
        target_path = Path(filepath)
        
        # Make relative paths relative to project root
        if not target_path.is_absolute():
            target_path = config.project_root / target_path
        
        # Create parent directories if needed
        if create_dirs:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        elif not target_path.parent.exists():
            return f"Error: Parent directory '{target_path.parent}' does not exist."
        
        # Check if file exists (for messaging)
        file_existed = target_path.exists()
        
        # Write the file
        target_path.write_text(content, encoding="utf-8")
        
        action = "Updated" if file_existed else "Created"
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        
        return f"{action} file: {target_path}\nLines: {line_count}, Size: {len(content)} bytes"
    
    except PermissionError:
        return f"Error: Permission denied to write '{filepath}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool(
    "append_file",
    "Append content to an existing file. Creates the file if it doesn't exist.",
    [
        ToolParameter(
            name="filepath",
            type="string",
            description="The path to the file to append to.",
            required=True,
        ),
        ToolParameter(
            name="content",
            type="string",
            description="The content to append to the file.",
            required=True,
        ),
    ],
)
def append_file(filepath: str, content: str) -> str:
    """Append content to a file."""
    try:
        config = get_config()
        target_path = Path(filepath)
        
        if not target_path.is_absolute():
            target_path = config.project_root / target_path
        
        # Create parent directories if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists
        file_existed = target_path.exists()
        
        # Append to file
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(content)
        
        action = "Appended to" if file_existed else "Created"
        return f"{action} file: {target_path}\nAppended: {len(content)} bytes"
    
    except Exception as e:
        return f"Error appending to file: {str(e)}"


@tool(
    "delete_file",
    "Delete a file from the filesystem.",
    [
        ToolParameter(
            name="filepath",
            type="string",
            description="The path to the file to delete.",
            required=True,
        ),
    ],
)
def delete_file(filepath: str) -> str:
    """Delete a file."""
    try:
        config = get_config()
        target_path = Path(filepath)
        
        if not target_path.is_absolute():
            target_path = config.project_root / target_path
        
        if not target_path.exists():
            return f"Error: File '{filepath}' does not exist."
        
        if not target_path.is_file():
            return f"Error: '{filepath}' is not a file."
        
        target_path.unlink()
        return f"Deleted file: {target_path}"
    
    except PermissionError:
        return f"Error: Permission denied to delete '{filepath}'."
    except Exception as e:
        return f"Error deleting file: {str(e)}"


# ============================================================================
# Shell Command Tool
# ============================================================================

@tool(
    "run_command",
    "Execute a shell command and return the output. Use with caution.",
    [
        ToolParameter(
            name="command",
            type="string",
            description="The shell command to execute.",
            required=True,
        ),
        ToolParameter(
            name="cwd",
            type="string",
            description="Working directory for the command. Defaults to project root.",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Timeout in seconds. Defaults to 30.",
            required=False,
            default=30,
        ),
    ],
)
def run_command(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
) -> str:
    """Execute a shell command."""
    try:
        config = get_config()
        
        # Set working directory
        working_dir = Path(cwd) if cwd else config.project_root
        if not working_dir.is_absolute():
            working_dir = config.project_root / working_dir
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        output_parts = []
        
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")
        
        if result.returncode != 0:
            output_parts.append(f"Exit code: {result.returncode}")
        
        if not output_parts:
            return "Command executed successfully (no output)."
        
        return "\n\n".join(output_parts)
    
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"


# ============================================================================
# Web Search Tool
# ============================================================================

@tool(
    "web_search",
    "Search the web for information using DuckDuckGo.",
    [
        ToolParameter(
            name="query",
            type="string",
            description="The search query.",
            required=True,
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results to return. Defaults to 5.",
            required=False,
            default=5,
        ),
    ],
)
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    if not DDGS_AVAILABLE:
        return (
            "Error: Web search is not available. "
            "Install duckduckgo-search: pip install duckduckgo-search"
        )
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        if not results:
            return f"No results found for: {query}"
        
        output = [f"Search results for: {query}\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("href", result.get("link", "No URL"))
            snippet = result.get("body", result.get("snippet", "No description"))
            
            output.append(f"{i}. **{title}**")
            output.append(f"   URL: {url}")
            output.append(f"   {snippet}\n")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"Error searching the web: {str(e)}"


# Alias for common hallucination
@tool(
    "search_web",
    "Search the web for information (alias for web_search).",
    [
        ToolParameter(
            name="query",
            type="string",
            description="The search query.",
            required=True,
        ),
    ],
)
def search_web(query: str, max_results: int = 5) -> str:
    """Alias for web_search."""
    return web_search(query, max_results)


# ============================================================================
# Project Context Tools
# ============================================================================

@tool(
    "get_project_structure",
    "Get the project directory structure as a tree.",
    [
        ToolParameter(
            name="max_depth",
            type="integer",
            description="Maximum depth to traverse. Defaults to 3.",
            required=False,
            default=3,
        ),
        ToolParameter(
            name="include_hidden",
            type="boolean",
            description="Whether to include hidden files and directories.",
            required=False,
            default=False,
        ),
    ],
)
def get_project_structure(max_depth: int = 3, include_hidden: bool = False) -> str:
    """Get the project directory structure."""
    try:
        config = get_config()
        root = config.project_root
        
        # Common directories to skip
        skip_dirs = {
            "__pycache__", "node_modules", ".git", ".venv", "venv",
            "dist", "build", ".cache", ".pytest_cache", "htmlcov",
        }
        
        def build_tree(path: Path, prefix: str = "", depth: int = 0) -> list[str]:
            if depth >= max_depth:
                return []
            
            lines = []
            
            try:
                entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return [f"{prefix}[Permission denied]"]
            
            # Filter entries
            filtered = []
            for entry in entries:
                if not include_hidden and entry.name.startswith("."):
                    continue
                if entry.is_dir() and entry.name in skip_dirs:
                    continue
                filtered.append(entry)
            
            for i, entry in enumerate(filtered):
                is_last = i == len(filtered) - 1
                connector = "└── " if is_last else "├── "
                
                icon = "📁 " if entry.is_dir() else "📄 "
                lines.append(f"{prefix}{connector}{icon}{entry.name}")
                
                if entry.is_dir():
                    extension = "    " if is_last else "│   "
                    lines.extend(build_tree(entry, prefix + extension, depth + 1))
            
            return lines
        
        tree_lines = [f"📂 {root.name}/"]
        tree_lines.extend(build_tree(root))
        
        return "\n".join(tree_lines)
    
    except Exception as e:
        return f"Error building project structure: {str(e)}"


# ============================================================================
# OSINT Tools - Reconnaissance and Enumeration
# ============================================================================

# Try to import OSINT dependencies
try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

try:
    import requests as http_requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

import socket


@tool(
    "dns_lookup",
    "Perform DNS lookup for a domain. Returns DNS records of the specified type.",
    [
        ToolParameter(
            name="domain",
            type="string",
            description="The domain name to look up (e.g., example.com).",
            required=True,
        ),
        ToolParameter(
            name="record_type",
            type="string",
            description="DNS record type: A, AAAA, MX, NS, TXT, CNAME, SOA. Defaults to A.",
            required=False,
            default="A",
        ),
    ],
)
def dns_lookup(domain: str, record_type: str = "A") -> str:
    """Perform DNS lookup for a domain."""
    if not DNS_AVAILABLE:
        return (
            "Error: DNS lookup is not available. "
            "Install dnspython: pip install dnspython"
        )
    
    try:
        record_type = record_type.upper()
        valid_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR"]
        
        if record_type not in valid_types:
            return f"Error: Invalid record type '{record_type}'. Valid types: {', '.join(valid_types)}"
        
        resolver = dns.resolver.Resolver()
        resolver.timeout = 10
        resolver.lifetime = 10
        
        answers = resolver.resolve(domain, record_type)
        
        results = [f"DNS {record_type} records for {domain}:\n"]
        
        for rdata in answers:
            if record_type == "MX":
                results.append(f"  • Priority {rdata.preference}: {rdata.exchange}")
            elif record_type == "SOA":
                results.append(f"  • Primary NS: {rdata.mname}")
                results.append(f"  • Email: {rdata.rname}")
                results.append(f"  • Serial: {rdata.serial}")
            else:
                results.append(f"  • {rdata.to_text()}")
        
        return "\n".join(results)
    
    except dns.resolver.NXDOMAIN:
        return f"Error: Domain '{domain}' does not exist."
    except dns.resolver.NoAnswer:
        return f"No {record_type} records found for '{domain}'."
    except dns.resolver.Timeout:
        return f"Error: DNS query timed out for '{domain}'."
    except Exception as e:
        return f"Error performing DNS lookup: {str(e)}"


@tool(
    "whois_lookup",
    "Perform WHOIS lookup for a domain. Returns domain registration information.",
    [
        ToolParameter(
            name="domain",
            type="string",
            description="The domain name to look up (e.g., example.com).",
            required=True,
        ),
    ],
)
def whois_lookup(domain: str) -> str:
    """Perform WHOIS lookup for a domain."""
    if not WHOIS_AVAILABLE:
        return (
            "Error: WHOIS lookup is not available. "
            "Install python-whois: pip install python-whois"
        )
    
    try:
        w = whois.whois(domain)
        
        if not w or not w.domain_name:
            return f"No WHOIS data found for '{domain}'."
        
        results = [f"WHOIS information for {domain}:\n"]
        
        # Helper to format lists/strings
        def fmt(val):
            if isinstance(val, list):
                return ", ".join(str(v) for v in val[:5])  # Limit to 5 items
            return str(val) if val else "N/A"
        
        results.append(f"  **Domain:** {fmt(w.domain_name)}")
        results.append(f"  **Registrar:** {fmt(w.registrar)}")
        results.append(f"  **Creation Date:** {fmt(w.creation_date)}")
        results.append(f"  **Expiration Date:** {fmt(w.expiration_date)}")
        results.append(f"  **Updated Date:** {fmt(w.updated_date)}")
        results.append(f"  **Name Servers:** {fmt(w.name_servers)}")
        results.append(f"  **Status:** {fmt(w.status)}")
        
        if w.org:
            results.append(f"  **Organization:** {fmt(w.org)}")
        if w.country:
            results.append(f"  **Country:** {fmt(w.country)}")
        
        return "\n".join(results)
    
    except Exception as e:
        return f"Error performing WHOIS lookup: {str(e)}"


@tool(
    "port_scan",
    "Scan common ports on a target host. Use only on authorized targets.",
    [
        ToolParameter(
            name="target",
            type="string",
            description="The target hostname or IP address to scan.",
            required=True,
        ),
        ToolParameter(
            name="ports",
            type="string",
            description="Comma-separated list of ports to scan (e.g., '22,80,443'). Defaults to common ports.",
            required=False,
            default="",
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Connection timeout in seconds per port. Defaults to 2.",
            required=False,
            default=2,
        ),
    ],
)
def port_scan(target: str, ports: str = "", timeout: int = 2) -> str:
    """Scan ports on a target host."""
    try:
        # Default common ports if none specified
        if not ports:
            port_list = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
        else:
            try:
                port_list = [int(p.strip()) for p in ports.split(",") if p.strip()]
            except ValueError:
                return "Error: Invalid port format. Use comma-separated numbers (e.g., '22,80,443')."
        
        # Limit number of ports to prevent abuse
        if len(port_list) > 50:
            return "Error: Maximum 50 ports can be scanned at once."
        
        # Resolve hostname
        try:
            ip = socket.gethostbyname(target)
        except socket.gaierror:
            return f"Error: Cannot resolve hostname '{target}'."
        
        results = [f"Port scan results for {target} ({ip}):\n"]
        open_ports = []
        closed_ports = []
        
        for port in port_list:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    # Try to get service name
                    try:
                        service = socket.getservbyport(port)
                    except OSError:
                        service = "unknown"
                    open_ports.append(f"  ✅ Port {port} ({service}): OPEN")
                else:
                    closed_ports.append(port)
            except Exception:
                closed_ports.append(port)
        
        if open_ports:
            results.append("**Open Ports:**")
            results.extend(open_ports)
        else:
            results.append("No open ports found.")
        
        if closed_ports:
            results.append(f"\n**Closed/Filtered:** {len(closed_ports)} ports")
        
        return "\n".join(results)
    
    except Exception as e:
        return f"Error performing port scan: {str(e)}"


@tool(
    "http_headers",
    "Fetch HTTP response headers from a URL. Useful for server fingerprinting and security analysis.",
    [
        ToolParameter(
            name="url",
            type="string",
            description="The URL to fetch headers from (e.g., https://example.com).",
            required=True,
        ),
        ToolParameter(
            name="follow_redirects",
            type="boolean",
            description="Whether to follow redirects. Defaults to True.",
            required=False,
            default=True,
        ),
    ],
)
def http_headers(url: str, follow_redirects: bool = True) -> str:
    """Fetch HTTP headers from a URL."""
    if not REQUESTS_AVAILABLE:
        return (
            "Error: HTTP headers tool is not available. "
            "Install requests: pip install requests"
        )
    
    try:
        # Ensure URL has a scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        response = http_requests.head(
            url,
            allow_redirects=follow_redirects,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OSINT-Tool/1.0)"}
        )
        
        results = [f"HTTP Headers for {url}:\n"]
        results.append(f"  **Status:** {response.status_code} {response.reason}")
        results.append(f"  **Final URL:** {response.url}\n")
        
        # Security-relevant headers to highlight
        security_headers = [
            "Server", "X-Powered-By", "X-Frame-Options", "X-XSS-Protection",
            "X-Content-Type-Options", "Strict-Transport-Security",
            "Content-Security-Policy", "Access-Control-Allow-Origin"
        ]
        
        results.append("**Headers:**")
        for header, value in response.headers.items():
            # Truncate long values
            display_value = value[:100] + "..." if len(value) > 100 else value
            if header in security_headers:
                results.append(f"  🔒 **{header}:** {display_value}")
            else:
                results.append(f"  • {header}: {display_value}")
        
        return "\n".join(results)
    
    except http_requests.exceptions.SSLError:
        return f"Error: SSL certificate verification failed for '{url}'."
    except http_requests.exceptions.ConnectionError:
        return f"Error: Cannot connect to '{url}'."
    except http_requests.exceptions.Timeout:
        return f"Error: Request timed out for '{url}'."
    except Exception as e:
        return f"Error fetching HTTP headers: {str(e)}"


# ============================================================================
# Utility Functions
# ============================================================================

def get_tool_descriptions() -> str:
    """Get a formatted string of all tool descriptions."""
    tools = registry.list_tools()
    lines = ["Available tools:\n"]
    
    for tool in tools:
        lines.append(f"• **{tool.name}**: {tool.description}")
        for param in tool.parameters:
            req = " (required)" if param.required else ""
            lines.append(f"  - `{param.name}` ({param.type}){req}: {param.description}")
        lines.append("")
    
    return "\n".join(lines)


def execute_tool_call(tool_call: dict[str, Any]) -> str:
    """
    Execute a tool call from LLM response.
    
    Args:
        tool_call: Dictionary with 'name' and 'arguments' keys
    
    Returns:
        The tool execution result
    """
    name = tool_call.get("name", "")
    arguments = tool_call.get("arguments", {})
    
    # Handle string arguments (JSON)
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments for tool '{name}'"
    
    return registry.execute(name, **arguments)


# ============================================================================
# Module initialization
# ============================================================================

# Ensure all tools are registered by importing the module
__all__ = [
    "registry",
    "tool",
    "Tool",
    "ToolParameter",
    "ToolRegistry",
    "list_files",
    "read_file",
    "write_file",
    "append_file",
    "delete_file",
    "run_command",
    "web_search",
    "get_project_structure",
    "get_tool_descriptions",
    "execute_tool_call",
    # OSINT Tools
    "dns_lookup",
    "whois_lookup",
    "port_scan",
    "http_headers",
]
