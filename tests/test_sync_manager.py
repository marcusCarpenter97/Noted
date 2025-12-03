
from unittest.mock import Mock
from database import Database
from notes_repository import NotesRepository
from sync_manager import SyncManager

def test_sync_down_creates_new_note():
    db = Database(":memory:")
    repo = NotesRepository(db)
    repo.create_notes_table()

    fake_remote_note = {
        "uuid": "28624697-db0b-4252-a904-8de04ea772e7",
        "title": "Hello",
        "contents": "World",
        "embeddings": "zczMPc3MTD6amZk+",
        "tags": "tag",
        "created_at": "2025-01-01T12:00:00Z",
        "last_updated": "2025-01-01T12:00:00Z",
        "deleted": False
    }

    client = Mock()
    client.pull_changes.return_value = [fake_remote_note]

    sm = SyncManager(repo, client)

    sm.sync_down()

    saved = repo.get_note("28624697-db0b-4252-a904-8de04ea772e7")
    assert saved is not None
    assert saved[1] == "Hello"
