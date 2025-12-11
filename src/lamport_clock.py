
class LamportClock:
    def __init__(self, db):
        self.db = db
        self.__lamport_time = 0

    def initialize_lamport_clock(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS lamport_clock(timestamp INTEGER PRIMARY KEY)")

        cursor.execute("SELECT timestamp FROM lamport_clock")
        row = cursor.fetchone()

        if not row:
            cursor.execute("INSERT INTO lamport_clock(timestamp) VALUES (0)")
            self.__lamport_time = 0

        if row:
            self.__lamport_time = row['timestamp']
        self.db.commit_to_database()

    def increment_lamport_time(self, remote_time=0):
        self.__lamport_time = max(self.__lamport_time, remote_time) + 1

    def save_lamport_time_to_db(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("REPLACE INTO lamport_clock(timestamp) VALUES (?)", (self.__lamport_time,))
        self.db.commit_to_database()

    def now(self):
        return self.__lamport_time
