import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_run_all_expands_every_iteration_and_policy_command() -> None:
    completed = subprocess.run(
        ["make", "--dry-run", "run-all"],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    commands = [
        line
        for line in completed.stdout.splitlines()
        if line.startswith("uv run python main.py ")
    ]
    expected_commands = [
        "uv run python main.py "
        f"--configs configs/iteration-{number:02d}/{policy}.yaml "
        f"--metrics-output-path outputs/iteration-{number:02d}/{policy}"
        for number in range(1, 11)
        for policy in (
            "always_active",
            "staggered_active",
            "threshold_staggered_active",
        )
    ]

    assert commands == expected_commands
