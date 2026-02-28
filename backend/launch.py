import os
import subprocess
import sys
import time


def _wait_for_server(url: str, timeout: float = 5.0) -> None:
    """Poll the health endpoint until the server is ready or timeout expires."""
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health") as resp:
                if resp.status == 200:
                    return
        except urllib.error.URLError:
            time.sleep(0.2)
    raise RuntimeError("Server did not become ready in time.")


def main() -> int:
    """Start server subprocess, run CLI, and ensure server is terminated on exit."""
    base_url = os.getenv("QUACKY_BASE_URL", "http://localhost:8000")
    server_cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "server.py")]

    server_proc = subprocess.Popen(server_cmd)
    try:
        _wait_for_server(base_url)
        cli_cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "cli.py")]
        return subprocess.call(cli_cmd)
    finally:
        if server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_proc.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
