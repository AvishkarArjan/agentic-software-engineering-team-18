"""Create the throwaway git workspace from the supplied tinyledger fixture."""

import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / "resources" / "lab1" / "task4_tools" / "tinyledger"
WORKSPACE = HERE / "workspace"


def main() -> None:
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
