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

        note_text = f"{note['title']} {note['contents']} {note['tags']}"
        tokens = self.tokenizer.tokenize(note_text)
        token_count = self.tokenizer.count(tokens)
        
        rows = [(note_id, token, count) for token, count in token_count.items()]
        self.notes_index.insert_many_tokens(rows)

    def update_index(self, note_id):
        self.notes_index.delete_tokens_for_note(note_id)
        self.index_note(note_id)

    def remove_from_index(self, note_id):
        self.notes_index.delete_tokens_for_note(note_id)

    def search(self, user_query):
        query_tokens = self.tokenizer.tokenize(user_query)

        result_scores = defaultdict(int)

        for token in query_tokens:
            # Retreive all note UUIDs (and token frequency) that contain that token.
            similar_tokens = self.notes_index.retrieve_similar_tokens(token)

            # Score the UUID by token count.
            for note_id, count in similar_tokens:
                if note_id not in result_scores:
                    result_scores[note_id] = 0
                result_scores[note_id] += count

        # Return a sorted list of UUIDs based on token frequency.
        final_result = list(result_scores.items())
        return sorted(final_result, key=lambda x: x[1], reverse=True)
