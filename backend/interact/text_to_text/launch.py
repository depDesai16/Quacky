import os
import subprocess
import sys
import time
import urllib.parse


def _normalize_base_url(url: str) -> str:
    raw = str(url or "").strip()
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("QUACKY_BASE_URL must use http or https and include a host")
    return raw.rstrip("/")


def _wait_for_server(url: str, timeout: float = 5.0) -> None:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{url}/health", method="GET")
            # The health check URL is constrained to a validated http(s) base URL.
            with urllib.request.urlopen(req) as resp:  # nosec B310
                if resp.status == 200:
                    return
        except urllib.error.URLError:
            time.sleep(0.2)
    raise RuntimeError("Server did not become ready in time.")


def main() -> int:
    base_url = _normalize_base_url(os.getenv("QUACKY_BASE_URL", "http://localhost:8000"))
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
