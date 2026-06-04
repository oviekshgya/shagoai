from shagoai import __version__
import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from shagoai.client import ShagoClient, ShagoClientError
from shagoai.config import CONFIG_FILE, load_config, set_config_value
from shagoai.tools import LocalTools, preview_text


console = Console()


SHAGO_LOGO = r"""
███████╗██╗  ██╗ █████╗  ██████╗  ██████╗
██╔════╝██║  ██║██╔══██╗██╔════╝ ██╔═══██╗
███████╗███████║███████║██║  ███╗██║   ██║
╚════██║██╔══██║██╔══██║██║   ██║██║   ██║
███████║██║  ██║██║  ██║╚██████╔╝╚██████╔╝
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝
"""


SYSTEM_PROMPT = """
Kamu adalah Shago, agentic coding CLI

Aturan:
- Jawab dalam Bahasa Indonesia.
- Kamu berjalan sebagai coding agent di workspace user.
- Jangan menebak isi file. Kalau perlu tahu isi file, gunakan tool read_file.
- Untuk memahami project, mulai dari list_dir, lalu baca file penting.
- Gunakan search_text untuk mencari simbol/function/teks.
- Gunakan run_cmd untuk test/build hanya jika memang perlu.
- Untuk perubahan file, gunakan write_file.
- Jangan membuat perubahan tanpa alasan jelas.
- Setelah tool selesai, jelaskan hasilnya ringkas.
- Jika task kompleks, buat plan singkat lalu lanjut eksekusi.
- Prioritaskan jawaban praktis dan langsung bisa dijalankan.
"""


@dataclass
class AgentState:
    model: str = "default"
    api_url: str = "http://127.0.0.1:8787"
    token: str = ""
    root: Path = field(default_factory=lambda: Path.cwd().resolve())
    mode: str = "plan → act → verify"
    guard: str = "approval required"
    max_turns: int = 8


STATE = AgentState()
TOOLS: LocalTools | None = None


def shorten_path(path: Path) -> str:
    home = Path.home()

    try:
        return "~/" + str(path.relative_to(home))
    except ValueError:
        return str(path)


def build_client() -> ShagoClient:
    config = load_config()

    STATE.api_url = str(config.get("api_url") or STATE.api_url)
    STATE.token = str(config.get("token") or "")
    STATE.model = str(config.get("model") or STATE.model)
    STATE.guard = str(config.get("guard") or STATE.guard)

    return ShagoClient(
        api_url=STATE.api_url,
        token=STATE.token,
    )


def ensure_tools() -> LocalTools:
    global TOOLS

    if TOOLS is None:
        TOOLS = LocalTools(
            root=STATE.root,
            get_guard=lambda: STATE.guard,
            confirm_callback=confirm_tool_action,
            notify_callback=notify_tool_event,
        )

    TOOLS.set_root(STATE.root)
    return TOOLS


def render_banner() -> None:
    body = (
        f"[bold cyan]{SHAGO_LOGO}[/bold cyan]\n"
        "[bold white]local autonomous coding interface[/bold white]\n\n"
        f"[cyan]AI[/cyan]        [white]{STATE.model}[/white]\n"
        f"[cyan]SERVER[/cyan]    [white]{STATE.api_url}[/white]\n"
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
        ("/health", "cek koneksi ke Shago AI Server"),
        ("/config", "lihat konfigurasi"),
        ("/config set <key> <value>", "ubah konfigurasi"),
        ("/models", "lihat model dari Shago AI Server"),
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
        ("/version", "lihat versi SHAGO AI"),
        ("/update", "lihat command update SHAGO AI"),
    ]

    for cmd, desc in rows:
        table.add_row(cmd, desc)

    console.print(table)


def confirm_tool_action(action: str, payload: dict[str, Any]) -> bool:
    if action == "write_file":
        content = (
            f"[cyan]file[/cyan]   {payload.get('path')}\n"
            f"[cyan]action[/cyan] write\n"
            f"[cyan]chars[/cyan]  {payload.get('chars')}"
        )

        console.print(
            Panel(
                content,
                title="[bold yellow]proposed change[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

        return Confirm.ask("Apply this change?", default=False)

    if action == "run_cmd":
        content = (
            f"[cyan]cwd[/cyan]     {shorten_path(STATE.root)}\n"
            f"[cyan]command[/cyan] {payload.get('command')}"
        )

        console.print(
            Panel(
                content,
                title="[bold yellow]command request[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

        return Confirm.ask("Run this command?", default=False)

    return Confirm.ask(f"Confirm {action}?", default=False)


def notify_tool_event(event: str, payload: dict[str, Any]) -> None:
    # Untuk sekarang event detail ditampilkan saat confirmation.
    # Function ini tetap ada supaya tools.py modular dan bisa dipakai TUI/Rust nanti.
    return None


def get_message_content(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("content") or "")

    return str(getattr(message, "content", "") or "")


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


def normalize_assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "role": message.get("role", "assistant"),
        "content": message.get("content") or "",
    }

    if message.get("tool_calls"):
        normalized["tool_calls"] = message["tool_calls"]

    return normalized


def run_agent(user_prompt: str) -> None:
    client = build_client()
    tools = ensure_tools()

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for _ in range(STATE.max_turns):
        try:
            with console.status("[cyan]● thinking[/cyan]", spinner="dots"):
                response = client.chat(
                    model=STATE.model,
                    messages=messages,
                    tools=tools.tool_specs(),
                    temperature=0.2,
                    max_turns=STATE.max_turns,
                )
        except ShagoClientError as exc:
            console.print(
                Panel(
                    str(exc),
                    title="[bold red]server error[/bold red]",
                    border_style="red",
                )
            )
            return
        except Exception as exc:
            console.print(
                Panel(
                    str(exc),
                    title="[bold red]unexpected error[/bold red]",
                    border_style="red",
                )
            )
            return

        message = response.get("message") or {}
        tool_calls = get_tool_calls(message)
        
        capman = response.get("capman") or {}

        if capman.get("enabled") and capman.get("saved_chars", 0) > 0:
            console.print(
                f"[dim]CapMan saved approx "
                f"{capman.get('approx_saved_tokens', 0)} tokens "
                f"({capman.get('saved_chars', 0)} chars).[/dim]"
            )

        if not tool_calls:
            content = get_message_content(message).strip()

            if content:
                console.print(Markdown(content))
            else:
                console.print("[dim]No response.[/dim]")

            return

        messages.append(normalize_assistant_message(message))

        for call in tool_calls:
            name, args = parse_tool_call(call)

            if not name:
                result = "ERROR: tool call missing function name"
            else:
                render_tool_call(name, args)
                result = tools.call_tool(name, args)

            console.print(
                Panel(
                    preview_text(str(result), 8000),
                    title="[bold green]tool result[/bold green]",
                    border_style="green",
                    expand=False,
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_name": name or "unknown",
                    "content": str(result),
                }
            )

    console.print(
        "[yellow]Agent berhenti karena mencapai batas turn. Coba pecah task jadi lebih kecil.[/yellow]"
    )


def handle_config_command(raw: str) -> bool:
    if raw == "/config":
        config = load_config()

        table = Table(title="SHAGO config", border_style="cyan")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        for key, value in config.items():
            display_value = str(value)

            if key == "token" and display_value:
                display_value = display_value[:6] + "..." + display_value[-4:]

            table.add_row(str(key), display_value)

        console.print(table)
        console.print(f"[dim]config file: {CONFIG_FILE}[/dim]")
        console.print("[dim]Usage: /config set <key> <value>[/dim]")
        return True

    if raw.startswith("/config set "):
        parts = raw.split(" ", 3)

        if len(parts) < 4:
            console.print("[red]Usage:[/red] /config set <key> <value>")
            return True

        key = parts[2].strip()
        value = parts[3].strip()

        allowed = {
         "api_url",
         "token",
         "model",
         "guard",
         "rpk_enabled",
         "rpk_max_tool_chars",
         "rpk_max_read_file_chars",
         "rpk_max_command_chars",
         "rpk_max_search_chars",
         "rpk_max_diff_chars",
        }

        if key not in allowed:
            console.print(f"[red]Invalid config key:[/red] {key}")
            console.print(f"[dim]Allowed keys: {', '.join(sorted(allowed))}[/dim]")
            return True

        set_config_value(key, value)

        if key == "model":
            STATE.model = value

        if key == "guard":
            STATE.guard = value

        if key == "api_url":
            STATE.api_url = value

        if key == "token":
            STATE.token = value

        console.print(f"[green]config updated:[/green] {key}")
        return True

    return False


def fetch_remote_models() -> list[str]:
    client = build_client()

    try:
        response = client.models()
    except ShagoClientError as exc:
        console.print(
            Panel(
                str(exc),
                title="[bold red]models error[/bold red]",
                border_style="red",
            )
        )
        return []

    models = response.get("models") or []
    names = []

    for item in models:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model")
        else:
            name = str(item)

        if name:
            names.append(str(name))

    return names


def handle_command(command: str) -> bool:
    raw = command.strip()

    if raw in {"/exit", "/quit", "/q", "/bye"}:
        return False

    if raw == "/clear":
        console.clear()
        render_banner()
        return True

    if raw == "/help":
        print_help()
        return True

    if raw == "/health":
        client = build_client()

        try:
            response = client.health()
            console.print(
                Panel(
                    json.dumps(response, indent=2, ensure_ascii=False),
                    title="[bold green]server health[/bold green]",
                    border_style="green",
                )
            )
        except ShagoClientError as exc:
            console.print(
                Panel(
                    str(exc),
                    title="[bold red]server health failed[/bold red]",
                    border_style="red",
                )
            )

        return True

    if raw == "/config" or raw.startswith("/config set "):
        return handle_config_command(raw)

    if raw == "/models":
        names = fetch_remote_models()

        table = Table(title="Available models", border_style="cyan")
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Model", style="white")
        table.add_column("Active", style="green")

        for idx, name in enumerate(names, start=1):
            table.add_row(str(idx), name, "yes" if name == STATE.model else "")

        if not names:
            table.add_row("-", "(no models found)", "")

        console.print(table)
        return True

    if raw == "/model":
        names = fetch_remote_models()

        table = Table(title="Model selection", border_style="cyan")
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Model", style="white")
        table.add_column("Active", style="green")

        for idx, name in enumerate(names, start=1):
            active = "yes" if name == STATE.model else ""
            table.add_row(str(idx), name, active)

        if not names:
            table.add_row("-", "(no models found)", "")

        console.print(table)
        console.print(f"[cyan]current model:[/cyan] {STATE.model}")
        console.print("[dim]Usage: /model <name> or /model <number>[/dim]")
        return True

    if raw.startswith("/model "):
        value = raw.split(" ", 1)[1].strip()
        names = fetch_remote_models()

        if not value:
            console.print("[red]Usage:[/red] /model <name>")
            return True

        selected = value

        if value.isdigit():
            index = int(value) - 1

            if index < 0 or index >= len(names):
                console.print(f"[red]Invalid model number:[/red] {value}")
                return True

            selected = names[index]

        if names and selected not in names and selected != "default":
            console.print(f"[red]Model not found:[/red] {selected}")
            console.print("[dim]Run /models or /model to see available models.[/dim]")
            return True

        STATE.model = selected
        set_config_value("model", STATE.model)

        console.print(f"[green]model set:[/green] {STATE.model}")
        console.print("[dim]Saved as default model.[/dim]")
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
        ensure_tools().set_root(STATE.root)

        console.print(f"[green]workspace set:[/green] {shorten_path(STATE.root)}")
        return True

    if raw == "/safe":
        STATE.guard = "approval required"
        set_config_value("guard", STATE.guard)
        console.print("[green]guard set:[/green] approval required")
        return True

    if raw == "/auto":
        STATE.guard = "confirm destructive"
        set_config_value("guard", STATE.guard)
        console.print("[yellow]guard set:[/yellow] confirm destructive")
        return True

    if raw == "/diff":
        result = ensure_tools().git_diff()
        console.print(
            Panel(
                preview_text(result, 12000),
                title="[cyan]git diff[/cyan]",
                border_style="cyan",
            )
        )
        return True

    if raw == "/undo":
        result = ensure_tools().undo_last_write()
        console.print(
            Panel(
                result,
                title="[cyan]undo[/cyan]",
                border_style="cyan",
            )
        )
        return True
    
    if raw == "/version":
        console.print(f"[cyan]shagoai[/cyan] {__version__}")
        return True

    if raw == "/update":
        console.print(
            Panel(
                "Run this command outside SHAGO AI:\n\n"
                "[cyan]curl -fsSL https://raw.githubusercontent.com/oviekshagya51/shagoai/main/install.sh | sh[/cyan]\n\n"
                "Your config will be kept at:\n"
                f"[white]{CONFIG_FILE}[/white]",
                title="[bold cyan]update SHAGO AI[/bold cyan]",
                border_style="cyan",
            )
        )
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

    parser.add_argument(
        "--api-url",
        default=None,
        help="Set Shago AI Server URL for this session.",
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show SHAGO AI version.",
    )
    args = parser.parse_args()
	

    config = load_config()

    STATE.root = (
        Path(args.workspace).expanduser().resolve()
        if args.workspace
        else Path.cwd().resolve()
    )

    STATE.api_url = args.api_url or str(config.get("api_url") or STATE.api_url)
    STATE.token = str(config.get("token") or "")
    STATE.model = args.model or str(config.get("model") or STATE.model)
    STATE.guard = str(config.get("guard") or STATE.guard)

    ensure_tools()

    console.clear()
    render_banner()
    console.print(
        "[dim]Tip: Use [cyan]/plan[/cyan] in your prompt to preview actions before execution.[/dim]\n"
    )

    history_path = str(Path.home() / ".shago_agent_history")

    style = Style.from_dict(
        {
            "prompt": "ansicyan bold",
        }
    )

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