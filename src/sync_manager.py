import json
import logging
import pickle
from change_log_repository import ChangeLog
from notes_repository import NotesRepository
from remote_api_client import RemoteAPIClient

class SyncManager:

    def __init__(self, db_worker, device_id, notes_repository, change_log, lamport_clock, se, li, fe, ep, transport_layer):
        self.db_worker = db_worker
        self.device_id = device_id
        self.notes_repo = notes_repository
        self.change_log = change_log
        self.lamport_clock = lamport_clock
        self.search_engine = se
        self.lexical_index = li
        self.faiss_engine = fe
        self.embedding_provider = ep
        self.transport_layer = transport_layer
        self.create_last_sync_table()
        self.initialize_sync_table()
        self.transport_layer.register_message_handler(self.sync_down)

    def create_last_sync_table(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS last_sync (
                                id INTEGER PRIMARY KEY CHECK (id = 1) DEFAULT 1,
                                last_updated DATETIME)""")
        self.db_worker.execute(_op)

    def initialize_sync_table(self):
        def _op(connection):
            cursor = connection.cursor()
            # Insert if empty.
            cursor.execute("""INSERT INTO last_sync (last_updated) SELECT CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT * FROM last_sync)""")
            connection.commit()
        self.db_worker.execute(_op)

    def update_last_sync(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("UPDATE last_sync SET last_updated = CURRENT_TIMESTAMP WHERE id = 1")
            connection.commit()
        self.db_worker.execute(_op)

    def get_last_sync(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("SELECT last_updated FROM last_sync WHERE id = 1")
            return cursor.fetchone()[0]
        return self.db_worker.execute(_op, wait=True)

    def sync_up(self, batch_size=50):
        """ Send new changes to the server. """
        last_sync_at = self.get_last_sync()
        operations = self.notes_repo.get_operations_since(last_sync_at)

        try:
            for i in range(0, len(operations), batch_size):
                batch = operations[i : i + batch_size]
                result = self.transport_layer.push_changes(batch)
                logging.info(result)
        except Exception as e:
            logging.error(f"Failed to push changes: %s", e)
            return

    def sync_down(self, peer_device_id, message):
        """ Pull new changes from the server. """
        last_sync_at = self.get_last_sync()

        logging.info(f"Received from peer {message}")
        logging.info(f"Received {len(message)} notes from {peer_device_id}")

        results = sorted(message, key=lambda x: x.get('lamport_clock', 0))

        for remote_operation in results:

            if self.change_log.check_operation_exists(remote_operation['op_id']) == 1:
                continue

            local_note = self.notes_repo.get_note(remote_operation['note_id'])

            # Payload comes as a string and need to be convereted to a dictionary.
            remote_operation["payload"] = json.loads(remote_operation["payload"])

            if remote_operation['operation_type'] == 'create':
                if local_note is None:
                    self.lamport_clock.increment_lamport_time(remote_operation['lamport_clock'])
                    self.lamport_clock.save_lamport_time_to_db()

                    response = self.embedding_provider.embed(
                        f"{remote_operation['payload']['title']} {remote_operation['payload']['contents']} {remote_operation['payload']['tags']}")

                    embeddings = pickle.dumps(response['embedding'])

                    self.notes_repo.insert_note(remote_operation['note_id'], remote_operation['payload']['title'],
                                                remote_operation['payload']['contents'], remote_operation['payload']['created_at'],
                                                remote_operation['payload']['last_updated'],
                                                embeddings, remote_operation['payload']['tags'])

                    self.search_engine.index_note(remote_operation['note_id'])

                    self.lexical_index.index_note_for_lexical_search(remote_operation['note_id'],
                                                                    remote_operation['payload'].get('title', ''),
                                                                    remote_operation['payload'].get('contents', ''))
                    self.faiss_engine.add_embedding(remote_operation['note_id'], response['embedding'])

                    self.change_log.log_operation(remote_operation['op_id'],
                                                    "create", remote_operation['payload'], self.lamport_clock.now(),
                                                    self.device_id)
                    logging.info(f"Inserted note from remote with id: {remote_operation['note_id']}")
                    self.update_last_sync()
                else:
                    logging.warning(f"Could not create note because a note with this id already exists. Note id : {remote_operation['note_id']}")

            if remote_operation['operation_type'] == 'update':
                if local_note is not None:  # Use .get because parameters may not exist in update function.
                    self.lamport_clock.increment_lamport_time(remote_operation['lamport_clock'])
                    self.lamport_clock.save_lamport_time_to_db()
                    self.notes_repo.update_note(remote_operation['note_id'],
                                                remote_operation['payload'].get('title', None),
                                                remote_operation['payload'].get('contents', None),
                                                remote_operation['payload'].get('embeddings', None),
                                                remote_operation['payload'].get('tags', None))

                    self.search_engine.index_note(remote_operation['note_id'])

                    note = self.notes_repo.get_note(remote_operation['note_id'])
                    self.lexical_index.index_note_for_lexical_search(note['uuid'], note['title'], note['contents'])

                    response = self.embedding_provider.embed(f"{note['title']} {note['contents']} {note['tags']}")
                    self.faiss_engine.add_embedding(remote_operation['note_id'], response['embedding'])

                    self.change_log.log_operation(remote_operation['op_id'],
                                                    "update", remote_operation['payload'], self.lamport_clock.now(),
                                                    self.device_id)
                    logging.info(f"Succesfully updated note with id: {remote_operation['note_id']}")
                    self.update_last_sync()
                else:
                    logging.warning(f"Could not update note becuase a note with this id does not exist. Note id : {remote_operation['note_id']}")

            if remote_operation['operation_type'] == 'delete':
                if local_note is not None:
                    self.lamport_clock.increment_lamport_time(remote_operation['lamport_clock'])
                    self.lamport_clock.save_lamport_time_to_db()
                    self.notes_repo.mark_note_as_deleted(remote_operation['note_id'])
                    self.lexical_index.delete_note_from_lexical_search(remote_operation['note_id'])
                    self.search_engine.remove_from_index(remote_operation['note_id'])
                    self.faiss_engine.delete_embedding(remote_operation['note_id'])
                    self.change_log.log_operation(remote_operation['op_id'], "delete", {'deleted': 1}, self.lamport_clock.now(), self.device_id)
                    logging.info(f"Marked note for deletion with id: {remote_operation['note_id']}")
                    self.update_last_sync()
                else:
                    logging.warning(f"Could not delete note becuase a note with this id does not exist. Note id : {remote_operation['note_id']}")

    def sync(self):
        self.sync_up()
