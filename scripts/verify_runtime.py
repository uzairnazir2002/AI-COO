from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"\n[run] {' '.join(cmd)}")
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    subprocess.run(cmd, cwd=str(cwd), env=merged_env, check=True)


def _wait_for_health(health_url: str, timeout_sec: int) -> None:
    print(f"[wait] health check: {health_url}")
    start = time.time()
    with httpx.Client(timeout=5.0) as client:
        while time.time() - start < timeout_sec:
            try:
                res = client.get(health_url)
                if res.status_code == 200:
                    print("[ok] health endpoint is up")
                    return
            except Exception:
                pass
            time.sleep(2)
    raise RuntimeError(f"Health check failed within {timeout_sec}s: {health_url}")


def _npm_cmd() -> str:
    return "npm.cmd" if sys.platform.startswith("win") else "npm"


def _resolve_python(root: Path) -> Path:
    win = root / ".venv" / "Scripts" / "python.exe"
    posix = root / ".venv" / "bin" / "python"
    if sys.platform.startswith("win") and win.exists():
        return win
    if posix.exists():
        return posix
    return Path(sys.executable)


def _cookie_mode_enabled() -> bool:
    value = os.environ.get("AUTH_COOKIE_MODE", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify local runtime end-to-end (backend + frontend).")
    parser.add_argument("--api-base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--frontend-base-url", default="http://localhost:3000")
    parser.add_argument("--health-timeout-sec", type=int, default=120)
    parser.add_argument("--skip-backend-tests", action="store_true")
    parser.add_argument("--skip-e2e", action="store_true")
    parser.add_argument("--with-visual", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    backend = root / "backend"
    frontend = root / "frontend"

    python_exe = _resolve_python(root)
    print(f"[info] using python: {python_exe}")

    health_url = f"{args.api_base_url}/health"
    _wait_for_health(health_url, args.health_timeout_sec)

    if not args.skip_backend_tests:
        _run([str(python_exe), "-m", "pytest", "app/tests", "-q"], cwd=backend)

    # Smoke bearer
    _run(
        [
            str(python_exe),
            str(root / "scripts" / "smoke_mvp.py"),
            "--base-url",
            args.api_base_url,
            "--auth-mode",
            "bearer",
        ],
        cwd=root,
    )

    if _cookie_mode_enabled():
        _run(
            [
                str(python_exe),
                str(root / "scripts" / "smoke_mvp.py"),
                "--base-url",
                args.api_base_url,
                "--auth-mode",
                "cookie",
            ],
            cwd=root,
        )
    else:
        print("\n[skip] cookie-mode smoke skipped because AUTH_COOKIE_MODE is disabled in the current env")

    if not args.skip_e2e:
        npm = _npm_cmd()
        _run(
            [npm, "run", "e2e"],
            cwd=frontend,
            env={
                "E2E_BASE_URL": args.frontend_base_url,
                "E2E_API_URL": args.api_base_url,
                "E2E_AUTH_MODE": "bearer",
            },
        )
        if _cookie_mode_enabled():
            _run(
                [npm, "run", "e2e"],
                cwd=frontend,
                env={
                    "E2E_BASE_URL": args.frontend_base_url,
                    "E2E_API_URL": args.api_base_url,
                    "E2E_AUTH_MODE": "cookie",
                },
            )
        else:
            print("[skip] cookie-mode E2E skipped because AUTH_COOKIE_MODE is disabled in the current env")
        if args.with_visual:
            _run(
                [npm, "run", "e2e:visual"],
                cwd=frontend,
                env={
                    "E2E_BASE_URL": args.frontend_base_url,
                    "E2E_API_URL": args.api_base_url,
                    "E2E_AUTH_MODE": "bearer",
                    "E2E_VISUAL": "1",
                },
            )

    print("\n[done] runtime verification completed successfully")


if __name__ == "__main__":
    main()
