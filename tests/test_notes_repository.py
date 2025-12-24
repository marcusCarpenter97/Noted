import pytest
import ollama
import pickle
import numpy as np
from database_worker import DBWorker
from lexical_index import LexicalIndex
from notes_repository import NotesRepository

@pytest.fixture
def clean_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = DBWorker(db_path=str(db_path))
    yield db
    db.shutdown()

@pytest.fixture
def fake_embedding():
    return {"embedding": [0.123, 0.69, 0.93]}

def test_create_note(clean_db, fake_embedding):
    notes_db = NotesRepository(clean_db)
    notes_db.create_notes_table()

    note_id = notes_db.create_note("Title", "Body", pickle.dumps(fake_embedding['embedding']), "tag1")
    note = notes_db.get_note(note_id)

    assert note is not None
    assert note[1] == "Title"

def test_get_note_not_found(clean_db):
    notes_db = NotesRepository(clean_db)
    notes_db.create_notes_table()
    assert notes_db.get_note(0) is None

def test_get_note_deleted_note_is_still_returned(clean_db, fake_embedding):
    notes_db = NotesRepository(clean_db)
    notes_db.create_notes_table()
    note_id = notes_db.create_note("Title", "Body", pickle.dumps(fake_embedding['embedding']), "tag1")
    notes_db.mark_note_as_deleted(note_id)
    note = notes_db.get_note(note_id)
    assert note is not None
    assert note['deleted'] == 1

def test_list_all_notes_with_deleted(clean_db):
    notes_db = NotesRepository(clean_db)
    notes_db.create_notes_table()
    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    notes_db.mark_note_as_deleted(note_id)
    result = notes_db.list_all_notes(include_deleted=True)
    assert len(result) == 2

def test_list_all_notes_without_deleted(clean_db):
    notes_db = NotesRepository(clean_db)
    notes_db.create_notes_table()
    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    notes_db.mark_note_as_deleted(note_id)
    result = notes_db.list_all_notes(include_deleted=False)
    assert len(result) == 1

def test_mark_note_as_deleted_sets_flag(clean_db):
    notes_db = NotesRepository(clean_db)
    notes_db.create_notes_table()
    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = notes_db.create_note("Title", "Body", fake_embedding, "tag1")
    notes_db.mark_note_as_deleted(note_id)
    note = notes_db.get_note(note_id)
    assert note is not None
    assert note['deleted'] == 1

def test_update_note(clean_db, fake_embedding):
    notes_db = NotesRepository(clean_db)
    notes_db.create_notes_table()

    note_id = notes_db.create_note("Title", "Body", pickle.dumps(fake_embedding['embedding']), "tag1")
    notes_db.update_note(note_id, title="New Title")

    note = notes_db.get_note(note_id)
    assert note is not None
    assert note[1] == "New Title"
