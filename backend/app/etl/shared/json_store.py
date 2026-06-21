import json
from pathlib import Path

from pydantic import BaseModel


def save_json(path: Path, data: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
