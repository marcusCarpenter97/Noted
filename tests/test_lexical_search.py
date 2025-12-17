import math
import pytest
from collections import defaultdict

from search_engine import SearchEngine


@pytest.fixture
def tokenizer():
    class T:
        def tokenize(self, text):
            return text.split()
    return T()


@pytest.fixture
def notes_repo():
    class MockRepo:
        def __init__(self):
            # Pretend "A" and "B" are our example notes.
            self.notes = {
                "A": {
                    "uuid": "A",
                    "title": "hello world",
                    "contents": "foo bar foo",
                    "tags": "x,y",
                    "deleted": 0
                },
                "B": {
                    "uuid": "B",
                    "title": "bar baz",
                    "contents": "foo foo baz",
                    "tags": "z",
                    "deleted": 0
                },
            }

        def get_note(self, uuid):
            return self.notes.get(uuid)

        def get_number_of_non_deleted_notes(self):
            return 2

    return MockRepo()


@pytest.fixture
def notes_index():
    class MockIndex:
        def __init__(self):
            # term-frequency for each token in each note
            self.tf = {
                ("A", "foo"): 2,
                ("A", "bar"): 1,
                ("B", "foo"): 2,
                ("B", "bar"): 0,
            }

        def retrieve_agerage_document_length(self):
            return 5.0

        def retrieve_term_frequency_in_document(self, note_id, token):
            return self.tf.get((note_id, token), 0)

    return MockIndex()


@pytest.fixture
def lexical_index():
    class MockLexicalIndex:
        def __init__(self):
            # Simulate FTS5 lookup results
            # Each entry looks like {"note_id": "..."}
            self.results = {
                "foo": [{"note_id": "A"}, {"note_id": "B"}],
                "bar": [{"note_id": "A"}],
            }

        def search_lexical_index(self, token):
            return self.results.get(token, [])

    return MockLexicalIndex()

@pytest.fixture
def faiss_engine():
    class MockFaiss:
        def __init__(self):
            pass
    return MockFaiss()

@pytest.fixture
def emb_prov():
    class MockEmbeddingProvider:
        def __init__(self):
            pass
    return MockEmbeddingProvider()

# -------------------------------------------------------------
#                    TEST CASES
# -------------------------------------------------------------

def test_returns_empty_if_no_docs(tokenizer, notes_repo, notes_index, faiss_engine, emb_prov, lexical_index):
    # override lexical index to return zero results
    lexical_index.results = {}

    engine = SearchEngine(notes_repo, notes_index, lexical_index, faiss_engine, emb_prov, tokenizer)
    result = engine.lexical_search("foo")

    assert result == []


def test_bm25_correctly_ranks_documents(tokenizer, notes_repo, notes_index, faiss_engine, emb_prov, lexical_index):
    engine = SearchEngine(notes_repo, notes_index, lexical_index, faiss_engine, emb_prov, tokenizer)
    
    # Query: "foo"
    result = engine.lexical_search("foo")

    # Both A and B contain "foo", each tf=2.
    # But A and B have different doc lengths, so ordering might differ.
    # We at least confirm:
    # 1. Both appear
    # 2. Scores sorted largest->smallest
    assert len(result) == 2
    assert result[0][1] >= result[1][1]


def test_multiple_tokens_accumulate(tokenizer, notes_repo, notes_index, faiss_engine, emb_prov, lexical_index):
    engine = SearchEngine(notes_repo, notes_index, lexical_index, faiss_engine, emb_prov, tokenizer)

    # Query containing two tokens that both appear in A
    # foo -> A,B
    # bar -> A
    result = engine.lexical_search("foo bar")

    # A should get score(foo) + score(bar)
    # B only gets score(foo)
    score_A = dict(result)["A"]
    score_B = dict(result)["B"]

    assert score_A > score_B


def test_idf_computation_is_called_properly(tokenizer, notes_repo, notes_index, faiss_engine, emb_prov, lexical_index, monkeypatch):
    """
    We mock math.log to ensure IDF is being passed the correct numerator/denominator.
    """
    captured_value = {}

    def fake_log(x):
        captured_value["idf_argument"] = x
        return 0.0  # score irrelevant

    monkeypatch.setattr("math.log", fake_log)

    engine = SearchEngine(notes_repo, notes_index, lexical_index, faiss_engine, emb_prov, tokenizer)
    engine.lexical_search("foo")

    # total=2 notes, "foo" appears in both (2)
    # IDF arg should be: (2 - 2 + 0.5) / (2 + 0.5) = 0.5 / 2.5 = 0.2
    assert pytest.approx(captured_value["idf_argument"], 0.01) == 0.2
