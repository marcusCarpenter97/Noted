
import pytest
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

#
# ────────────────────────────────────────────────────────────────────────────────
#   HELPERS: Fake in-memory DB and repositories
# ────────────────────────────────────────────────────────────────────────────────
#

class FakeDB:
    """A minimal fake Database that stores rows in memory instead of SQLite."""
    def __init__(self):
        self.tables = {
            "last_sync": [{"id": 1, "last_updated": "2000-01-01 00:00:00"}]
        }

    def get_database_cursor(self):
        return self

    def execute(self, query, params=()):
        query = query.lower()

        # update last_sync
        if "update last_sync" in query:
            self.tables["last_sync"][0]["last_updated"] = "3000-01-01 00:00:00"

        # select last_sync
        if "select last_updated" in query:
            self._fetchone = (self.tables["last_sync"][0]["last_updated"],)

        return self

    def fetchone(self):
        return self._fetchone

    def commit_to_database(self):
        pass


class FakeNotesRepository:
    """A fake NotesRepository with in-memory notes and change log."""
    def __init__(self):
        self.notes = {}  # uuid → payload
        self.operations = []  # operations since last sync

    #
    # ── Notes table ──────────────────────────────────────────────────────────────
    #
    def insert_note(self, uuid, title, contents, created_at, last_updated, embeddings, tags):
        self.notes[uuid] = {
            "uuid": uuid,
            "title": title,
            "contents": contents,
            "created_at": created_at,
            "last_updated": last_updated,
            "embeddings": embeddings,
            "tags": tags,
            "deleted": False,
        }

    def update_note(self, uuid, title=None, contents=None, embeddings=None, tags=None):
        note = self.notes.get(uuid)
        if not note:
            return
        if title:
            note["title"] = title
        if contents:
            note["contents"] = contents
        if embeddings:
            note["embeddings"] = embeddings
        if tags:
            note["tags"] = tags

    def mark_note_as_deleted(self, uuid):
        if uuid in self.notes:
            self.notes[uuid]["deleted"] = True

    def get_note(self, uuid):
        return self.notes.get(uuid)

    #
    # ── Change Log ──────────────────────────────────────────────────────────────
    #
    def get_operations_since(self, last_sync_timestamp):
        return self.operations


class FakeRemoteAPI:
    """Fake API that returns predetermined push/pull results."""
    def __init__(self):
        self.pull_result = []
        self.push_received = None

    def pull_changes(self, since_timestamp):
        return self.pull_result

    def push_changes(self, operations):
        self.push_received = operations
        return {"ok": True}



#
# ────────────────────────────────────────────────────────────────────────────────
#   TESTS
# ────────────────────────────────────────────────────────────────────────────────
#


def test_remote_wins_on_conflict():
    """
    Remote sends an update for a note that also exists locally.
    Since SyncManager always applies remote operations, remote wins.
    """
    db = FakeDB()
    nr = FakeNotesRepository()
    api = FakeRemoteAPI()

    # Local note
    nr.notes["A"] = {
        "uuid": "A",
        "title": "Local Title",
        "contents": "Local Contents",
        "created_at": "2020",
        "last_updated": "2020",
        "embeddings": None,
        "tags": [],
        "deleted": False,
    }

    # Remote update
    api.pull_result = [{
        "uuid": "A",
        "operation_type": "update",
        "payload": {
            "title": "Remote Title",
            "contents": "Remote Contents"
        }
    }]

    sm = SyncManager(db, nr, api)
    sm.sync_down()

    assert nr.notes["A"]["title"] == "Remote Title"
    assert nr.notes["A"]["contents"] == "Remote Contents"



def test_local_wins_if_newer_is_simulated_by_not_overwriting_on_missing_fields():
    """
    Since the current SyncManager does NOT compare timestamps,
    the only way local 'wins' is when remote does NOT send certain fields.

    If remote update lacks 'contents', local content stays.
    """
    db = FakeDB()
    nr = FakeNotesRepository()
    api = FakeRemoteAPI()

    # Local note
    nr.notes["A"] = {
        "uuid": "A",
        "title": "Local Title",
        "contents": "Local Contents",
        "created_at": "2020",
        "last_updated": "2021",
        "embeddings": None,
        "tags": [],
        "deleted": False,
    }

    # Remote update missing 'contents'
    api.pull_result = [{
        "uuid": "A",
        "operation_type": "update",
        "payload": {
            "title": "Remote Title"
        }
    }]

    sm = SyncManager(db, nr, api)
    sm.sync_down()

    # Title updated from remote
    assert nr.notes["A"]["title"] == "Remote Title"
    # Contents unchanged → "local wins"
    assert nr.notes["A"]["contents"] == "Local Contents"



def test_delete_vs_update_edge_case():
    """
    Remote says "delete", local still has the note.
    SyncManager must mark it as deleted.
    """
    db = FakeDB()
    nr = FakeNotesRepository()
    api = FakeRemoteAPI()

    nr.notes["A"] = {
        "uuid": "A",
        "title": "Local",
        "contents": "Local",
        "created_at": "2020",
        "last_updated": "2020",
        "embeddings": None,
        "tags": [],
        "deleted": False,
    }

    api.pull_result = [{
        "uuid": "A",
        "operation_type": "delete",
        "payload": {}
    }]

    sm = SyncManager(db, nr, api)
    sm.sync_down()

    assert nr.notes["A"]["deleted"] is True



def test_multiple_sync_cycles_apply_changes_in_order():
    """
    Remote sends multiple operations over multiple cycles.
    SyncManager must apply them correctly.
    """
    db = FakeDB()
    nr = FakeNotesRepository()
    api = FakeRemoteAPI()

    sm = SyncManager(db, nr, api)

    #
    # First cycle: create
    #
    api.pull_result = [{
        "uuid": "A",
        "operation_type": "create",
        "payload": {
            "title": "First",
            "contents": "Hello",
            "created_at": "2020",
            "last_updated": "2020",
            "embeddings": None,
            "tags": []
        }
    }]

    sm.sync_down()
    assert nr.get_note("A")["title"] == "First"

    #
    # Second cycle: update
    #
    api.pull_result = [{
        "uuid": "A",
        "operation_type": "update",
        "payload": {
            "title": "Second",
            "contents": "World"
        }
    }]

    sm.sync_down()
    assert nr.get_note("A")["title"] == "Second"
    assert nr.get_note("A")["contents"] == "World"

    #
    # Third cycle: delete
    #
    api.pull_result = [{
        "uuid": "A",
        "operation_type": "delete",
        "payload": {}
    }]

    sm.sync_down()
    assert nr.get_note("A")["deleted"] is True
