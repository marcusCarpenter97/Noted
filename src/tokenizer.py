from collections import Counter

class Tokenizer:

    def tokenize(self, text):
        return text.split(" ")

    def count(self, tokens):
        return Counter(tokens)
