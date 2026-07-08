import sqlite3

db = r'C:\Users\52161\AppData\Roaming\Code\User\globalStorage\github.copilot-chat\session-store.db'
conn = sqlite3.connect(db)

print("=== Recent Sessions ===")
rows = conn.execute("SELECT id, cwd, summary, created_at FROM sessions ORDER BY updated_at DESC LIMIT 20").fetchall()
for r in rows:
    print(f"ID={r[0]} | cwd={r[1]} | summary={str(r[2])[:80]} | created={r[3]}")

conn.close()
