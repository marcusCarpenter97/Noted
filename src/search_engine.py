import logging 
from notes_repository import NotesRepository

class SearchEngine:
    def __init__(self, notes_repo, notes_index, tokenizer):
        self.notes_repo = notes_repo
        self.notes_index = notes_index
        self.tokenizer = tokenizer

    def index_note(self, note_id):
        note = self.notes_repo.get_note(note_id)

        if note is None:
            logging.error("Could not index node with ID {note_id} because it does not exist.")
            return

        note_text = f"{note[1]} {note[2]} {note[5]}" # Merge title, body, and tags.
        tokens = self.tokenizer.tokenize(note_text)
        token_count = self.tokenizer.count(tokens)
        
        for token, count in token_count.items():
            self.notes_index.insert_token(note_id, token, count)

    def update_index(self, note_id):
        self.notes_index.delete_tokens_for_note(note_id)
        self.index_note(note_id)

    def remove_from_index(self, note_id):
        self.notes_index.delete_tokens_for_note(note_id)
