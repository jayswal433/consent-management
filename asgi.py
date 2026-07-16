import os
import socket
from pathlib import Path

import click
import uvicorn
from app.core.logging import setup_logging
from app.api.server import app


def _get_lan_ip() -> str:
    """Return the machine's outbound LAN IP.

    Opens a UDP socket toward an external address (no packet is sent) to let
    the OS pick the correct outbound interface, then reads the local address.
    Falls back to localhost on any error.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def load_env_file(env: str) -> None:
    env_file = Path(f"{env}.env")
    if env_file.exists():
        with env_file.open("r", encoding="utf-8") as env_handle:
            for line in env_handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value


@click.command("run_server", help="Run the server")
@click.option(
    "--env",
    type=click.Choice(["local", "dev", "prod"], case_sensitive=False),
    default="local",
)
@click.option(
    "--debug",
    type=click.BOOL,
    is_flag=True,
    default=False,
)
def main(env: str, debug: bool) -> None:
    os.environ["ENV"] = env
    os.environ["DEBUG"] = str(debug)

    load_env_file(env=env)

    log_level = "DEBUG" if debug else "INFO"
    setup_logging(level=log_level)

    host = str(os.environ.get("SERVER_HOST", "localhost"))
    port = int(os.environ.get("SERVER_PORT", 8008))

    use_reload = env in ["local", "dev"] or debug
    workers = None if use_reload else os.cpu_count()

 
    uvicorn.run(
        app="app.api.server:app",
        host=host,
        port=port,
        reload=use_reload,
        workers=workers,
        # RequestLoggingMiddleware handles request/response logging with
        # timing and body context, so uvicorn's duplicate access log is off.
        access_log=False,
        log_level=log_level.lower(),
    )


if __name__ == "__main__":
    main()
