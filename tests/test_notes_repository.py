import pytest
import numpy as np
from database import Database
from notes_repository import NotesRepository

@pytest.fixture(autouse=True)
def reset_db():
    Database._instance = None
    Database._initialized = None

def test_create_note():
    db = Database(":memory:")
    notes_db = NotesRepository(db)
    notes_db.create_notes_table()

    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    note = notes_db.get_note(note_id)

    assert note is not None
    assert note[1] == "Title"

def test_get_note_not_found():
    db = Database(":memory:")
    notes_db = NotesRepository(db)
    notes_db.create_notes_table()
    assert notes_db.get_note(0) is None

def test_get_note_deleted_note_is_still_returned():
    db = Database(":memory:")
    notes_db = NotesRepository(db)
    notes_db.create_notes_table()
    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    notes_db.mark_note_as_deleted(note_id)
    note = notes_db.get_note(note_id)
    assert note is not None
    assert note[-1] == 1

def test_list_all_notes_with_deleted():
    db = Database(":memory:")
    notes_db = NotesRepository(db)
    notes_db.create_notes_table()
    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    notes_db.mark_note_as_deleted(note_id)
    result = notes_db.list_all_notes(include_deleted=True)
    assert len(result) == 2

def test_list_all_notes_without_deleted():
    db = Database(":memory:")
    notes_db = NotesRepository(db)
    notes_db.create_notes_table()
    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    notes_db.mark_note_as_deleted(note_id)
    result = notes_db.list_all_notes(include_deleted=False)
    assert len(result) == 1

def test_mark_note_as_deleted_sets_flag():
    db = Database(":memory:")
    notes_db = NotesRepository(db)
    notes_db.create_notes_table()
    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    notes_db.mark_note_as_deleted(note_id)
    note = notes_db.get_note(note_id)
    assert note is not None
    assert note[-1] == 1

def test_update_note():
    db = Database(":memory:")
    notes_db = NotesRepository(db)
    notes_db.create_notes_table()
    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    notes_db.update_note(note_id, title="New Title")

    note = notes_db.get_note(note_id)
    assert note is not None
    assert note[1] == "New Title"

def test_get_notes_since_last_sync():
    db = Database(":memory:")
    repo = NotesRepository(db)
    repo.create_notes_table()

    # Insert 3 notes with known timestamps
    cursor = db.get_database_cursor()

    cursor.execute(
        "INSERT INTO notes (uuid, title, contents, last_updated, embeddings, tags) "
        "VALUES ('abc', 'A', 'x', '2025-01-01 10:00:00', ?, 't')", (b'x',)
    )
    cursor.execute(
        "INSERT INTO notes (uuid, title, contents, last_updated, embeddings, tags) "
        "VALUES ('def', 'B', 'y', '2025-01-02 10:00:00', ?, 't')", (b'y',)
    )
    cursor.execute(
        "INSERT INTO notes (uuid, title, contents, last_updated, embeddings, tags) "
        "VALUES ('ghi', 'C', 'z', '2025-01-03 10:00:00', ?, 't')", (b'z',)
    )
    db.commit_to_database()

    # Call function
    result = repo.get_notes_since_last_sync("2025-01-02 00:00:00")

    # Expect notes B and C (id 2 and 3)
    ids = [row['uuid'] for row in result]
    assert ids == ['def', 'ghi']
