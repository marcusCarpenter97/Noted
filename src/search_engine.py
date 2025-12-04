import math
import ollama
import logging
from collections import defaultdict
from notes_repository import NotesRepository
from lexical_index import LexicalIndex

class SearchEngine:
    def __init__(self, notes_repo, notes_index, lexical_index, tokenizer):
        self.notes_repo = notes_repo
        self.notes_index = notes_index
        self.lexical_index = lexical_index
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

    def lexical_search(self, user_query, k1=1.5, b=0.75):
        query_tokens = self.tokenizer.tokenize(user_query)
        total_num_notes = self.notes_repo.get_number_of_non_deleted_notes()
        average_document_length = self.notes_index.retrieve_agerage_document_length()

        bm25_scores = defaultdict(float)

        for token in query_tokens:
            # Returns all document UUIDs that contain the token.
            results = self.lexical_index.search_lexical_index(token)
            notes_containing_token = len(results)

            idf = math.log((total_num_notes-notes_containing_token+0.5)/(notes_containing_token+0.5))

            # For each document calculate its BM25 score.
            for result in results:
                note = self.notes_repo.get_note(result['note_id'])

                temp_tags = " ".join(note['tags'].split(','))
                document = f"{note['title']} {note['contents']} {temp_tags}"
                document_length = len(document.split(" "))

                local_token_count = self.notes_index.retrieve_term_frequency_in_document(note['uuid'], token)

                tf = local_token_count / (local_token_count + k1 * (1 - b + b * (document_length / average_document_length)))

                bm25_scores[note['uuid']] += (tf * idf)

        final_result = list(bm25_scores.items())
        return sorted(final_result, key=lambda x: x[1], reverse=True)

    def semantic_search(self, user_query, neighbours=100):

        responce = ollama.embedding(model="nomic-embed-text", prompt=user_query)
        embeddings = responce['embedding']

        distances, indices = self.embedding_database.search(embeddings, neighbours)

        uuids = [faiss_to_uuid[index] for index in indeices]

        results = [(uuid, distance) for uuid, ditance in zip(uuids, distances)]

        return sorted(results, key=lambda x: x[1], reverse=True)
