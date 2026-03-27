"""Generic version comparison for any product/platform version format."""

import re
from typing import Dict, List, Optional, Tuple

VersionTuple = Tuple[int, ...]


class VersionComparator:
    """Compares version strings using a configurable regex and capture groups.

    Supports:
      - kernel_range: RHEL-style kernels like 4.18.0-425.el8
      - semver: standard major.minor.patch
      - package_version: RPM/deb style epoch:version-release
    """

    def __init__(self, constraint_config: Dict) -> None:
        self.type = constraint_config["type"]
        self.regex = re.compile(constraint_config["version_regex"])
        self.groups: Optional[List[int]] = constraint_config.get("comparison_groups")

    def parse(self, version_str: str) -> VersionTuple:
        """Parse a version string into a comparable integer tuple."""
        m = self.regex.search(version_str)
        if not m:
            raise ValueError(
                f"Version '{version_str}' does not match regex '{self.regex.pattern}'"
            )
        if self.groups:
            return tuple(int(m.group(i)) for i in self.groups)
        # Fallback: use all capture groups
        return tuple(int(g) for g in m.groups() if g is not None)

    def is_within(self, version: str, min_v: str, max_v: str) -> bool:
        """Return True if version is within [min_v, max_v] inclusive."""
        v = self.parse(version)
        lo = self.parse(min_v)
        hi = self.parse(max_v)
        return lo <= v <= hi

    def bump(self, version: str) -> str:
        """Increment the last comparison group by 1 and return the new version string.

        Used by generate_tests.py to produce an above-max test case.
        """
        m = self.regex.search(version)
        if not m:
            raise ValueError(f"Cannot bump: '{version}' does not match regex '{self.regex.pattern}'")

        if self.groups:
            last_group = self.groups[-1]
        else:
            # Use the last capture group
            last_group = len(m.groups())

        span = m.span(last_group)
        incremented = str(int(m.group(last_group)) + 1)
        return version[: span[0]] + incremented + version[span[1] :]

    def sort_key(self, version: str) -> VersionTuple:
        return self.parse(version)

    def compare(self, a: str, b: str) -> int:
        """Return -1, 0, or 1 comparing a to b."""
        ta = self.parse(a)
        tb = self.parse(b)
        if ta < tb:
            return -1
        if ta > tb:
            return 1
        return 0
