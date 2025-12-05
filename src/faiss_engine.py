import faiss
import pickle
import ollama
import numpy as np

class Faiss:
    def __init__(self, notes_repository):
        self.notes_repo = notes_repository

        self.embedding_dim = self._get_embedding_dimension()
        self.embedding_database = faiss.IndexFlatL2(self.embedding_dim)

        self.faiss_to_uuid = []
        self.initialize_faiss_index()

    def _get_embedding_dimension(self):
        sample = ollama.embeddings(model="nomic-embed-text", prompt="dimension probe")
        return len(sample["embedding"])

    def initialize_faiss_index(self):
        """ Assumes FAISS is empty otherwise it will append to existing data. """
        all_notes = self.notes_repo.list_all_notes()

        for note in all_notes:
            if note['embeddings'] is None:
                continue
            vector = pickle.loads(note["embeddings"])
            self.embedding_database.add(np.array([vector], dtype="float32"))
            self.faiss_to_uuid.append(note["uuid"])

    def add_embedding(self, uuid, vector):
        self.embedding_database.add(np.array([vector], dtype="float32"))
        self.faiss_to_uuid.append(uuid)

    def delete_embedding(self, uuid):
        faiss_index = self.faiss_to_uuid.index(uuid)
        faiss_index = np.array([faiss_index])
        self.embedding_database.remove_ids(fiass_index)
        self.faiss_to_uuis.remove(uuid)

    def update_embedding(self, uuid, vector):
        self.delete_embedding(uuid)
        self.add_embedding(uuid, vector)

    def search(self, embedding_vector, k):
        return self.embedding_database.search(embedding_vector, k)
