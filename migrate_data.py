import json
import psycopg2
import os

DATABASE_URL = "postgresql://postgres:password@localhost:5433/deadline_db"

def migrate():
    with open('codebase/data/storage.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Migrate deadlines
    for d in data.get('deadlines', []):
        cur.execute(
            "INSERT INTO deadlines (id, title, course, due_date, due_relative, source, status, priority) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (d.get('id'), d.get('title'), d.get('course'), d.get('due_date'), d.get('due_relative'), d.get('source'), d.get('status'), d.get('priority'))
        )

    # Migrate notifications
    for n in data.get('notifications', []):
        cur.execute(
            "INSERT INTO notifications (id, title, summary, course, source, time_relative, content, is_read) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (n.get('id'), n.get('title'), n.get('summary'), n.get('course'), n.get('source'), n.get('time_relative'), n.get('content'), n.get('is_read'))
        )

    # Migrate documents
    for doc in data.get('documents', []):
        cur.execute(
            "INSERT INTO documents (id, name, file_type, course, source, updated_date, url) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (doc.get('id'), doc.get('name'), doc.get('file_type'), doc.get('course'), doc.get('source'), doc.get('updated_date'), doc.get('url'))
        )

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete!")

if __name__ == '__main__':
    migrate()
