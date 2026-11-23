"""Local-only exercise audit, does not certify official data or editor identities."""
from pathlib import Path
import sqlite3, json
from datetime import datetime, timezone
DB_PATH=Path(__file__).parent/'data'/'project1_events.sqlite3'

def initialize():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS event (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT NOT NULL, event_type TEXT NOT NULL, article_id TEXT,
            scenario TEXT, status TEXT NOT NULL, evidence_id TEXT, detail TEXT NOT NULL
        )""")
def record(event_type,article_id=None,scenario=None,status='recorded',evidence_id=None,detail=None):
    initialize()
    with sqlite3.connect(DB_PATH) as c:
        cursor=c.execute('INSERT INTO event (at,event_type,article_id,scenario,status,evidence_id,detail) VALUES (?,?,?,?,?,?,?)',
            (datetime.now(timezone.utc).isoformat(timespec='seconds'),event_type,article_id,
             scenario,status,evidence_id,json.dumps(detail or {},ensure_ascii=False)))
        return cursor.lastrowid
def list_events(limit=50):
    initialize()
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory=sqlite3.Row
        return [dict(x) for x in c.execute('SELECT * FROM event ORDER BY event_id DESC LIMIT ?', (min(100,max(1,limit)),))]
