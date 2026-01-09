"""Check PostgreSQL connections and locks"""
import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'), connect_timeout=5)
cursor = conn.cursor()

print("=== Active Connections ===")
cursor.execute("""
    SELECT pid, usename, application_name, client_addr, state, query_start, query
    FROM pg_stat_activity
    WHERE datname = 'faceless_db'
    ORDER BY query_start
""")
for row in cursor.fetchall():
    print(f"\nPID: {row[0]}")
    print(f"  User: {row[1]}")
    print(f"  App: {row[2]}")
    print(f"  State: {row[4]}")
    print(f"  Query: {str(row[6])[:100]}...")

print("\n=== Blocking Locks ===")
cursor.execute("""
    SELECT blocked_locks.pid AS blocked_pid,
           blocked_activity.usename AS blocked_user,
           blocking_locks.pid AS blocking_pid,
           blocking_activity.usename AS blocking_user,
           blocked_activity.query AS blocked_statement
    FROM pg_catalog.pg_locks blocked_locks
    JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
    JOIN pg_catalog.pg_locks blocking_locks 
        ON blocking_locks.locktype = blocked_locks.locktype
        AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
        AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
        AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
        AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
        AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
        AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
        AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
        AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
        AND blocking_locks.pid != blocked_locks.pid
    JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
    WHERE NOT blocked_locks.GRANTED
""")
locks = cursor.fetchall()
if locks:
    for row in locks:
        print(f"Blocked PID {row[0]} by PID {row[2]}")
        print(f"  Query: {str(row[4])[:100]}")
else:
    print("No blocking locks found")

conn.close()
print("\nDone!")
