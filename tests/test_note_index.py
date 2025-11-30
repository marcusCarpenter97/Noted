import pytest
from database import Database
from note_index import NoteIndex

@pytest.fixture(autouse=True)
def reset_db():
    Database._instance = None
    Database._initialized = None

def test_insert_token():
    db = Database(":memory:")
    n_index = NoteIndex(db)
    n_index.create_word_index_table()

    note_id = n_index.insert_token(1, "Hello", 2)
    tokens = n_index.retreive_tokens_for_note(note_id)

    assert tokens is not None
    assert len(tokens) == 1
    
