import atexit
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SERVICES = [
    "audio-service",
    "asr-service",
    "language-service",
    "translation-service",
    "nlp-service",
    "urgency-service",
    "persistence-service",
]

_worker_procs: list[subprocess.Popen] = []


def _pid_file(logs_dir: Path, svc: str) -> Path:
    return logs_dir / f"{svc}.pid"


def _is_running(pid: int) -> bool:
    """Return True if a process with *pid* is alive."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _read_pid(pid_path: Path) -> int | None:
    try:
        return int(pid_path.read_text().strip())
    except (ValueError, OSError):
        return None


def start_workers() -> None:
    rabbit_url = os.environ.get("RABBIT_URL", "amqp://sentiment:password@rabbitmqalhos:5672/")
    python_bin = os.environ.get("PYTHON_BIN", sys.executable)
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    base_env = os.environ.copy()
    base_env.update(
        {
            "RABBIT_URL": rabbit_url,
            "HF_HUB_DISABLE_PROGRESS_BARS": "1",
            "TRANSFORMERS_NO_PROGRESS_BAR": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TQDM_DISABLE": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )

    print(f"Starting pipeline workers (RABBIT_URL={rabbit_url})")
    print(f"Using Python: {python_bin}")
    print(f"Logs in: {logs_dir}/")
    print()

    for svc in SERVICES:
        pid_path = _pid_file(logs_dir, svc)
        existing_pid = _read_pid(pid_path)
        if existing_pid is not None and _is_running(existing_pid):
            print(f"  \u23ed {svc} already running (pid {existing_pid}), skipping")
            continue

        # Stale PID file — remove it before starting a fresh process.
        pid_path.unlink(missing_ok=True)

        svc_dir = ROOT / "services" / svc
        log_file = logs_dir / f"{svc}.log"
        svc_env = base_env.copy()
        svc_env["PYTHONPATH"] = f"{svc_dir}:{ROOT}"

        print(f"  \u25b6 {svc} \u2192 {log_file}")
        with open(log_file, "a") as log_fh:
            proc = subprocess.Popen(
                [python_bin, "-u", "-m", "app.main"],
                cwd=svc_dir,
                env=svc_env,
                stdout=log_fh,
                stderr=log_fh,
                stdin=subprocess.DEVNULL,
            )
            pid_path.write_text(str(proc.pid))
            _worker_procs.append(proc)

    print()
    print("All workers started.")
    print(f"Monitor logs with:  tail -f {logs_dir}/*.log")
    print(f"To stop workers:    pkill -f '{python_bin} -m app.main'")
    print()


def stop_workers() -> None:
    logs_dir = ROOT / "logs"
    for proc in _worker_procs:
        if proc.poll() is None:
            proc.terminate()
    for proc in _worker_procs:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        # Clean up the PID file for any process this instance owns.
        for svc in SERVICES:
            pid_path = _pid_file(logs_dir, svc)
            existing_pid = _read_pid(pid_path)
            if existing_pid == proc.pid:
                pid_path.unlink(missing_ok=True)


def main() -> None:
    start_workers()
    atexit.register(stop_workers)

    # Add the API gateway directory to sys.path so `app.main` resolves correctly.
    api_gateway_dir = str(ROOT / "services" / "api-gateway")
    if api_gateway_dir not in sys.path:
        sys.path.insert(0, api_gateway_dir)

    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))

    print(f"Starting API Gateway on http://{host}:{port}")
    print("Press Ctrl+C to stop all services.")
    print()

    reload_env = os.environ.get("DEV_RELOAD", os.environ.get("RELOAD", "false")).lower()
    reload_flag = reload_env in ("1", "true", "yes", "on")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload_flag,
        app_dir=api_gateway_dir,
    )


if __name__ == "__main__":
    main()

