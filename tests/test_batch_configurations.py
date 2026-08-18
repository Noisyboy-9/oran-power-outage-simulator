from pathlib import Path

from simulator.configuration import ControllerKind, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ITERATIONS = tuple(f"iteration-{number:02d}" for number in range(1, 11))
POLICIES = (
    "always_active",
    "staggered_active",
    "threshold_staggered_active",
)
EXPECTED_KINDS = {
    "always_active": ControllerKind.ALWAYS_ACTIVE,
    "staggered_active": ControllerKind.STAGGERED_ACTIVE,
    "threshold_staggered_active": ControllerKind.THRESHOLD_STAGGERED_ACTIVE,
}


def test_iteration_configurations_are_complete_and_loader_valid() -> None:
    seeds: list[int] = []

    for iteration_number, iteration in enumerate(ITERATIONS, start=1):
        iteration_path = PROJECT_ROOT / "configs" / iteration
        assert {path.stem for path in iteration_path.glob("*.yaml")} == set(POLICIES)

        iteration_seeds = set()
        for policy in POLICIES:
            config = load_config(iteration_path / f"{policy}.yaml")
            assert config.controller.kind is EXPECTED_KINDS[policy]
            iteration_seeds.add(config.environment.random_seed)

        assert iteration_seeds == {iteration_number}
        seeds.extend(iteration_seeds)

    assert set(seeds) == set(range(1, 11))


def test_flat_policy_configurations_are_absent() -> None:
    configs_path = PROJECT_ROOT / "configs"

    for policy in POLICIES:
        assert not (configs_path / f"{policy}.yaml").exists()

    assert (configs_path / "default.yaml").exists()
