"""Single source of truth for all file paths in the compatibility automation tool."""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def configs_dir() -> Path:
    return REPO_ROOT / "configs" / "sources"


def data_dir(config_id: str) -> Path:
    return REPO_ROOT / "data" / config_id


def raw_dir(config_id: str) -> Path:
    return data_dir(config_id) / "raw"


def parsed_dir(config_id: str) -> Path:
    return data_dir(config_id) / "parsed"


def baseline_rule(config_id: str) -> Path:
    return REPO_ROOT / "rules" / "baselines" / f"{config_id}.yaml"


def generated_rule(config_id: str) -> Path:
    return REPO_ROOT / "rules" / "generated" / f"{config_id}.yaml"


def baseline_tests(config_id: str) -> Path:
    return REPO_ROOT / "tests" / "baselines" / f"{config_id}_cases.yaml"


def generated_tests(config_id: str) -> Path:
    return REPO_ROOT / "tests" / "generated" / f"{config_id}_cases.yaml"


def human_review_dir(config_id: str) -> Path:
    return REPO_ROOT / "human_reviews" / config_id


def diff_summary(config_id: str) -> Path:
    return parsed_dir(config_id) / "diff_summary.json"


def pr_body(config_id: str) -> Path:
    return parsed_dir(config_id) / "pr_body.md"
