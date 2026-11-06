"""Write contract/schema.json from the pydantic views. Run: uv run python -m contract.export"""
import json
from pathlib import Path

from contract.views import Contract

PATH = Path(__file__).with_name("schema.json")


def schema_text() -> str:
    return json.dumps(Contract.model_json_schema(), indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    PATH.write_text(schema_text())
    print(f"wrote {PATH}")
