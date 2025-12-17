import math
import logging
import numpy as np
from collections import defaultdict

class SearchEngine:
    def __init__(self, notes_repo, notes_index, lexical_index, faiss_engine, emb_prov, tokenizer):
        self.notes_repo = notes_repo
        self.notes_index = notes_index
        self.lexical_index = lexical_index
        self.embedding_database = faiss_engine
        self.embedding_provider = emb_prov
        self.tokenizer = tokenizer

    def index_note(self, note_id):
        note = self.notes_repo.get_note(note_id)

        if note is None:
            logging.error(f"Could not index node with ID {note_id} because it does not exist.")
            return

        note_text = f"{note['title']} {note['contents']} {note['tags']}"  # TODO should tags be split? They are comma separated.
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

    def semantic_search(self, user_query, neighbours=10):

        responce = self.embedding_provider.embed(user_query)
        embeddings = np.array(responce['embedding'])
        embeddings = embeddings.reshape(1, embeddings.shape[0])

        distances, indices = self.embedding_database.search(embeddings, neighbours)

        distances = distances.flatten()
        indices = indices.flatten()

        if not self.embedding_database.faiss_to_uuid:
            logging.warning("Semantic database is empty. Could not search semanticaly.")
            return

        # If we find unretreived indices in the results store their positions.
        if any(x == -1 for x in indices):
            positions = [i for i, v in enumerate(indices) if v == -1]
            indices = np.delete(indices, positions)
            distances = np.delete(distances, positions)

        uuids = [self.embedding_database.faiss_to_uuid[index] for index in indices]

        results = [(uuid, distance) for uuid, distance in zip(uuids, distances)]

        return sorted(results, key=lambda x: x[1])

    def hybrid_search(self, user_query, alpha=0.5):
        lexical_results = self.lexical_search(user_query)
        semantic_results = self.semantic_search(user_query)

        if not lexical_results and semantic_results is None:
            logging.warning("Could not perform hybid search, database is empty.")
            return

        def normalize_scores(results):
            min_score = min(results, key=lambda x: x[1])[1]
            max_score = max(results, key=lambda x: x[1])[1]
            normalized_scores = defaultdict(float)

            # Sometimes there is only one results or a tie between results
            # that would yield the min/max functions to return the same
            # value causing a vivision by 0.
            if min_score == max_score:
                for note_id, _ in results:
                    normalized_scores[note_id] = 1.0
                return normalized_scores

            for note_id, score in results:
                normalized_scores[note_id] = (score - min_score) / (max_score - min_score)
            return normalized_scores

        normalized_lexical_scores = defaultdict(float)
        normalized_semantic_scores = defaultdict(float)

        if lexical_results:
            normalized_lexical_scores = normalize_scores(lexical_results)

        if semantic_results:
            normalized_semantic_scores = normalize_scores(semantic_results)

        all_note_ids = []
        for note_id, _ in lexical_results:
            all_note_ids.append(note_id)

        for note_id, _ in semantic_results:
            all_note_ids.append(note_id)

        all_note_ids = set(all_note_ids)
        combined_scores = {}

        for note_id in all_note_ids:
            lex_score = normalized_lexical_scores.get(note_id, 0)
            sem_score = normalized_semantic_scores.get(note_id, 0)
            combined_scores[note_id] = {"lexical": lex_score, "semantic": sem_score}

        hybrid_scores = []
        for note_id in combined_scores:
            lex_score = combined_scores[note_id]["lexical"]
            sem_score = combined_scores[note_id]["semantic"]
            hybrid_score = alpha * lex_score + (1-alpha) * sem_score
            hybrid_scores.append((note_id, hybrid_score))

        return sorted(hybrid_scores, key=lambda x: x[1], reverse=True)
