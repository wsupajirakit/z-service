"""Where build_meta.py wrote the server symbol list and the build metadata."""

from pathlib import Path

from zservice.core.config import ZsSettings, env_field, settings_getter

BACKEND_DIR = Path(__file__).resolve().parents[3]


class SymbolsSettings(ZsSettings):
    symbols_file: str = env_field(
        "SYMBOLS_FILE", "", doc="Server symbol list written at build time (backend/symbols.json)."
    )
    version_file: str = env_field(
        "VERSION_FILE", "", doc="Build metadata for /api/version (backend/VERSION.json)."
    )
    source_commit: str = env_field(
        "SOURCE_COMMIT",
        "",
        doc="Commit being run, set by the hosting panel at run time (Coolify does); "
        "/api/version shows it when the build did not record one.",
    )

    def symbols_path(self) -> str:
        return self.symbols_file or str(BACKEND_DIR / "symbols.json")

    def version_path(self) -> str:
        return self.version_file or str(BACKEND_DIR / "VERSION.json")


get_settings = settings_getter(SymbolsSettings)
