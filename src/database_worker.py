import os
import queue
import sqlite3
import logging
import threading

DATABASE_PATH = os.environ.get("DB_PATH", 'database/database.db')

class DBWorker:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        logging.info("Database worker thread started.")

        while True:
            item = self.queue.get()
            if item is None:
                break

            fn, args, kwargs, result_q = item
            try:
                result = fn(self.connection, *args, **kwargs)
                if result_q:
                    result_q.put(result)
            except Exception as e:
                logging.exception("Database operation failed.")
                if result_q:
                    result_q.put(e)

    def execute(self, fn, args=(), wait=False, kwargs={}):
        result_q = queue.Queue() if wait else None
        self.queue.put((fn, args, kwargs, result_q))
        if wait:
            result = result_q.get()
            if isinstance(result, Exception):
                raise result
            return result

    def shutdown(self):
        self.queue.put(None)
        self.thread.join()
