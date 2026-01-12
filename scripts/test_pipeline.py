"""Test script to simulate pipeline run with 10 leads."""
import requests
import json

# Test the run_pipeline endpoint directly
response = requests.post('http://localhost:8001/tools/run_pipeline', json={
    "leadCount": 10,
    "seed": 42,
    "enrichmentMode": "offline",
    "dryRun": True,
    "pipelineRunId": "test_run_123"
})

print(f"Status Code: {response.status_code}")
print(f"\nResponse:")
print(json.dumps(response.json(), indent=2))

# Check database
import sqlite3
conn = sqlite3.connect('database/leads.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM leads')
lead_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM messages')
message_count = cursor.fetchone()[0]

print(f"\n\nDatabase State:")
print(f"  Leads: {lead_count}")
print(f"  Messages: {message_count}")
print(f"  Expected: 10 leads, 40 messages (4 per lead)")

conn.close()
