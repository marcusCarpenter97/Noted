import json
import pytest
from unittest.mock import Mock
from sync_manager import SyncManager


# ────────────────────────────────────────────────────────────────
#   Minimal Fakes
# ────────────────────────────────────────────────────────────────

class FakeDBWorker:
    def execute(self, fn, args=(), wait=False, kwargs=None):
        # call the function with a fake connection
        class FakeCursor:
            def execute(self, *args, **kwargs): pass
            def fetchone(self): return ((0,))

        class FakeConn:
            def cursor(self): return FakeCursor()
            def commit(self): pass

        result = fn(FakeConn(), *(args or ()))
        return result

class FakeNotesRepository:
    def __init__(self):
        self.notes = {}

    def insert_note(self, uuid, title, contents, created_at, last_updated, embeddings, tags):
        self.notes[uuid] = {
            "note_id": uuid,
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

def get_operation_since_lamport(self, lamport):
    return []

# ────────────────────────────────────────────────────────────────
#   Helper: build SyncManager with minimal mocks
# ────────────────────────────────────────────────────────────────

def make_sync_manager(
    mocker=None,
    *,
    db_worker=None,
    notes_repo=None,
    change_log=None,
    lamport_clock=None,
    transport_layer=None
):
    db_worker = db_worker or FakeDBWorker()
    notes_repo = notes_repo or FakeNotesRepository()
    change_log = change_log or FakeChangeLog()
    lamport_clock = lamport_clock or FakeLamportClock()

    se = Mock()
    li = Mock()
    fe = Mock()
    ep = FakeEmbeddings()

    if transport_layer is None:
        transport_layer = Mock()
        transport_layer.register_message_handler = Mock()
        transport_layer.get_peers.return_value = []
        transport_layer.push_changes = Mock()

    sm = SyncManager(
        db_worker=db_worker,
        device_id="DEVICE",
        notes_repository=notes_repo,
        change_log=change_log,
        lamport_clock=lamport_clock,
        se=se,
        li=li,
        fe=fe,
        ep=ep,
        transport_layer=transport_layer,
    )

    return sm, notes_repo

# ────────────────────────────────────────────────────────────────
#   TESTS
# ────────────────────────────────────────────────────────────────

def test_create_note_from_remote():
    #api = FakeRemoteAPI()
    #api.pull_result = [{
    message = [{
        "op_id": "1",
        "note_id": "A",
        "lamport_clock": 5,
        "operation_type": "create",
        "payload": json.dumps({
            "title": "Hello",
            "contents": "World",
            "created_at": "2020",
            "last_updated": "2020",
            "embeddings": None,
            "tags": []
        })
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
        "note_id": "A",
        "lamport_clock": 10,
        "operation_type": "update",
        "payload": json.dumps({"title": "New Title"})
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
        "note_id": "A",
        "lamport_clock": 7,
        "operation_type": "delete",
        "payload": json.dumps({})
    }]

    sm.sync_down("A", message)

    assert notes.get_note("A")["deleted"] is True


def test_multiple_operations_in_order():
    #api = FakeRemoteAPI()
    sm, notes = make_sync_manager()

    # 1. create
    message = [{
        "op_id": "4",
        "note_id": "A",
        "lamport_clock": 1,
        "operation_type": "create",
        "payload": json.dumps({
            "title": "One",
            "contents": "X",
            "created_at": "t",
            "last_updated": "t",
            "embeddings": None,
            "tags": []
        })
    }]
    sm.sync_down("A", message)
    assert notes.get_note("A")["title"] == "One"

    # 2. update
    message = [{
        "op_id": "5",
        "note_id": "A",
        "lamport_clock": 2,
        "operation_type": "update",
        "payload": json.dumps({"title": "Two"})
    }]
    sm.sync_down("A", message)
    assert notes.get_note("A")["title"] == "Two"

    # 3. delete
    message = [{
        "op_id": "6",
        "note_id": "A",
        "lamport_clock": 3,
        "operation_type": "delete",
        "payload": json.dumps({})
    }]
    sm.sync_down("A", message)
    assert notes.get_note("A")["deleted"] is True


def test_idempotency_operation_not_replayed():
    #api = FakeRemoteAPI()
    sm, notes = make_sync_manager()

    message = [{
        "op_id": "7",
        "note_id": "A",
        "lamport_clock": 1,
        "operation_type": "create",
        "payload": json.dumps({
            "title": "Title",
            "contents": "Body",
            "created_at": "t",
            "last_updated": "t",
            "embeddings": None,
            "tags": []
        })
    }]

    sm.sync_down("A", message)
    sm.sync_down("A", message)  # same op again

    assert notes.get_note("A")["title"] == "Title"


def test_sync_up_no_peers(mocker):
    transport = mocker.Mock()
    transport.get_peers.return_value = []

    sm, _ = make_sync_manager(mocker, transport_layer=transport)

    sm.sync_up()

    transport.push_changes.assert_not_called()


def test_sync_up_no_operations(mocker):
    peer = mocker.Mock(device_id="peerA")
    transport = mocker.Mock()
    transport.get_peers.return_value = [peer]

    change_log = mocker.Mock()
    change_log.get_operation_since_lamport.return_value = []

    sm, _ = make_sync_manager(
        mocker,
        transport_layer=transport,
        change_log=change_log
    )

    sm.sync_up()

    transport.push_changes.assert_not_called()


def test_sync_up_batches_operations(mocker):
    peer = mocker.Mock(device_id="peerA")
    transport = mocker.Mock()
    transport.get_peers.return_value = [peer]

    ops = [{"lamport_clock": i} for i in range(120)]

    change_log = mocker.Mock()
    change_log.get_operation_since_lamport.return_value = ops

    sm, _ = make_sync_manager(
        mocker,
        transport_layer=transport,
        change_log=change_log
    )

    sm.sync_up(batch_size=50)

    assert transport.push_changes.call_count == 3


def test_sync_up_updates_last_lamport(mocker):
    peer = mocker.Mock(device_id="peerA")
    transport = mocker.Mock()
    transport.get_peers.return_value = [peer]

    ops = [
        {"lamport_clock": 5},
        {"lamport_clock": 10},
        {"lamport_clock": 7},
    ]

    change_log = mocker.Mock()
    change_log.get_operation_since_lamport.return_value = ops

    sm, _ = make_sync_manager(
        mocker,
        transport_layer=transport,
        change_log=change_log
    )

    spy = mocker.spy(sm, "insert_peer_into_lamport_last_sync")

    sm.sync_up()

    spy.assert_called_with("peerA", 10)


def test_sync_up_does_not_update_on_failure(mocker):
    peer = mocker.Mock(device_id="peerA")
    transport = mocker.Mock()
    transport.get_peers.return_value = [peer]
    transport.push_changes.side_effect = Exception("network error")

    change_log = mocker.Mock()
    change_log.get_operation_since_lamport.return_value = [{"lamport_clock": 1}]

    sm, _ = make_sync_manager(
        mocker,
        transport_layer=transport,
        change_log=change_log
    )

    spy = mocker.spy(sm, "insert_peer_into_lamport_last_sync")

    sm.sync_up()

    spy.assert_not_called()


def test_sync_down_ignores_existing_operation(mocker):
    change_log = mocker.Mock()
    change_log.check_operation_exists.return_value = 1

    notes_repo = mocker.Mock()

    sm, _ = make_sync_manager(
        mocker,
        change_log=change_log,
        notes_repo=notes_repo
    )

    msg = [{
        "op_id": "op1",
        "note_id": "note1",
        "operation_type": "create",
        "lamport_clock": 1,
        "payload": json.dumps({})
    }]

    sm.sync_down("peerA", msg)

    notes_repo.insert_note.assert_not_called()


def test_sync_down_create_uses_remote_uuid(mocker):
    notes_repo = mocker.Mock()
    notes_repo.get_note.return_value = None

    change_log = mocker.Mock()
    change_log.check_operation_exists.return_value = 0

    sm, _ = make_sync_manager(mocker, notes_repo=notes_repo, change_log=change_log)

    msg = [{
        "op_id": "op1",
        "note_id": "note-uuid-123",
        "operation_type": "create",
        "lamport_clock": 1,
        "payload": json.dumps({
            "title": "t",
            "contents": "c",
            "tags": "",
            "created_at": "x",
            "last_updated": "y"
        })
    }]

    sm.sync_down("peerA", msg)

    notes_repo.insert_note.assert_called_once()
    assert notes_repo.insert_note.call_args[0][0] == "note-uuid-123"


def test_sync_down_update_missing_note(mocker):
    notes_repo = mocker.Mock()
    notes_repo.get_note.return_value = None

    change_log = mocker.Mock()
    change_log.check_operation_exists.return_value = 0

    sm, _ = make_sync_manager(mocker, notes_repo=notes_repo, change_log=change_log)

    msg = [{
        "op_id": "op2",
        "note_id": "note1",
        "operation_type": "update",
        "lamport_clock": 2,
        "payload": json.dumps({"title": "new"})
    }]

    sm.sync_down("peerA", msg)

    notes_repo.update_note.assert_not_called()


def test_sync_down_advances_lamport(mocker):
    lamport = mocker.Mock()
    lamport.now.return_value = 10

    change_log = mocker.Mock()
    change_log.check_operation_exists.return_value = 0

    notes_repo = mocker.Mock()
    notes_repo.get_note.return_value = None

    sm, _ = make_sync_manager(
        mocker,
        lamport_clock=lamport,
        change_log=change_log,
        notes_repo=notes_repo
    )

    msg = [{
        "op_id": "op1",
        "note_id": "note1",
        "operation_type": "create",
        "lamport_clock": 20,
        "payload": json.dumps({
            "title": "a",
            "contents": "b",
            "tags": "",
            "created_at": "x",
            "last_updated": "y"
        })
    }]

    sm.sync_down("peerA", msg)

    lamport.increment_lamport_time.assert_called_with(20)
