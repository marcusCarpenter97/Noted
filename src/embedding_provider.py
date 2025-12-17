import ollama

class EmbeddingProvider:

    def embed(self, text, model="nomic-embed-text"):
        return ollama.embeddings(model=model, prompt=text)
