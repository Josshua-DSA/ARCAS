"""Parquet storage helpers for bulk dumps and training datasets."""

from pathlib import Path
from typing import Any
import pandas as pd


class ParquetStore:
    """Manages Parquet writes and reads for processed time series."""

    def __init__(self, base_dir: Path | str = Path("data/processed")):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_dataset(self, name: str, data: list[dict[str, Any]] | pd.DataFrame) -> Path:
        """Saves records to a Parquet file."""
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data

        file_path = self.base_dir / f"{name}.parquet"
        df.to_parquet(file_path, index=False, engine="pyarrow")
        return file_path

    def read_dataset(self, name: str) -> pd.DataFrame:
        """Reads records from a Parquet file."""
        file_path = self.base_dir / f"{name}.parquet"
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")
        return pd.read_parquet(file_path, engine="pyarrow")
