import string
from collections import Counter

class Tokenizer:

    def tokenize(self, text):
        no_punctuation = text.translate(str.maketrans("", "", string.punctuation))
        tokens = no_punctuation.split(" ")
        return [token for token in tokens if len(token) > 1]

    def count(self, tokens):
        return Counter(tokens)
