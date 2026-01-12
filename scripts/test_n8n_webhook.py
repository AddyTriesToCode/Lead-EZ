"""Test sending config to n8n webhook."""
import requests
import json

config = {
    "leadCount": 10,
    "seed": 82,
    "enrichmentMode": "offline",
    "dryRun": True,
    "pipelineRunId": "test_manual_123"
}

payload = {
    "trigger": "test",
    "timestamp": "2026-01-12T00:00:00Z",
    "config": config
}

print("Sending to n8n webhook:")
print(json.dumps(payload, indent=2))
print("\n" + "="*50 + "\n")

try:
    response = requests.post('http://localhost:5678/webhook/run-pipeline', json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
