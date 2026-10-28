import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    static_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "./data")).resolve(),
            static_dir=Path(os.getenv("STATIC_DIR", "./static")).resolve(),
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "fpl-assistant.sqlite3"
