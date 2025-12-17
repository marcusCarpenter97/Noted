import time
import pytest
import random
import ollama
import pickle
import numpy as np
from unittest.mock import Mock
from notes_repository import NotesRepository
from embedding_provider import EmbeddingProvider
from lexical_index import LexicalIndex
from search_engine import SearchEngine
from note_index import NoteIndex
from tokenizer import Tokenizer
from faiss_engine import Faiss
from database import Database
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

random.seed(0)

@pytest.fixture(autouse=True)
def reset_db():
    Database._instance = None
    Database._initialized = None

@pytest.fixture
def fake_embedding():
    return {"embedding": [0.0] * 768}

@pytest.fixture
def emb_prov(fake_embedding):
    class MockEmbeddingProvider():
        def __init__(self, embedding):
            self.embedding = embedding

        def embed(self, text):
            return self.embedding
    return MockEmbeddingProvider(fake_embedding)

def test_index_note(fake_embedding, emb_prov):
    db = Database(":memory:") 

    li = LexicalIndex(db)
    li.create_lexical_table()
    nr = NotesRepository(db)
    nr.create_notes_table()

    emb_prov.embedding = fake_embedding
    #responce = ollama.embeddings(model="nomic-embed-text", prompt="dimension probe")
    embeddings = pickle.dumps(fake_embedding['embedding'])
    note_id = nr.create_note("Title", "Body", embeddings, "tag1")

    ni = NoteIndex(db)
    ni.create_word_index_table()

    fe = Faiss(emb_prov, nr)
    
    tok = Tokenizer()
    se = SearchEngine(nr, ni, li, fe, emb_prov, tok)

    se.index_note(note_id)

    tokens = ni.retrieve_tokens_for_note(note_id)
    assert len(tokens) == 3  # Three words in the test data.

def test_query_on_10k_notes():
    db = Database(BASE_DIR / "database" / "ten_thousand_notes.db")

    li = LexicalIndex(db)
    li.create_lexical_table()
    nr = NotesRepository(db)

    # Query one thousand random notes from the database.
    random_note_ids = random.sample(range(1, 10000), 1000)

    start = time.perf_counter()

    for note_id in random_note_ids:
        _ = nr.get_note(note_id)

    end = time.perf_counter()

    assert (end-start) <= 0.2
    assert ((end-start)/1000) <= 0.00005

def test_index_note_on_1k_notes(emb_prov):
    db = Database(BASE_DIR / "database" / "one_thousand_notes.db")

    li = LexicalIndex(db)
    li.create_lexical_table()
    nr = NotesRepository(db)
    ni = NoteIndex(db)
    ni.create_word_index_table()
    tk = Tokenizer()

    fe = Faiss(emb_prov, nr)

    se = SearchEngine(nr, ni, li, fe, emb_prov, tk)

    start = time.perf_counter()

    for note_id in range(1, 1001):
        se.index_note(note_id)

    end = time.perf_counter()

    assert (end-start) < 1

def make_engine():
    notes_repo = Mock()
    notes_index = Mock()
    lexical_index = Mock()
    faiss_engine = Mock()
    emb_prov = Mock()
    tokenizer = Mock()
    return SearchEngine(notes_repo, notes_index, lexical_index, faiss_engine, emb_prov, tokenizer), notes_repo, notes_index, lexical_index, faiss_engine, emb_prov, tokenizer

def test_search_returns_sorted_results():
    engine, repo, index, l_index, faiss_engine, emb_prov, tokenizer = make_engine()

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
    engine, repo, index, l_index, faiss_engine, emb_prov, tokenizer = make_engine()

    tokenizer.tokenize.return_value = ["nothing"]

    index.retrieve_similar_tokens.return_value = []

    result = engine.search("nothing")

    assert result == []

def test_search_calls_retrieve_similar_tokens_per_token():
    engine, repo, index, l_index, faiss_engine, emb_prov, tokenizer = make_engine()

    tokenizer.tokenize.return_value = ["a", "b"]

    index.retrieve_similar_tokens.return_value = []

    engine.search("query")

    assert index.retrieve_similar_tokens.call_count == 2
    index.retrieve_similar_tokens.assert_any_call("a")
    index.retrieve_similar_tokens.assert_any_call("b")

def test_search_accumulates_scores_correctly():
    engine, repo, index, l_index, faiss_engine, emb_prov, tokenizer = make_engine()

    tokenizer.tokenize.return_value = ["dog", "dog"]  # duplicate token

    index.retrieve_similar_tokens.return_value = [(10, 2)]

    result = engine.search("dog dog")

    # 2 occurrences * count=2 = 4
    assert result == [(10, 4)]

def test_search_tokenizes_query_once():
    engine, repo, index, l_index, faiss_engine, emb_prov, tokenizer = make_engine()

    tokenizer.tokenize.return_value = []

    engine.search("anything")

    tokenizer.tokenize.assert_called_once_with("anything")
