import pickle
import logging
from faiss_engine import Faiss
from tokenizer import Tokenizer
from note_index import NoteIndex
from database_worker import DBWorker
from sync_manager import SyncManager
from lamport_clock import LamportClock
from search_engine import SearchEngine
from lexical_index import LexicalIndex
from installation_wizard_cli import run_wizard_cli
from device_identification import DeviceID
from transport_layer import TransportLayer
from change_log_repository import ChangeLog
from notes_repository import NotesRepository
from peer_to_peer import advertise, discover
from embedding_provider import EmbeddingProvider

def print_note(note):
    print("UUID: ", note['uuid'])
    print("Title: ", note['title'])
    print("Contents: ", note['contents'])
    print("Created at: ", note['created_at'])
    print("Last updated: ", note['last_updated'])
    print("Tags: ", note['tags'])
    print("Deleted: ", note['deleted'])
    print()

def main(db_worker, device_id, transport_layer):

    embedding_prov = EmbeddingProvider()

    lamport_clock = LamportClock(db_worker)
    lamport_clock.initialize_lamport_clock()

    notes_db = NotesRepository(db_worker)
    notes_db.create_notes_table()

    note_index = NoteIndex(db_worker)
    note_index.create_word_index_table()

    lexical_index = LexicalIndex(db_worker)
    lexical_index.create_lexical_table()

    change_log = ChangeLog(db_worker, device_id)
    change_log.create_change_log_table()

    faiss_engine = Faiss(embedding_prov, notes_db)

    tokenizer = Tokenizer()

    search_engine = SearchEngine(notes_db, note_index, lexical_index, faiss_engine, embedding_prov, tokenizer)

    synchronization_manager = SyncManager(db_worker, device_id, notes_db,
                                          change_log, lamport_clock,
                                          search_engine, lexical_index,
                                          faiss_engine, embedding_prov,
                                          transport_layer)

    synchronization_manager.create_last_sync_table()
    synchronization_manager.initialize_sync_table()
    synchronization_manager.create_lamport_last_sync_table()

    while True:
        user_choice = input(
            "Choose an option:\n1. Enter a new note\n2. Search for a note\n3. Edit a note\n4. Delete a note\n5. List all\n6. Sync\nYour choice: ")

        if user_choice == '1':
            print("Enter the data for your note or leave it blank.")
            title = input("Choose a title for your note: ")
            contents = input("Enter the contents of your note: ")
            tags = input("Enter comma separated tags for your note: ")

            responce = embedding_prov.embed(f"{title} {contents} {tags}")
            embeddings = pickle.dumps(responce['embedding'])

            note_id = notes_db.create_note(title, contents, embeddings, tags)

            search_engine.index_note(note_id)
            lexical_index.index_note_for_lexical_search(note_id, title, contents)
            faiss_engine.add_embedding(note_id, responce['embedding'])

            # Convert the SQLite row object into a dictionary.
            note_as_dict = dict(notes_db.get_note(note_id))

            lamport_clock.increment_lamport_time()
            lamport_clock.save_lamport_time_to_db()
            change_log.log_operation(note_id, "create", note_as_dict, lamport_clock.now(), device_id)
            print(f"You successfully entered a note with an ID of {note_id}")

        elif user_choice == '2':
            search_params = input("Enter search parameters: ")

            top_results = search_engine.hybrid_search(search_params)

            if top_results is None:
                print("Database is empty, could not search.")
                continue

            if len(top_results) == 0:
                print("No search results found.")
                continue

            for res in top_results:
                note = notes_db.get_note(res[0])
                print_note(note)

        elif user_choice == '3':
            note_id = input("Enter ID of note to edit: ")
            title = input("Enter a new title (or leave blank to remain unchanged): ")
            contents = input("Enter the new contents (or leave blank): ")
            tags = input("Enter the new tags (or leave blank): ")
            title = title if title.strip() != "" else None
            contents = contents if contents.strip() != "" else None
            tags = tags if tags.strip() != "" else None

            old_note = notes_db.get_note(note_id)

            change_as_json = {}
            # Build the change log with only what's changed.
            if title is not None:
                change_as_json['title'] = title
            if contents is not None:
                change_as_json['contents'] = contents
            if tags is not None:
                change_as_json['tags'] = tags

            # Build the note merging old and new contents.
            if title is None:
                title = old_note['title']
            if contents is None:
                contents = old_note['contents']
            if tags is None:
                tags = old_note['tags']

            responce = embedding_prov.embed(f"{title} {contents} {tags}")
            embeddings = pickle.dumps(responce['embedding'])

            notes_db.update_note(note_id, title, contents, embeddings, tags)
            lexical_index.index_note_for_lexical_search(note_id, title, contents)
            search_engine.update_index(note_id)

            faiss_engine.update_embedding(note_id, responce['embedding'])

            change_as_json['embeddings'] = embeddings
            lamport_clock.increment_lamport_time()
            lamport_clock.save_lamport_time_to_db()
            change_log.log_operation(note_id, "update", change_as_json, lamport_clock.now(), device_id)

            print("Note updated.")

        elif user_choice == '4':
            note_id = input("Enter ID of note to delete: ")
            notes_db.mark_note_as_deleted(note_id)
            lexical_index.delete_note_from_lexical_search(note_id)
            search_engine.remove_from_index(note_id)
            faiss_engine.delete_embedding(note_id)
            lamport_clock.increment_lamport_time()
            lamport_clock.save_lamport_time_to_db()
            change_log.log_operation(note_id, "delete", {"deleted": 1}, lamport_clock.now(), device_id)
            print(f"Note {note_id} marked as deleted.")

        elif user_choice == '5':
            print("\nPrinting all notes in the database...\n")
            for note in notes_db.list_all_notes():
                print_note(note)

        elif user_choice == '6':
            synchronization_manager.sync()

        else:
            print("\nInvalid choice. Try again or press ctrl c to exit.\n")

if __name__ == "__main__":

    logging.basicConfig(handlers=[logging.StreamHandler(), logging.FileHandler("noted.log")],
                        level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    logging.captureWarnings(True)

    print("\nWelcome to Noted.\n")

    device_name = input("New device detected. Enter device name: ")

    db_worker = DBWorker()

    device = DeviceID(db_worker)
    device_id = device.get_or_generate_device_id()
    private_key, public_key = device.get_or_generate_public_private_keys()

    transport_layer = TransportLayer(device_id, public_key, private_key)
    transport_layer.run_tcp_server()

    advertiser, info = advertise(device_id, public_key, device_name)
    discoverer = discover(device_id, transport_layer)

    try:
        run_wizard_cli()
        main(db_worker, device_id, transport_layer)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        logging.info("Closing database ...")
        db_worker.shutdown()
        logging.info("Unregistering device ...")
        advertiser.unregister_service(info)
        advertiser.close()
        discoverer.close()
        raise SystemExit
