"""Challenges of the TD parcours, read from the overlay catalogue.

Source of truth : ``overlay/frontend/src/assets/juicelab/selected_challenges.yml``
(the list the students see). The dashboard reads it from, in order :

1. ``DASHBOARD_PARCOURS_YML`` (env var, explicit path) ;
2. ``<dashboard>/parcours/selected_challenges.yml`` (copied there by
   docker/Dockerfile.dashboard) ;
3. ``<repo>/overlay/frontend/src/assets/juicelab/selected_challenges.yml``
   (dashboard run from a checkout).

Only the keys are needed, so the file is parsed with a minimal reader (no
YAML dependency) : the two-space indented ``<key>:`` lines under
``selected_challenges:``. No file found, or a file without any key, raises
ParcoursUnavailable : a diploma must not be computed on a guessed total.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = (
    HERE / "parcours" / "selected_challenges.yml",
    HERE.parent / "overlay" / "frontend" / "src" / "assets" / "juicelab" / "selected_challenges.yml",
)
_KEY = re.compile(r"^  ([A-Za-z0-9_]+):\s*(#.*)?$")


class ParcoursUnavailable(RuntimeError):
    """The parcours catalogue is missing or holds no challenge."""


def parcours_path() -> Path:
    """First existing catalogue path (see module docstring)."""
    env = os.environ.get("DASHBOARD_PARCOURS_YML", "").strip()
    paths = (Path(env),) if env else CANDIDATES
    for p in paths:
        if p.is_file():
            return p
    raise ParcoursUnavailable(
        "parcours catalogue not found (set DASHBOARD_PARCOURS_YML) : "
        + ", ".join(str(p) for p in paths))


def parse_keys(text: str) -> list[str]:
    """Challenge keys listed under ``selected_challenges:``, in file order."""
    keys: list[str] = []
    inside = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            inside = line.rstrip() == "selected_challenges:"
            continue
        m = _KEY.match(line) if inside else None
        if m:
            keys.append(m.group(1))
    return keys


def parcours_keys() -> list[str]:
    """Parcours challenge keys. Raises ParcoursUnavailable."""
    path = parcours_path()
    keys = parse_keys(path.read_text(encoding="utf-8"))
    if not keys:
        raise ParcoursUnavailable("no challenge listed in " + str(path))
    return keys
