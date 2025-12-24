import pytest
from note_index import NoteIndex
from database_worker import DBWorker

@pytest.fixture
def clean_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = DBWorker(db_path=str(db_path))
    yield db
    db.shutdown()

def test_insert_token(clean_db):
    n_index = NoteIndex(clean_db)
    n_index.create_word_index_table()

    note_id = n_index.insert_token(1, "Hello", 2)
    tokens = n_index.retrieve_tokens_for_note(note_id)

    assert tokens is not None
    assert len(tokens) == 1
    
