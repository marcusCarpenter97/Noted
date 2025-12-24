
class LamportClock:
    def __init__(self, db_worker):
        self.db_worker = db_worker
        self.__lamport_time = 0

    def initialize_lamport_clock(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS lamport_clock(timestamp INTEGER PRIMARY KEY)")

            cursor.execute("SELECT timestamp FROM lamport_clock")
            row = cursor.fetchone()

            if not row:
                cursor.execute("INSERT INTO lamport_clock(timestamp) VALUES (0)")
                self.__lamport_time = 0

            if row:
                self.__lamport_time = row['timestamp']
            connection.commit()
        self.db_worker.execute(_op)

    def increment_lamport_time(self, remote_time=0):
        self.__lamport_time = max(self.__lamport_time, remote_time) + 1

    def save_lamport_time_to_db(self):
        def _op(connection):
            cursor = connection.cursor()
            cursor.execute("REPLACE INTO lamport_clock(timestamp) VALUES (?)", (self.__lamport_time,))
            connection.commit()
        self.db_worker.execute(_op)

    def now(self):
        return self.__lamport_time
