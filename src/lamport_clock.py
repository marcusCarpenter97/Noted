
class LamportClock:
    def __init__(self, db):
        self.db = db
        self.lamport_time = 0

    def initialize_lamport_clock(self):
        cursor = self.db.get_database_cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS lamport_clock(timestamp INTEGER PRIMARY KEY)")

        cursor.execute("SELECT timestamp FROM lamport_clock")
        row = cursor.fetchone()

        if row:
            self.lamport_time = row['timestamp']

    def increment_lamport_time(self):
        self.lamport_time += 1
