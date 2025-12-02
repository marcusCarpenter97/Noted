import time
import pytest
import random
import numpy as np
from unittest.mock import Mock
from notes_repository import NotesRepository
from search_engine import SearchEngine
from note_index import NoteIndex
from tokenizer import Tokenizer
from database import Database

random.seed(0)

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

    tokens = ni.retrieve_tokens_for_note(note_id)
    assert len(tokens) == 3  # Three words in the test data.

def test_query_on_10k_notes():
    db = Database("ten_thousand_notes.db")

    nr = NotesRepository(db)

    # Query one thousand random notes from the database.
    random_note_ids = random.sample(range(1, 10000), 1000)

    start = time.perf_counter()

    for note_id in random_note_ids:
        _ = nr.get_note(note_id)

    end = time.perf_counter()

    assert (end-start) <= 0.2
    assert ((end-start)/1000) <= 0.00002

def test_index_note_on_1k_notes():
    db = Database("one_thousand_notes.db")

    nr = NotesRepository(db)
    ni = NoteIndex(db)
    ni.create_word_index_table()
    tk = Tokenizer()

    se = SearchEngine(nr, ni, tk)

    start = time.perf_counter()

    for note_id in range(1, 1001):
        se.index_note(note_id)

    end = time.perf_counter()

    assert (end-start) < 10  # TODO Can you lower this to 1 second?

def make_engine():
    notes_repo = Mock()
    notes_index = Mock()
    tokenizer = Mock()
    return SearchEngine(notes_repo, notes_index, tokenizer), notes_repo, notes_index, tokenizer

def test_search_returns_sorted_results():
    engine, repo, index, tokenizer = make_engine()

    tokenizer.tokenize.return_value = ["hello", "world"]

    index.retrieve_similar_tokens.side_effect = [
        [(1, 2), (2, 1)],      # results for "hello"
        [(1, 3), (3, 5)],      # results for "world"
    ]

    result = engine.search("hello world")

    assert result == [
        (1, 5),  # 2+3
        (3, 5),  # from world only
        (2, 1),
    ]

def test_search_empty_results_when_no_matches():
    engine, repo, index, tokenizer = make_engine()

    tokenizer.tokenize.return_value = ["nothing"]

    index.retrieve_similar_tokens.return_value = []

    result = engine.search("nothing")

    assert result == []

def test_search_calls_retrieve_similar_tokens_per_token():
    engine, repo, index, tokenizer = make_engine()

    tokenizer.tokenize.return_value = ["a", "b"]

    index.retrieve_similar_tokens.return_value = []

    engine.search("query")

    assert index.retrieve_similar_tokens.call_count == 2
    index.retrieve_similar_tokens.assert_any_call("a")
    index.retrieve_similar_tokens.assert_any_call("b")

def test_search_accumulates_scores_correctly():
    engine, repo, index, tokenizer = make_engine()

    tokenizer.tokenize.return_value = ["dog", "dog"]  # duplicate token

    index.retrieve_similar_tokens.return_value = [(10, 2)]

    result = engine.search("dog dog")

    # 2 occurrences * count=2 = 4
    assert result == [(10, 4)]

def test_search_tokenizes_query_once():
    engine, repo, index, tokenizer = make_engine()

    tokenizer.tokenize.return_value = []

    engine.search("anything")

    tokenizer.tokenize.assert_called_once_with("anything")
