import argparse
import os
import re
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ollama import chat, list as list_models
from ollama import ResponseError

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.prompt import Confirm

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style


console = Console()


SHAGO_LOGO = r"""
███████╗██╗  ██╗ █████╗  ██████╗  ██████╗
██╔════╝██║  ██║██╔══██╗██╔════╝ ██╔═══██╗
███████╗███████║███████║██║  ███╗██║   ██║
╚════██║██╔══██║██╔══██║██║   ██║██║   ██║
███████║██║  ██║██║  ██║╚██████╔╝╚██████╔╝
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝
"""


@dataclass
class AgentState:
    model: str = ""
    root: Path = field(default_factory=lambda: Path.cwd().resolve())
    mode: str = "plan → act → verify"
    guard: str = "approval required"
    max_turns: int = 8
    last_write_backup: tuple[Path, str | None] | None = None


STATE = AgentState()


def shorten_path(path: Path) -> str:
    home = Path.home()
    try:
        return "~/" + str(path.relative_to(home))
    except ValueError:
        return str(path)


def extract_model_name(model_obj: Any) -> str | None:
    if isinstance(model_obj, dict):
        return model_obj.get("model") or model_obj.get("name")

    return getattr(model_obj, "model", None) or getattr(model_obj, "name", None)


def get_installed_models() -> list[str]:
    names: list[str] = []

    try:
        response = list_models()
        models = getattr(response, "models", None)

        if models is None and isinstance(response, dict):
            models = response.get("models", [])

        for item in models or []:
            name = extract_model_name(item)
            if name:
                names.append(name)
    except Exception:
        pass

    if names:
        return names

    # Fallback kalau Python SDK gagal membaca list model.
    try:
        result = subprocess.run(
            ["ollama", "ls"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()[1:]
            for line in lines:
                parts = line.split()
                if parts:
                    names.append(parts[0])
    except Exception:
        pass

    return names


def choose_default_model() -> str:
    env_model = os.getenv("SHAGO_MODEL") or os.getenv("OLLAMA_MODEL")
    if env_model:
        return env_model

    models = get_installed_models()
    if models:
        return models[0]

    return "gemma4:31b-cloud"


def render_banner() -> None:
    body = (
        f"[bold cyan]{SHAGO_LOGO}[/bold cyan]\n"
        "[bold white]local autonomous coding interface[/bold white]\n\n"
        f"[cyan]AI[/cyan]        [white]{STATE.model}[/white]\n"
        f"[cyan]ROOT[/cyan]      [white]{shorten_path(STATE.root)}[/white]\n"
        f"[cyan]MODE[/cyan]      [white]{STATE.mode}[/white]\n"
        f"[cyan]GUARD[/cyan]     [white]{STATE.guard}[/white]"
    )

    console.print(
        Panel(
            body,
            border_style="cyan",
            title="[bold cyan]SHAGO//AGENT[/bold cyan]",
            subtitle="[dim]type /help for commands[/dim]",
            expand=False,
        )
    )


def print_help() -> None:
    table = Table(title="SHAGO commands", border_style="cyan")
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    rows = [
        ("/help", "lihat bantuan"),
        ("/models", "lihat model yang tersedia"),
        ("/model", "lihat model aktif"),
        ("/model <name>", "ganti model aktif"),
        ("/workspace", "lihat root workspace"),
        ("/workspace <path>", "ganti root workspace"),
        ("/safe", "aktifkan approval untuk write/run"),
        ("/auto", "mode lebih longgar"),
        ("/diff", "lihat git diff"),
        ("/undo", "rollback write_file terakhir"),
        ("/clear", "bersihkan layar"),
        ("/exit", "keluar"),
    ]

    for cmd, desc in rows:
        table.add_row(cmd, desc)

    console.print(table)


def resolve_workspace_path(path: str) -> Path:
    raw = Path(path).expanduser()

    if not raw.is_absolute():
        raw = STATE.root / raw

    resolved = raw.resolve()

    # File tools dibatasi agar tidak keluar dari workspace.
    if resolved != STATE.root and STATE.root not in resolved.parents:
        raise ValueError(f"path keluar dari workspace: {path}")

    return resolved


def preview_text(text: str, limit: int = 20_000) -> str:
    if len(text) <= limit:
        return text

    return text[:limit] + f"\n\n[TRUNCATED: {len(text) - limit} chars omitted]"


def list_dir(path: str = ".") -> str:
    """List files and folders inside the workspace.

    Args:
        path: Relative directory path to list.
    """
    try:
        target = resolve_workspace_path(path)

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


def read_file(path: str) -> str:
    """Read a text file from the workspace.

    Args:
        path: Relative file path to read.
    """
    try:
        target = resolve_workspace_path(path)

        if not target.exists():
            return f"ERROR: file not found: {path}"

        if not target.is_file():
            return f"ERROR: not a file: {path}"

        data = target.read_text(encoding="utf-8", errors="replace")
        return preview_text(data)
    except Exception as exc:
        return f"ERROR: {exc}"


def write_file(path: str, content: str) -> str:
    """Write content to a file inside the workspace.

    Args:
        path: Relative file path to write.
        content: New file content.
    """
    try:
        target = resolve_workspace_path(path)
        before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else None

        console.print(
            Panel(
                f"[cyan]file[/cyan]   {path}\n"
                f"[cyan]action[/cyan] write\n"
                f"[cyan]chars[/cyan]  {len(content)}",
                title="[bold yellow]proposed change[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

        if STATE.guard == "approval required":
            if not Confirm.ask("Apply this change?", default=False):
                return "CANCELLED by user"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        STATE.last_write_backup = (target, before)

        return f"OK: wrote {path}"
    except Exception as exc:
        return f"ERROR: {exc}"


def run_cmd(command: str) -> str:
    """Run a shell command from the workspace root.

    Args:
        command: Shell command to execute.
    """
    blocked_patterns = [
        r"\brm\s+-rf\b",
        r"\bdd\s+",
        r"\bmkfs\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r":\(\)\{",
        r">\s*/dev/sd",
        r"\bchmod\s+-R\s+777\b",
    ]

    if any(re.search(pattern, command) for pattern in blocked_patterns):
        return "BLOCKED: dangerous command"

    console.print(
        Panel(
            f"[cyan]cwd[/cyan]     {shorten_path(STATE.root)}\n"
            f"[cyan]command[/cyan] {command}",
            title="[bold yellow]command request[/bold yellow]",
            border_style="yellow",
            expand=False,
        )
    )

    if STATE.guard == "approval required":
        if not Confirm.ask("Run this command?", default=False):
            return "CANCELLED by user"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(STATE.root),
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


def search_text(pattern: str, path: str = ".") -> str:
    """Search text in files inside the workspace.

    Args:
        pattern: Regex or plain text pattern to search.
        path: Relative path to search from.
    """
    try:
        root = resolve_workspace_path(path)

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
            }

            files = [
                p for p in root.rglob("*")
                if p.is_file() and not any(part in ignored for part in p.parts)
            ]

        regex = re.compile(pattern, re.IGNORECASE)
        hits = []

        for file_path in files[:2000]:
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for idx, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    rel = file_path.relative_to(STATE.root)
                    hits.append(f"{rel}:{idx}: {line.strip()}")

                    if len(hits) >= 80:
                        return "\n".join(hits) + "\n\n[TRUNCATED: max 80 hits]"

        return "\n".join(hits) if hits else "No matches"
    except Exception as exc:
        return f"ERROR: {exc}"


def git_status() -> str:
    """Show git status for the workspace."""
    return run_cmd("git status --short")


def git_diff() -> str:
    """Show git diff for the workspace."""
    return run_cmd("git diff -- .")


TOOLS = {
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,
    "run_cmd": run_cmd,
    "search_text": search_text,
    "git_status": git_status,
    "git_diff": git_diff,
}


SYSTEM_PROMPT = """
Kamu adalah Shago, agentic coding CLI lokal.

Aturan kerja:
- Jawab dalam Bahasa Indonesia.
- Jangan menebak isi file. Jika butuh isi file, gunakan read_file.
- Untuk memahami project, mulai dari list_dir, lalu baca file penting.
- Gunakan run_cmd untuk test/build hanya jika memang perlu.
- Jangan membuat perubahan tanpa alasan jelas.
- Untuk perubahan file, gunakan write_file.
- Setelah menjalankan tool, jelaskan hasilnya secara ringkas.
- Jika task kompleks, buat plan singkat lalu lanjut eksekusi.
- Prioritaskan solusi praktis, langsung bisa dijalankan.
"""


def get_response_message(response: Any) -> Any:
    if isinstance(response, dict):
        return response.get("message", {})

    return getattr(response, "message", {})


def get_message_content(message: Any) -> str:
    if isinstance(message, dict):
        return message.get("content") or ""

    return getattr(message, "content", None) or ""


def get_tool_calls(message: Any) -> list[Any]:
    if isinstance(message, dict):
        return message.get("tool_calls") or []

    return getattr(message, "tool_calls", None) or []


def parse_tool_call(call: Any) -> tuple[str | None, dict[str, Any]]:
    if isinstance(call, dict):
        fn = call.get("function", {})
        name = fn.get("name")
        args = fn.get("arguments") or {}
    else:
        fn = getattr(call, "function", None)
        name = getattr(fn, "name", None)
        args = getattr(fn, "arguments", {}) if fn else {}

    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}

    return name, dict(args or {})


def render_tool_call(name: str, args: dict[str, Any]) -> None:
    safe_args = json.dumps(args, indent=2, ensure_ascii=False)

    console.print(
        Panel(
            Syntax(safe_args, "json", theme="monokai", word_wrap=True),
            title=f"[bold cyan]tool::{name}[/bold cyan]",
            border_style="cyan",
            expand=False,
        )
    )


def append_assistant_message(messages: list[dict[str, Any]], message: Any) -> None:
    if isinstance(message, dict):
        messages.append(message)
        return

    item = {
        "role": getattr(message, "role", "assistant"),
        "content": getattr(message, "content", "") or "",
    }

    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        item["tool_calls"] = tool_calls

    messages.append(item)


def run_agent(user_prompt: str) -> None:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for _ in range(STATE.max_turns):
        try:
            with console.status("[cyan]● thinking[/cyan]", spinner="dots"):
                response = chat(
                    model=STATE.model,
                    messages=messages,
                    tools=list(TOOLS.values()),
                    options={
                        "temperature": 0.2,
                        "num_ctx": 8192,
                    },
                )
        except ResponseError as exc:
            if getattr(exc, "status_code", None) == 404:
                console.print(
                    Panel(
                        f"Model [bold red]{STATE.model}[/bold red] tidak ditemukan.\n\n"
                        "Jalankan [cyan]/models[/cyan] untuk lihat model tersedia, "
                        "lalu pakai [cyan]/model <nama-model>[/cyan].\n\n"
                        "Contoh:\n"
                        "[cyan]/model gemma4:31b-cloud[/cyan]",
                        title="[bold red]model error[/bold red]",
                        border_style="red",
                    )
                )
            else:
                console.print(f"[red]ERROR:[/red] {exc}")

            return
        except Exception as exc:
            console.print(f"[red]ERROR:[/red] {exc}")
            return

        message = get_response_message(response)
        tool_calls = get_tool_calls(message)

        if not tool_calls:
            content = get_message_content(message).strip()

            if content:
                console.print(Markdown(content))
            else:
                console.print("[dim]No response.[/dim]")

            return

        append_assistant_message(messages, message)

        for call in tool_calls:
            name, args = parse_tool_call(call)

            if not name or name not in TOOLS:
                result = f"ERROR: unknown tool {name}"
            else:
                render_tool_call(name, args)

                try:
                    result = TOOLS[name](**args)
                except TypeError as exc:
                    result = f"ERROR: invalid tool arguments: {exc}"
                except Exception as exc:
                    result = f"ERROR: tool failed: {exc}"

            console.print(
                Panel(
                    preview_text(str(result), 8000),
                    title="[bold green]tool result[/bold green]",
                    border_style="green",
                    expand=False,
                )
            )

            messages.append({
                "role": "tool",
                "tool_name": name or "unknown",
                "content": str(result),
            })

    console.print("[yellow]Agent berhenti karena mencapai batas turn. Coba pecah task jadi lebih kecil.[/yellow]")


def handle_command(command: str) -> bool:
    raw = command.strip()

    if raw in {"/exit", "/quit"}:
        return False

    if raw == "/clear":
        console.clear()
        render_banner()
        return True

    if raw == "/help":
        print_help()
        return True

    if raw == "/models":
        models = get_installed_models()

        table = Table(title="Available models", border_style="cyan")
        table.add_column("Model", style="white")
        table.add_column("Active", style="cyan")

        for model in models:
            table.add_row(model, "yes" if model == STATE.model else "")

        if not models:
            table.add_row("(none)", "")

        console.print(table)
        return True

    if raw == "/model":
        console.print(f"[cyan]current model:[/cyan] {STATE.model}")
        return True

    if raw.startswith("/model "):
        name = raw.split(" ", 1)[1].strip()

        if not name:
            console.print("[red]Usage:[/red] /model <name>")
            return True

        STATE.model = name
        console.print(f"[green]model set:[/green] {STATE.model}")
        return True

    if raw == "/workspace":
        console.print(f"[cyan]workspace:[/cyan] {shorten_path(STATE.root)}")
        return True

    if raw.startswith("/workspace "):
        path = Path(raw.split(" ", 1)[1].strip()).expanduser().resolve()

        if not path.exists() or not path.is_dir():
            console.print(f"[red]Invalid directory:[/red] {path}")
            return True

        STATE.root = path
        console.print(f"[green]workspace set:[/green] {shorten_path(STATE.root)}")
        return True

    if raw == "/safe":
        STATE.guard = "approval required"
        console.print("[green]guard set:[/green] approval required")
        return True

    if raw == "/auto":
        STATE.guard = "confirm destructive"
        console.print("[yellow]guard set:[/yellow] confirm destructive")
        return True

    if raw == "/diff":
        console.print(Panel(git_diff(), title="[cyan]git diff[/cyan]", border_style="cyan"))
        return True

    if raw == "/undo":
        if not STATE.last_write_backup:
            console.print("[yellow]No write backup available.[/yellow]")
            return True

        path, before = STATE.last_write_backup

        if before is None:
            if path.exists():
                path.unlink()

            console.print(f"[green]removed file:[/green] {path.relative_to(STATE.root)}")
        else:
            path.write_text(before, encoding="utf-8")
            console.print(f"[green]restored file:[/green] {path.relative_to(STATE.root)}")

        STATE.last_write_backup = None
        return True

    console.print(f"[red]Unknown command:[/red] {raw}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="shagoai",
        description="SHAGO local agentic coding CLI",
    )

    parser.add_argument(
        "-C",
        "--workspace",
        default=None,
        help="Set workspace directory. Default: current directory.",
    )

    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Set model name.",
    )

    args = parser.parse_args()

    STATE.root = Path(args.workspace).expanduser().resolve() if args.workspace else Path.cwd().resolve()
    STATE.model = args.model or choose_default_model()

    console.clear()
    render_banner()
    console.print("[dim]Tip: Use [cyan]/plan[/cyan] in your prompt to preview actions before execution.[/dim]\n")

    history_path = str(Path.home() / ".shago_agent_history")

    style = Style.from_dict({
        "prompt": "ansicyan bold",
    })

    session = PromptSession(
        history=FileHistory(history_path),
        style=style,
    )

    while True:
        try:
            user_input = session.prompt([("class:prompt", "shago ❯ ")])
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]bye[/dim]")
            break

        if not user_input.strip():
            continue

        if user_input.strip().startswith("/"):
            should_continue = handle_command(user_input)

            if not should_continue:
                console.print("[dim]bye[/dim]")
                break

            continue

        run_agent(user_input)

if __name__ == "__main__":
    main()