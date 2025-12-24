import pytest
from database_worker import DBWorker
from lexical_index import LexicalIndex

@pytest.fixture
def clean_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = DBWorker(db_path=str(db_path))
    yield db
    db.shutdown()

def test_index_note_for_lexical_search(clean_db):

    li = LexicalIndex(clean_db)
    li.create_lexical_table()
    li.index_note_for_lexical_search("abc", "Title", "contents")
    result = li.get_note_from_lexical_index("abc")
    assert result['note_id'] == "abc"
    assert result['title'] == "Title"
    assert result['contents'] == "contents"

def test_delete_note_from_lexical_search(clean_db):

    li = LexicalIndex(clean_db)
    li.create_lexical_table()
    li.index_note_for_lexical_search("abc", "Title", "contents")
    li.delete_note_from_lexical_search("abc")
    result = li.get_note_from_lexical_index("abc")
    assert result is None

def test_search_lexical_index(clean_db):

    li = LexicalIndex(clean_db)
    li.create_lexical_table()
    li.index_note_for_lexical_search("abc", "Title", "Some contents for my personal note.")
    result = li.search_lexical_index("contents")
    result = result[0]
    assert result['note_id'] == "abc"
