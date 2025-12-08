import json
from pathlib import Path

class RemoteAPIClient:
    def __init__(self, fixtures_dir="tests/fixtures/"):
        self.fixtures_dir = Path(fixtures_dir)

    def pull_changes(self, since_timestamp: str) -> list[dict]:
        with open(self.fixtures_dir / "pull_response.json") as f:
            return json.load(f)

    def push_changes(self, operations: list[dict]) -> dict:
        with open(self.fixtures_dir / "push_response.json") as f:
            return json.load(f)
