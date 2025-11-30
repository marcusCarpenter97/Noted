import logging
from collections import defaultdict
from notes_repository import NotesRepository

class SearchEngine:
    def __init__(self, notes_repo, notes_index, tokenizer):
        self.notes_repo = notes_repo
        self.notes_index = notes_index
        self.tokenizer = tokenizer

    def index_note(self, note_id):
        note = self.notes_repo.get_note(note_id)

        if note is None:
            logging.error(f"Could not index node with ID {note_id} because it does not exist.")
            return

        note_text = f"{note[1]} {note[2]} {note[5]}" # Merge title, body, and tags.
        tokens = self.tokenizer.tokenize(note_text)
        token_count = self.tokenizer.count(tokens)
        
        for token, count in token_count.items():
            self.notes_index.insert_token(note_id, token, count, commit=False)

        self.notes_index.commit_to_database()

    def update_index(self, note_id):
        self.notes_index.delete_tokens_for_note(note_id)
        self.index_note(note_id)

    def remove_from_index(self, note_id):
        self.notes_index.delete_tokens_for_note(note_id)

    def search(self, user_query):
        query_tokens = self.tokenizer.tokenize(user_query)

        result_scores = defaultdict(int)

        for token in query_tokens:
            similar_tokens = self.notes_index.retrieve_similar_tokens(token)

            for note_id, count in similar_tokens:
                if note_id not in result_scores:
                    result_scores[note_id] = 0
                result_scores[note_id] += count

        final_result = list(result_scores.items())
        return sorted(final_result, key=lambda x: x[1], reverse=True)
