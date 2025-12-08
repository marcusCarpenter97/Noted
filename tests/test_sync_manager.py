
from unittest.mock import Mock
from database import Database
from notes_repository import NotesRepository
from sync_manager import SyncManager
from lexical_index import LexicalIndex

def test_sync_down_creates_new_note():
    db = Database(":memory:")
    repo = NotesRepository(db)
    repo.create_notes_table()

    fake_remote_note = {
        "op_id": "49bc3c9c-f0ee-4fdf-bb94-52cc7d1d68a6",
        "uuid": "67f5de82-2bcc-481e-9bca-6b18761c7051",
        "operation_type": "create",
        "timestamp": "2025-02-01 12:00:00",
        "device_id": "6dfb9091-831c-45db-b130-a60d6b8a05a8",
        "payload": {
            "title": "Remote title",
            "contents": "Updated remotely",
            "created_at": "2025-02-01 12:00:00",
            "last_updated": "2025-02-10 21:00:00",
            "embeddings": "zczMPc3MTD6amZk+",
            "tags": "tag1",
            "deleted": 0 
        }
    }

    client = Mock()
    client.pull_changes.return_value = [fake_remote_note]

    sm = SyncManager(db, repo, client)

    sm.sync_down()

    saved = repo.get_note("67f5de82-2bcc-481e-9bca-6b18761c7051")
    assert saved is not None
    assert saved[1] == "Remote title"
