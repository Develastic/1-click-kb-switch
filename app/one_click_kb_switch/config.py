from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
import tomllib

from one_click_kb_switch.paths import bundle_root


@dataclass(frozen=True, slots=True)
class AppMetadata:
    canonical_name: str
    company: str
    company_url: str
    author: str
    version: str
    config_schema_version: int
    windows_upgrade_code: str


def load_metadata() -> AppMetadata:
    data = tomllib.loads((bundle_root() / "config.toml").read_text(encoding="utf-8"))["app"]
    return AppMetadata(
        canonical_name=data["canonical_name"],
        company=data["company"],
        company_url=data["company_url"],
        author=data["author"],
        version=_load_version(),
        config_schema_version=int(data["config_schema_version"]),
        windows_upgrade_code=data["windows_upgrade_code"],
    )


def _load_version() -> str:
    try:
        return version("one-click-kb-switch")
    except PackageNotFoundError:
        pyproject_path = bundle_root() / "pyproject.toml"
        if pyproject_path.exists():
            payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            return str(payload["project"]["version"])
        return "0.0.0"
