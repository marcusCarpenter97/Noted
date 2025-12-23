import pytest
from unittest.mock import Mock
from sync_manager import SyncManager


# ────────────────────────────────────────────────────────────────
#   Minimal Fakes
# ────────────────────────────────────────────────────────────────

class FakeDB:
    def __init__(self):
        self.last_updated = "2000-01-01 00:00:00"

    def get_database_cursor(self):
        return self

    def execute(self, query, params=()):
        q = query.lower()
        if "select last_updated" in q:
            self._fetchone = (self.last_updated,)
        if "update last_sync" in q:
            self.last_updated = "3000-01-01 00:00:00"
        return self

    def fetchone(self):
        return self._fetchone

    def commit_to_database(self):
        pass


class FakeNotesRepository:
    def __init__(self):
        self.notes = {}

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
        n = self.notes.get(uuid)
        if not n:
            return
        if title is not None:
            n["title"] = title
        if contents is not None:
            n["contents"] = contents
        if embeddings is not None:
            n["embeddings"] = embeddings
        if tags is not None:
            n["tags"] = tags

    def mark_note_as_deleted(self, uuid):
        if uuid in self.notes:
            self.notes[uuid]["deleted"] = True

    def get_note(self, uuid):
        return self.notes.get(uuid)

    def get_operations_since(self, ts):
        return []


class FakeRemoteAPI:
    def __init__(self):
        self.pull_result = []

    def pull_changes(self, since_ts):
        return self.pull_result


class FakeLamportClock:
    def __init__(self):
        self.time = 0

    def initialize_lamport_clock(self):
        self.time = 0

    def increment_lamport_time(self, incoming=None):
        if incoming is None:
            self.time += 1
        else:
            self.time = max(self.time + 1, incoming + 1)

    def save_lamport_time_to_db(self):
        pass

    def now(self):
        return self.time


class FakeChangeLog:
    def __init__(self):
        self.ops = {}

    def create_change_log_table(self): pass

    def check_operation_exists(self, op_id):
        return 1 if op_id in self.ops else 0

    def log_operation(self, op_id, op_type, payload, ts, origin):
        self.ops[op_id] = True


class FakeEmbeddings:
    def embed(self, text):
        return {"embedding": [0.1, 0.2, 0.3]}

# ────────────────────────────────────────────────────────────────
#   Helper: build SyncManager with minimal mocks
# ────────────────────────────────────────────────────────────────

def make_sync_manager():
    db = FakeDB()
    notes = FakeNotesRepository()
    clock = FakeLamportClock()
    change_log = FakeChangeLog()

    # minimal mocks for unused injected deps
    se = Mock()
    li = Mock()
    fe = Mock()
    ep = FakeEmbeddings()
    tl = Mock()

    return SyncManager(
        db=db,
        device_id="DEVICE",
        notes_repository=notes,
        change_log=change_log,
        lamport_clock=clock,
        se=se,
        li=li,
        fe=fe,
        ep=ep,
        transport_layer=tl
    ), notes


# ────────────────────────────────────────────────────────────────
#   TESTS
# ────────────────────────────────────────────────────────────────

def test_create_note_from_remote():
    #api = FakeRemoteAPI()
    #api.pull_result = [{
    message = [{
        "op_id": "1",
        "uuid": "A",
        "lamport_clock": 5,
        "operation_type": "create",
        "payload": {
            "title": "Hello",
            "contents": "World",
            "created_at": "2020",
            "last_updated": "2020",
            "embeddings": None,
            "tags": []
        }
    }]

    sm, notes = make_sync_manager()
    sm.sync_down("A", message)

    assert notes.get_note("A")["title"] == "Hello"


def test_update_note_from_remote():
    #api = FakeRemoteAPI()
    sm, notes = make_sync_manager()

    # local existing
    notes.insert_note("A", "Old", "Body", "2020", "2020", None, [])

    message = [{
        "op_id": "2",
        "uuid": "A",
        "lamport_clock": 10,
        "operation_type": "update",
        "payload": {"title": "New Title"}
    }]

    sm.sync_down("A", message)

    assert notes.get_note("A")["title"] == "New Title"
    assert notes.get_note("A")["contents"] == "Body"  # unchanged


def test_delete_note_from_remote():
    #api = FakeRemoteAPI()
    sm, notes = make_sync_manager()

    notes.insert_note("A", "T", "C", "2020", "2020", None, [])

    message = [{
        "op_id": "3",
        "uuid": "A",
        "lamport_clock": 7,
        "operation_type": "delete",
        "payload": {}
    }]

    sm.sync_down("A", message)

    assert notes.get_note("A")["deleted"] is True


def test_multiple_operations_in_order():
    #api = FakeRemoteAPI()
    sm, notes = make_sync_manager()

    # 1. create
    message = [{
        "op_id": "4",
        "uuid": "A",
        "lamport_clock": 1,
        "operation_type": "create",
        "payload": {
            "title": "One",
            "contents": "X",
            "created_at": "t",
            "last_updated": "t",
            "embeddings": None,
            "tags": []
        }
    }]
    sm.sync_down("A", message)
    assert notes.get_note("A")["title"] == "One"

    # 2. update
    message = [{
        "op_id": "5",
        "uuid": "A",
        "lamport_clock": 2,
        "operation_type": "update",
        "payload": {"title": "Two"}
    }]
    sm.sync_down("A", message)
    assert notes.get_note("A")["title"] == "Two"

    # 3. delete
    message = [{
        "op_id": "6",
        "uuid": "A",
        "lamport_clock": 3,
        "operation_type": "delete",
        "payload": {}
    }]
    sm.sync_down("A", message)
    assert notes.get_note("A")["deleted"] is True


def test_idempotency_operation_not_replayed():
    #api = FakeRemoteAPI()
    sm, notes = make_sync_manager()

    message = [{
        "op_id": "7",
        "uuid": "A",
        "lamport_clock": 1,
        "operation_type": "create",
        "payload": {
            "title": "Title",
            "contents": "Body",
            "created_at": "t",
            "last_updated": "t",
            "embeddings": None,
            "tags": []
        }
    }]

    sm.sync_down("A", message)
    sm.sync_down("A", message)  # same op again

    assert notes.get_note("A")["title"] == "Title"

