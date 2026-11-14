"""Create the throwaway git workspace from the supplied tinyledger fixture."""

import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL_FIXTURE = HERE / "tinyledger"
UPSTREAM_FIXTURE = HERE.parents[2] / "resources" / "lab1" / "task4_tools" / "tinyledger"
SOURCE = LOCAL_FIXTURE if LOCAL_FIXTURE.is_dir() else UPSTREAM_FIXTURE
WORKSPACE = HERE / "workspace"


def main() -> None:
    if not SOURCE.is_dir():
        raise SystemExit(
            f"tinyledger fixture not found at {SOURCE}\n"
            "Copy it there from the lab material (resources/lab1/task4_tools/tinyledger)."
        )
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
    shutil.copytree(SOURCE, WORKSPACE, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    git = ["git", "-C", str(WORKSPACE), "-c", "user.name=lab", "-c", "user.email=lab@example.org"]
    subprocess.run(git[:3] + ["init", "-q"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "initial state"], check=True)
    print(f"Fresh workspace ready: {WORKSPACE}")


if __name__ == "__main__":
    main()
