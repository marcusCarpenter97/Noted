import pytest
import numpy as np
from notes_repository import NotesRepository
from search_engine import SearchEngine
from note_index import NoteIndex
from tokenizer import Tokenizer
from database import Database

@pytest.fixture(autouse=True)
def reset_db():
    Database._instance = None
    Database._initialized = None

def test_index_note():
    db = Database(":memory:") 

    nr = NotesRepository(db)
    nr.create_notes_table()

    fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()
    note_id = nr.create_note("Title", "Body", fake_embedding, "tag1")

    ni = NoteIndex(db)
    ni.create_word_index_table()
    
    tok = Tokenizer()
    se = SearchEngine(nr, ni, tok)

    se.index_note(note_id)

    tokens = ni.retreive_tokens_for_note(note_id)
    assert len(tokens) == 3  # Three words in the test data.
