"""Load and validate source configs from configs/sources/*.yaml."""

import re
from pathlib import Path
from typing import Dict, List

import yaml  # type: ignore

from . import path_resolver

VALID_CONSTRAINT_TYPES = {"kernel_range", "semver", "package_version"}


class ConfigValidationError(Exception):
    pass


def load_config(config_id: str) -> Dict:
    path = path_resolver.configs_dir() / f"{config_id}.yaml"
    if not path.exists():
        raise ConfigValidationError(f"Config not found: {path}")
    with path.open() as f:
        cfg = yaml.safe_load(f) or {}
    _validate(cfg, path)
    return cfg


def list_config_ids() -> List[str]:
    configs_dir = path_resolver.configs_dir()
    if not configs_dir.exists():
        return []
    ids = []
    for p in sorted(configs_dir.glob("*.yaml")):
        try:
            with p.open() as f:
                cfg = yaml.safe_load(f) or {}
            ids.append(cfg.get("id", p.stem))
        except Exception:
            ids.append(p.stem)
    return ids


def load_all_configs() -> Dict[str, Dict]:
    result = {}
    for config_id in list_config_ids():
        try:
            result[config_id] = load_config(config_id)
        except ConfigValidationError:
            pass
    return result


def _validate(cfg: Dict, path: Path) -> None:
    def require(key: str, obj: Dict, label: str) -> None:
        if key not in obj or obj[key] is None:
            raise ConfigValidationError(f"Missing required field '{label}.{key}' in {path}")

    require("id", cfg, "root")
    require("product", cfg, "root")
    require("platform", cfg, "root")
    require("version_constraint", cfg, "root")

    vc = cfg["version_constraint"]
    require("type", vc, "version_constraint")
    require("version_regex", vc, "version_constraint")

    if vc["type"] not in VALID_CONSTRAINT_TYPES:
        raise ConfigValidationError(
            f"version_constraint.type must be one of {VALID_CONSTRAINT_TYPES}, got '{vc['type']}' in {path}"
        )

    try:
        re.compile(vc["version_regex"])
    except re.error as e:
        raise ConfigValidationError(
            f"version_constraint.version_regex is invalid regex in {path}: {e}"
        )
