import ollama

class EmbeddingProvider:

    def embed(self, text, model="nomic-embed-text", max_chars=5000):
        return ollama.embeddings(model=model, prompt=text[:max_chars])
