import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

class Store:
    """Short independent transactions; compatible with the original SQLite file."""
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, at TEXT, action TEXT, detail TEXT);
            CREATE TABLE IF NOT EXISTS target(email TEXT PRIMARY KEY, body TEXT, run_id TEXT, record_id TEXT);
            CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY);''')

    def connect(self):
        class ClosingConnection(sqlite3.Connection):
            def __exit__(self, *args):
                try:
                    return super().__exit__(*args)
                finally:
                    self.close()
        db = sqlite3.connect(self.path, timeout=10, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        return db

    def save(self, run):
        with self.connect() as db:
            db.execute('INSERT INTO runs VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body', (run['id'], json.dumps(run)))

    def get(self, run_id):
        with self.connect() as db:
            row = db.execute('SELECT body FROM runs WHERE id=?', (run_id,)).fetchone()
            return json.loads(row['body']) if row else None

    def runs(self):
        with self.connect() as db:
            return [json.loads(r['body']) for r in db.execute('SELECT body FROM runs ORDER BY rowid DESC')]

    def audit(self, run, action, detail):
        with self.connect() as db:
            db.execute('INSERT INTO audit(run_id,at,action,detail) VALUES(?,?,?,?)', (run['id'], now(), action, json.dumps(detail)))

    def events(self, run_id):
        with self.connect() as db:
            return [dict(r, detail=json.loads(r['detail'])) for r in db.execute('SELECT * FROM audit WHERE run_id=? ORDER BY seq DESC', (run_id,))]

    def target_count(self, run_id):
        with self.connect() as db:
            return db.execute('SELECT count(*) FROM target WHERE run_id=?', (run_id,)).fetchone()[0]
