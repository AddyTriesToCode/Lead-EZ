"""Debug script to check message counts."""
import sqlite3

conn = sqlite3.connect('database/leads.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Total counts
cursor.execute('SELECT COUNT(*) as count FROM messages')
total_messages = cursor.fetchone()['count']

cursor.execute('SELECT COUNT(*) as count FROM leads')
total_leads = cursor.fetchone()['count']

print(f'Total messages: {total_messages}')
print(f'Total leads: {total_leads}')
print(f'Expected messages for {total_leads} leads: {total_leads * 4}')
print(f'Actual: {total_messages}')
print(f'Ratio: {total_messages / max(1, total_leads)} messages per lead\n')

# Messages per lead
cursor.execute('SELECT lead_id, COUNT(*) as msg_count FROM messages GROUP BY lead_id')
print('Messages per lead:')
for row in cursor.fetchall():
    print(f'  Lead {row["lead_id"]}: {row["msg_count"]} messages')

# Check for duplicates
cursor.execute('''
    SELECT lead_id, channel, variant, COUNT(*) as count
    FROM messages
    GROUP BY lead_id, channel, variant
    HAVING count > 1
''')
duplicates = cursor.fetchall()
if duplicates:
    print('\n⚠️ DUPLICATES FOUND:')
    for row in duplicates:
        print(f'  Lead {row["lead_id"]}, {row["channel"]}/{row["variant"]}: {row["count"]} copies')
else:
    print('\n✓ No duplicates found')

conn.close()
