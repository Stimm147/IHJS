import sys
import asyncio
import importlib
import importlib.util
from pathlib import Path
from contextlib import asynccontextmanager

import typer
import uvicorn
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket
from watchfiles import awatch

app = typer.Typer(name="ihjs", add_completion=False)


active_connections = set()

SCRIPT_AUTORELOAD = """
<script>
    (function() {
        var ws = new WebSocket("ws://" + window.location.host + "/ws");
        ws.onmessage = function(event) {
            if (event.data === "reload") {
                console.log("File changed. Reloading website.");
                window.location.reload();
            }
        };
        ws.onclose = function() {
            console.log("Connection lost. Trying to reconnect after 2s...");
            setTimeout(() => window.location.reload(), 2000);
        };
    })();
</script>
"""


def get_user_module(path: Path):
    module_name = path.stem
    user_dir = str(path.parent.resolve())

    if user_dir not in sys.path:
        sys.path.insert(0, user_dir)

    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Can't load {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def create_dev_server(app_path: Path):
    async def homepage(request):
        try:
            user_module = get_user_module(app_path)
            if not hasattr(user_module, "index"):
                return HTMLResponse("Error: No index() function", status_code=500)

            page = user_module.index()
            html = page.render()

            if "</body>" in html:
                html = html.replace("</body>", f"{SCRIPT_AUTORELOAD}</body>")
            else:
                html += SCRIPT_AUTORELOAD

            return HTMLResponse(html)
        except Exception as e:
            import traceback

            return HTMLResponse(
                f"<div style='color:red'><pre>{traceback.format_exc()}</pre></div>{SCRIPT_AUTORELOAD}",
                status_code=500,
            )

    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        active_connections.add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except:
            active_connections.remove(websocket)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(file_watcher(app_path))
        yield

    async def file_watcher(path):
        watch_dir = path.parent

        async for changes in awatch(watch_dir):
            if any(f.endswith(".py") for _, f in changes):
                print("Change detected. Reloading client...")
                for ws in list(active_connections):
                    try:
                        await ws.send_text("reload")
                    except:
                        active_connections.remove(ws)

    return Starlette(
        debug=True,
        routes=[Route("/", homepage), WebSocketRoute("/ws", websocket_endpoint)],
        lifespan=lifespan,
    )


@app.command()
def dev(
    file: Path = typer.Argument(Path("app.py"), help="App file path"),
    port: int = typer.Option(8000),
    host: str = typer.Option("127.0.0.1"),
):
    """
    Starts the dev server with hot reload (defaults to app.py).
    """
    if not file.exists():
        typer.secho(f"Error: File '{file}' not found!", fg=typer.colors.RED)
        typer.echo("Hint: Use 'ihjs init <name>' to create a new project.")
        raise typer.Exit(1)

    print(f"\nLive Server: http://{host}:{port}")

    server = create_dev_server(file)

    uvicorn.run(server, host=host, port=port, log_level="warning")


def load_user_app(path: Path):
    if not path.exists():
        typer.secho(f"Error: Can't find file {path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    sys.path.insert(0, str(path.parent.resolve()))

    spec = importlib.util.spec_from_file_location("user_app", path)
    if spec is None or spec.loader is None:
        typer.secho("Error: Can't load module.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


@app.command()
def build(
    file: Path = typer.Argument(Path("app.py"), help="Path to the app file"),
    output: Path = typer.Option(
        Path("dist"), "--output", "-o", help="Output directory"
    ),
):
    """
    Builds the static site (defaults to app.py in the current directory).
    """
    if not file.exists():
        typer.secho(
            f"Error: File '{file}' not found. Are you in the right directory?",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    typer.echo(f"Building project from file: {file}")

    try:
        user_module = get_user_module(file)
    except Exception as e:
        typer.secho(f"Error loading module: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not hasattr(user_module, "index"):
        typer.secho("Error: Missing index() function in app.py", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        html_content = user_module.index().render()
    except Exception as e:
        typer.secho(f"Error during rendering: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    output.mkdir(exist_ok=True)
    with open(output / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    typer.secho(f"Success! Generated at: {output}/index.html", fg=typer.colors.GREEN)


@app.command()
def init(
    name: str = typer.Argument(..., help="Project name (creates a directory)"),
):
    """
    Initialize a new IHJS project structure.
    """
    project_path = Path(name)

    if project_path.exists():
        typer.secho(f"Error: Directory '{name}' already exists!", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"Creating project directory: {name}...")
    project_path.mkdir()
    (project_path / "assets").mkdir()
    (project_path / "components").mkdir()

    app_code = """import ihjs as ui

def index():
    return ui.div(
        class_name="min-h-screen bg-gray-50 flex items-center justify-center",
        children=[
            ui.div(
                class_name="p-8 bg-white shadow-lg rounded-xl text-center",
                children=[
                    ui.heading("Welcome to IHJS! 🚀", level=1, class_name="text-3xl font-bold text-blue-600 mb-4"),
                    ui.text("This is your new static site project.", class_name="text-gray-600 mb-6 block"),
                    ui.text("Edit app.py to get started.", class_name="text-sm text-gray-400 italic")
                ]
            )
        ]
    )
"""
    with open(project_path / "app.py", "w", encoding="utf-8") as f:
        f.write(app_code)

    with open(project_path / "components" / "__init__.py", "w") as f:
        pass

    gitignore_content = """dist/
__pycache__/
.venv/
*.pyc
"""
    with open(project_path / ".gitignore", "w", encoding="utf-8") as f:
        f.write(gitignore_content)

    typer.secho(f"Project '{name}' created successfully!", fg=typer.colors.GREEN)
    typer.echo("To get started:")
    typer.secho(f"cd {name}", fg=typer.colors.CYAN)
    typer.secho(f"ihjs dev", fg=typer.colors.CYAN)


def main():
    app()


if __name__ == "__main__":
    main()
