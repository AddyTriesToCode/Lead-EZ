"""Check history table for pipeline runs."""
import sqlite3

conn = sqlite3.connect('database/leads.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Total history
cursor.execute('SELECT COUNT(*) as count FROM history')
total_history = cursor.fetchone()['count']
print(f'Total history records: {total_history}')

# Records per pipeline run
cursor.execute('SELECT pipeline_run_id, COUNT(*) as count FROM history GROUP BY pipeline_run_id ORDER BY pipeline_run_id')
print('\nRecords per pipeline run:')
for row in cursor.fetchall():
    print(f'  {row["pipeline_run_id"]}: {row["count"]} records')

# Check for run_1768210943028_bhgcwcfgk specifically
cursor.execute('SELECT pipeline_run_id, COUNT(*) as count FROM history WHERE pipeline_run_id = ?', ('run_1768210943028_bhgcwcfgk',))
result = cursor.fetchone()
if result:
    print(f'\nPipeline run_1768210943028_bhgcwcfgk: {result["count"]} records')
else:
    print('\nPipeline run_1768210943028_bhgcwcfgk: Not found in history')

conn.close()
