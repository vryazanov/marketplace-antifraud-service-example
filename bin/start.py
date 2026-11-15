import os
import subprocess
import sys


def main() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    # Replace the supervisor: SIGTERM reaches uvicorn directly.
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "bin.api:app",
            "--host",
            "0.0.0.0",
            "--port",
            os.getenv("PORT", "8000"),
        ],
    )


if __name__ == "__main__":
    main()
