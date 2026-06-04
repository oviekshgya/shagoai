import re
import subprocess
from pathlib import Path
from typing import Any, Callable


ConfirmCallback = Callable[[str, dict[str, Any]], bool]
NotifyCallback = Callable[[str, dict[str, Any]], None]


def preview_text(text: str, limit: int = 20_000) -> str:
    if len(text) <= limit:
        return text

    omitted = len(text) - limit
    return text[:limit] + f"\n\n[TRUNCATED: {omitted} chars omitted]"


def is_dangerous_command(command: str) -> bool:
    blocked_patterns = [
        r"\brm\s+-rf\b",
        r"\bdd\s+",
        r"\bmkfs\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r":\(\)\{",
        r">\s*/dev/sd",
        r"\bchmod\s+-R\s+777\b",
        r"\bchown\s+-R\b",
        r"\bpasswd\b",
        r"\buserdel\b",
        r"\bgroupdel\b",
    ]

    return any(re.search(pattern, command) for pattern in blocked_patterns)


class LocalTools:
    def __init__(
        self,
        root: Path,
        get_guard: Callable[[], str] | None = None,
        confirm_callback: ConfirmCallback | None = None,
        notify_callback: NotifyCallback | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.get_guard = get_guard or (lambda: "approval required")
        self.confirm_callback = confirm_callback
        self.notify_callback = notify_callback
        self.last_write_backup: tuple[Path, str | None] | None = None

    def set_root(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def should_confirm(self, action: str, payload: dict[str, Any]) -> bool:
        guard = self.get_guard()

        if guard == "approval required":
            return True

        # Mode /auto: command non-destruktif boleh jalan,
        # tapi write_file tetap harus approval.
        if action == "write_file":
            return True

        if action == "run_cmd":
            command = str(payload.get("command", ""))
            return is_dangerous_command(command)

        return False

    def confirm(self, action: str, payload: dict[str, Any]) -> bool:
        if not self.should_confirm(action, payload):
            return True

        if self.confirm_callback:
            return self.confirm_callback(action, payload)

        answer = input(f"Confirm {action}? [y/N] ")
        return answer.strip().lower() == "y"

    def notify(self, event: str, payload: dict[str, Any]) -> None:
        if self.notify_callback:
            self.notify_callback(event, payload)

    def resolve_workspace_path(self, path: str) -> Path:
        raw = Path(path).expanduser()

        if not raw.is_absolute():
            raw = self.root / raw

        resolved = raw.resolve()

        # Semua file operation dibatasi agar tidak keluar dari workspace.
        if resolved != self.root and self.root not in resolved.parents:
            raise ValueError(f"path keluar dari workspace: {path}")

        return resolved

    def list_dir(self, path: str = ".") -> str:
        """List files and folders inside the workspace.

        Args:
            path: Relative directory path to list.
        """
        try:
            target = self.resolve_workspace_path(path)

            if not target.exists():
                return f"ERROR: path not found: {path}"

            if not target.is_dir():
                return f"ERROR: not a directory: {path}"

            rows = []

            for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                suffix = "/" if item.is_dir() else ""
                rows.append(f"{item.name}{suffix}")

            return "\n".join(rows) if rows else "(empty directory)"
        except Exception as exc:
            return f"ERROR: {exc}"

    def read_file(self, path: str) -> str:
        """Read a text file from the workspace.

        Args:
            path: Relative file path to read.
        """
        try:
            target = self.resolve_workspace_path(path)

            if not target.exists():
                return f"ERROR: file not found: {path}"

            if not target.is_file():
                return f"ERROR: not a file: {path}"

            data = target.read_text(encoding="utf-8", errors="replace")
            return preview_text(data)
        except Exception as exc:
            return f"ERROR: {exc}"

    def write_file(self, path: str, content: str) -> str:
        """Write content to a file inside the workspace.

        Args:
            path: Relative file path to write.
            content: New file content.
        """
        try:
            target = self.resolve_workspace_path(path)

            payload = {
                "path": path,
                "chars": len(content),
                "action": "write",
            }

            self.notify("proposed_change", payload)

            if not self.confirm("write_file", payload):
                return "CANCELLED by user"

            before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else None

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

            self.last_write_backup = (target, before)

            return f"OK: wrote {path}"
        except Exception as exc:
            return f"ERROR: {exc}"

    def run_cmd(self, command: str) -> str:
        """Run a shell command from the workspace root.

        Args:
            command: Shell command to execute.
        """
        if is_dangerous_command(command):
            return "BLOCKED: dangerous command"

        payload = {
            "cwd": str(self.root),
            "command": command,
        }

        self.notify("command_request", payload)

        if not self.confirm("run_cmd", payload):
            return "CANCELLED by user"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=60,
            )

            return (
                f"EXIT_CODE: {result.returncode}\n\n"
                f"STDOUT:\n{preview_text(result.stdout, 12_000)}\n\n"
                f"STDERR:\n{preview_text(result.stderr, 12_000)}"
            )
        except subprocess.TimeoutExpired:
            return "ERROR: command timeout after 60 seconds"
        except Exception as exc:
            return f"ERROR: {exc}"

    def search_text(self, pattern: str, path: str = ".") -> str:
        """Search text in files inside the workspace.

        Args:
            pattern: Regex or plain text pattern to search.
            path: Relative path to search from.
        """
        try:
            root = self.resolve_workspace_path(path)

            if root.is_file():
                files = [root]
            else:
                ignored = {
                    ".git",
                    "node_modules",
                    ".venv",
                    "venv",
                    "__pycache__",
                    "dist",
                    "build",
                    ".next",
                    "target",
                    "vendor",
                }

                files = [
                    p for p in root.rglob("*")
                    if p.is_file() and not any(part in ignored for part in p.parts)
                ]

            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error:
                regex = re.compile(re.escape(pattern), re.IGNORECASE)

            hits = []

            for file_path in files[:3000]:
                try:
                    text = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                for idx, line in enumerate(text.splitlines(), start=1):
                    if regex.search(line):
                        rel = file_path.relative_to(self.root)
                        hits.append(f"{rel}:{idx}: {line.strip()}")

                        if len(hits) >= 100:
                            return "\n".join(hits) + "\n\n[TRUNCATED: max 100 hits]"

            return "\n".join(hits) if hits else "No matches"
        except Exception as exc:
            return f"ERROR: {exc}"

    def git_status(self) -> str:
        """Show git status for the workspace."""
        return self.run_cmd("git status --short")

    def git_diff(self) -> str:
        """Show git diff for the workspace."""
        return self.run_cmd("git diff -- .")

    def undo_last_write(self) -> str:
        if not self.last_write_backup:
            return "No write backup available."

        path, before = self.last_write_backup

        if before is None:
            if path.exists():
                path.unlink()

            self.last_write_backup = None
            return f"removed file: {path.relative_to(self.root)}"

        path.write_text(before, encoding="utf-8")
        self.last_write_backup = None
        return f"restored file: {path.relative_to(self.root)}"

    def tool_map(self) -> dict[str, Callable[..., str]]:
        return {
            "list_dir": self.list_dir,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_cmd": self.run_cmd,
            "search_text": self.search_text,
            "git_status": self.git_status,
            "git_diff": self.git_diff,
        }

    def call_tool(self, name: str, args: dict[str, Any]) -> str:
        tools = self.tool_map()

        if name not in tools:
            return f"ERROR: unknown tool {name}"

        return tools[name](**args)

    def tool_specs(self) -> list[dict[str, Any]]:
        """
        JSON schema untuk Shago AI Server nanti.
        Format ini sengaja generic agar server bisa meneruskan ke model internal apa pun.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "description": "List files and folders inside the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative directory path to list.",
                                "default": ".",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a text file from the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative file path to read.",
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file inside the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative file path to write.",
                            },
                            "content": {
                                "type": "string",
                                "description": "New file content.",
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_cmd",
                    "description": "Run a shell command from the workspace root.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute.",
                            }
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_text",
                    "description": "Search text in files inside the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Regex or plain text pattern to search.",
                            },
                            "path": {
                                "type": "string",
                                "description": "Relative path to search from.",
                                "default": ".",
                            },
                        },
                        "required": ["pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_status",
                    "description": "Show git status for the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_diff",
                    "description": "Show git diff for the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
        ]