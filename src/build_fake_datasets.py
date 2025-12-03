import time
import random
import numpy as np
from wonderwords import RandomWord
from database import Database
from notes_repository import NotesRepository

random.seed(0)

def build_fake_database(notes_repository, number_of_notes):

    def build_a_note():
        title_size = random.randint(5, 10)
        body_size = random.randint(20, 200)
        tag_size = random.randint(1, 5)

        rand_words = RandomWord()

        title = " ".join([rand_words.word() for _ in range(title_size)])
        body = " ".join([rand_words.word() for _ in range(body_size)])
        tag = " ".join([rand_words.word() for _ in range(tag_size)])
        fake_embedding = np.array([0.123, 0.69, 0.93]).astype('float32').tobytes()

        return notes_repository.create_note(title, body, fake_embedding, tag)

    for _ in range(number_of_notes):
        _ = build_a_note()

if __name__ == "__main__":

    # This scritp takes over half an hour to run on a core-i7 laptop.

    db = Database("ten_thousand_notes.db")

    nr = NotesRepository(db)
    nr.create_notes_table()

    start_time = time.perf_counter()
    build_fake_database(nr, 10000)
    end_time = time.perf_counter()
    print(f"Time take to build database with 10000 notes was of: {end_time-start_time} seconds")

    Database._instance = None
    Database._initialized = None

    db = Database("one_thousand_notes.db")

    nr = NotesRepository(db)
    nr.create_notes_table()

    start_time = time.perf_counter()
    build_fake_database(nr, 1000)
    end_time = time.perf_counter()
    print(f"Time take to build database with 1000 notes was of: {end_time-start_time} seconds")
