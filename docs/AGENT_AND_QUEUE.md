# Lead-EZ Agent & Queue System

## Overview
This implementation includes:
1. **Message Queue System** - Batch-fetches and rate-limits message delivery
2. **Agent Decision Engine** - Determines next action based on status fields
3. **MCP Server** - Exposes tool endpoints for n8n integration
4. **n8n Workflow** - Orchestrates the entire pipeline

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      n8n Workflow                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Schedule   │ -> │  Get Stats   │ -> │    Agent     │  │
│  │   Trigger    │    │  (DB Query)  │    │   Decision   │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                   │          │
│                                    ┌──────────────▼──────┐  │
│                                    │  IF Decision Node   │  │
│                                    └──┬──────────────┬───┘  │
│                                       │              │      │
│                             ┌─────────▼───┐    ┌────▼────┐ │
│                             │  Wait (None)│    │  Call   │ │
│                             └─────────────┘    │   MCP   │ │
│                                                └────┬────┘ │
└────────────────────────────────────────────────────┼──────┘
                                                      │
                 ┌────────────────────────────────────▼─────┐
                 │            MCP Server (Port 8001)         │
                 │  ┌──────────────────────────────────┐    │
                 │  │  Tools:                          │    │
                 │  │  - /tools/generate_leads         │    │
                 │  │  - /tools/enrich_leads           │    │
                 │  │  - /tools/generate_messages      │    │
                 │  │  - /tools/review_messages        │    │
                 │  │  - /tools/send_messages          │    │
                 │  │  - /tools/agent_decide           │    │
                 │  │  - /tools/get_stats              │    │
                 │  └──────────────────────────────────┘    │
                 └──────────────────┬────────────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │     Message Queue Service      │
                    │  - Batch fetch (50 at a time)  │
                    │  - In-memory queue             │
                    │  - Rate limiting (10/min)      │
                    │  - Auto-refill when low        │
                    └───────────────┬────────────────┘
                                    │
                            ┌───────▼────────┐
                            │   Database     │
                            │  leads.db      │
                            └────────────────┘
```

---

## Components

### 1. Message Queue (`backend/services/message_queue.py`)

**Purpose:** Batch-fetch and rate-limit message delivery

**Features:**
- Batch fetches 50 messages at a time from DB
- Holds messages in-memory (deque)
- Rate limiting: 10 messages/minute (configurable)
- Auto-refills when queue drops below threshold
- Batch status updates after sending

**Usage:**
```python
from backend.services.message_queue import get_message_queue

# Get queue instance
queue = get_message_queue(batch_size=50, max_per_minute=10)

# Fetch batch
queue.fetch_batch(status="APPROVED")

# Process with rate limiting
async def sender(message):
    # Your email/LinkedIn sending logic
    return True

result = await queue.process_with_rate_limit(sender, dry_run=False)
print(f"Sent: {result['sent']}, Failed: {result['failed']}")
```

---

### 2. Agent Decision Engine (`backend/agent/decision_engine.py`)

**Purpose:** Determine next MCP tool endpoint based on status

**Decision Logic:**
```
NEW         -> /tools/generate_leads
GENERATED   -> /tools/enrich_leads
ENRICHED    -> /tools/generate_messages
MESSAGED    -> /tools/review_messages
PENDING     -> /tools/review_messages
APPROVED    -> /tools/send_messages
SENT        -> complete
FAILED      -> /tools/retry_failed
```

**Usage:**
```python
from backend.agent.decision_engine import AgentDecisionEngine

# Single decision
decision = AgentDecisionEngine.decide_next_action(
    lead_status="ENRICHED",
    message_status=None
)
print(decision)
# {
#   "action": "generate_messages",
#   "endpoint": "/tools/generate_messages",
#   "method": "POST",
#   "params": {}
# }

# Batch decisions
items = [
    {"lead_status": "NEW", "lead_id": "123"},
    {"lead_status": "ENRICHED", "lead_id": "456"}
]
actions = AgentDecisionEngine.batch_decide(items)
```

**n8n Code Node:**
The module includes ready-to-use JavaScript code for n8n Code nodes. See the `n8n_agent_node_code()` function for copy-paste code.

---

### 3. MCP Server (`backend/mcp/server.py`)

**Purpose:** FastAPI server exposing tool endpoints for n8n

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/tools` | GET | List all tools |
| `/tools/generate_leads` | POST | Generate leads |
| `/tools/enrich_leads` | POST | Enrich leads |
| `/tools/generate_messages` | POST | Generate messages (confidence >= 55) |
| `/tools/review_messages` | POST | Review & approve |
| `/tools/send_messages` | POST | Send via queue |
| `/tools/agent_decide` | POST | Agent decision |
| `/tools/get_stats` | GET | Pipeline stats |

**Start Server:**
```bash
python -m backend.mcp.server
```

Or:
```python
from backend.mcp.server import start_mcp_server
start_mcp_server(host="localhost", port=8001)
```

---

### 4. n8n Workflow (`automation/n8n_agent_workflow.json`)

**Purpose:** Orchestrate the entire pipeline

**Workflow Steps:**

1. **Schedule Trigger** - Runs every 5 minutes
2. **Get Pipeline Stats** - HTTP GET `/tools/get_stats`
3. **Agent Decision Node** - JavaScript code that:
   - Examines lead/message counts by status
   - Prioritizes actions (send > review > generate > enrich)
   - Decides next endpoint to call
4. **Should Wait?** - IF node checks if action = "wait"
5. **Wait - No Action** - Logs "nothing to do"
6. **Call MCP Tool** - HTTP POST to chosen endpoint
7. **Log Result** - Logs success/failure

**Import to n8n:**
1. Open n8n
2. Go to Workflows → Import from File
3. Select `automation/n8n_agent_workflow.json`
4. Activate the workflow

---

## Setup Instructions

### 1. Start the MCP Server

```bash
cd e:\AIML-Projects\Lead-EZ

# Install dependencies
pip install fastapi uvicorn

# Start server
python -m backend.mcp.server
```

Server will run on `http://localhost:8001`

### 2. Test MCP Endpoints

```bash
# Health check
curl http://localhost:8001/

# List tools
curl http://localhost:8001/tools

# Get stats
curl http://localhost:8001/tools/get_stats

# Generate leads
curl -X POST http://localhost:8001/tools/generate_leads \
  -H "Content-Type: application/json" \
  -d '{"count": 100, "save_to_db": true}'

# Enrich leads
curl -X POST http://localhost:8001/tools/enrich_leads \
  -H "Content-Type: application/json" \
  -d '{"mode": "offline", "limit": 50}'

# Generate messages
curl -X POST http://localhost:8001/tools/generate_messages \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'

# Generate messages with custom confidence threshold
curl -X POST http://localhost:8001/tools/generate_messages \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "min_confidence_score": 70}'

# Review messages
curl -X POST http://localhost:8001/tools/review_messages \
  -H "Content-Type: application/json" \
  -d '{"auto_approve": false, "min_quality_score": 70}'

# Send messages (dry run)
curl -X POST http://localhost:8001/tools/send_messages \
  -H "Content-Type: application/json" \
  -d '{"use_queue": true, "batch_size": 50, "dry_run": true}'
```

### 3. Import n8n Workflow

1. Start n8n:
   ```bash
   npx n8n
   ```

2. Open http://localhost:5678

3. Import workflow:
   - Click "Workflows" → "Import from File"
   - Select `automation/n8n_agent_workflow.json`
   - Click "Import"

4. Configure Schedule Trigger:
   - Double-click "Schedule Trigger" node
   - Set interval (default: 5 minutes)
   - Click "Save"

5. Activate workflow:
   - Toggle "Active" switch in top-right

---

## How It Works

### Pipeline Flow

1. **n8n Schedule Trigger** fires every 5 minutes

2. **Get Stats** fetches current pipeline state:
   ```json
   {
     "leads": {
       "NEW": 0,
       "GENERATED": 100,
       "ENRICHED": 50,
       "MESSAGED": 20
     },
     "messages": {
       "PENDING": 80,
       "APPROVED": 0,
       "SENT": 0
     }
   }
   ```

3. **Agent Decision Node** examines status and decides:
   - Priority 1: Send approved messages (APPROVED > 0)
   - Priority 2: Review pending messages (PENDING > 0)
   - Priority 3: Generate messages for enriched leads (ENRICHED > 0, confidence >= 55)
   - Priority 4: Enrich generated leads (GENERATED > 0)
   - Priority 5: Generate new leads (if low inventory)
   
   **Note:** Messages are only generated for leads with confidence score >= 55

4. **IF Node** checks if action = "wait"
   - Yes → Log "nothing to do"
   - No → Call MCP tool endpoint

5. **MCP Tool** executes:
   - `/tools/review_messages` → Reviews 80 pending messages, approves 75
   - Returns: `{"approved": 75, "rejected": 5}`

6. **Next Cycle:**
   - Stats now show: `{"APPROVED": 75, "PENDING": 0}`
   - Agent decides: "send_messages"
   - MCP calls `/tools/send_messages`
   - Queue fetches 50 messages, sends at 10/min rate

### Message Queue in Action

When `/tools/send_messages` is called:

```python
# 1. Initialize queue
queue = get_message_queue(batch_size=50, max_per_minute=10)

# 2. Fetch batch from DB (1 query)
queue.fetch_batch(status="APPROVED")  # Fetches 50 messages

# 3. Process with rate limiting
async def sender(message):
    # Send email or LinkedIn DM
    return True

result = await queue.process_with_rate_limit(sender, dry_run=False)

# 4. Queue auto-refills when < 10 remain
# 5. Status updates happen in batches
```

**Result:** Instead of 50 DB queries, only 2-3 queries total!

---

## Agent Review & Filtering Logic

### Message Generation Filter (`/tools/generate_messages`)

Before messages are even generated, leads are filtered by confidence score:

```python
# Only generate messages for leads with confidence >= 55
query = """
    SELECT * FROM leads 
    WHERE status = 'ENRICHED' 
    AND confidence_score >= 55
"""
```

**Why filter by confidence?**
- Saves processing time on low-quality leads
- Focuses resources on high-potential prospects
- Reduces message volume and spam risk

**Check your leads:**
```bash
python scripts/check_confidence.py
```

### Message Quality Review (`/tools/review_messages`)

After messages are generated, they're reviewed for quality:

```python
# Simple quality checks
quality_score = 80

# Check word limits
if channel == "email" and word_count > 120:
    quality_score = 50
elif channel == "linkedin" and word_count > 60:
    quality_score = 50

# Check for CTA
if "call" in content or "chat" in content:
    quality_score += 10

# Decide
if quality_score >= 70:
    status = "APPROVED"
else:
    status = "REJECTED"
```

**You can enhance this with:**
- AI-powered quality scoring
- Compliance checks (spam words, GDPR)
- Personalization validation
- A/B test selection logic

---

## Configuration

Edit `backend/core/config.py`:

```python
# Rate limiting
max_messages_per_minute: int = 10  # Messages per minute
max_retries: int = 3               # Max retry attempts

# Queue settings
lead_batch_size: int = 50          # Batch fetch size

# Message Generation
min_confidence_score: int = 55     # Only generate messages for confidence >= 55

# MCP Server
mcp_host: str = "localhost"
mcp_port: int = 8001
```

Or use environment variables:
```bash
export MIN_CONFIDENCE_SCORE=70  # Raise threshold to 70
export MAX_MESSAGES_PER_MINUTE=20  # Increase rate limit
```

---

## Testing

### Test Message Queue

```python
import asyncio
from backend.services.message_queue import get_message_queue

async def test_queue():
    queue = get_message_queue(batch_size=10, max_per_minute=20)
    
    # Fetch batch
    fetched = queue.fetch_batch(status="APPROVED")
    print(f"Fetched: {fetched}")
    
    # Process
    async def mock_sender(msg):
        print(f"Sending to {msg['lead_name']}")
        return True
    
    result = await queue.process_with_rate_limit(mock_sender, dry_run=True)
    print(result)

asyncio.run(test_queue())
```

### Test Agent Decision

```python
from backend.agent.decision_engine import AgentDecisionEngine

# Test decisions
print(AgentDecisionEngine.decide_next_action("NEW"))
print(AgentDecisionEngine.decide_next_action("ENRICHED"))
print(AgentDecisionEngine.decide_next_action("MESSAGED", "PENDING"))
print(AgentDecisionEngine.decide_next_action("MESSAGED", "APPROVED"))
```

### Test MCP Server

```bash
# Start server
python -m backend.mcp.server

# In another terminal
curl http://localhost:8001/tools/get_stats
```

---

## Next Steps

1. **Implement actual email/LinkedIn sending:**
   - Update the `mock_sender` function in `/tools/send_messages`
   - Integrate SMTP for emails
   - Integrate LinkedIn API for DMs

2. **Enhance agent review:**
   - Add AI-powered quality scoring
   - Implement compliance checks
   - Add personalization validation

3. **Add monitoring:**
   - Log all agent decisions
   - Track success rates
   - Alert on failures

4. **Scale the queue:**
   - Use Redis instead of in-memory queue
   - Implement distributed workers
   - Add priority queues

---

## Troubleshooting

**MCP Server won't start:**
```bash
pip install fastapi uvicorn
python -m backend.mcp.server
```

**n8n can't reach MCP server:**
- Check server is running: `curl http://localhost:8001/`
- Check firewall settings
- Ensure port 8001 is not in use

**Queue not refilling:**
- Check DB has messages with status="APPROVED"
- Check `min_threshold` setting (default: 10)
- View queue stats: `GET /tools/get_stats`

**Messages not sending:**
- Check `dry_run` is set to `false`
- Implement actual sender function (currently just mocked)
- Check rate limit settings

---

## Summary

✅ **Message Queue** - Batch-fetches 50 messages, processes with 10/min rate limit  
✅ **Agent Decision Engine** - Examines status, decides next MCP endpoint  
✅ **MCP Server** - Exposes 7 tool endpoints for n8n  
✅ **n8n Workflow** - Orchestrates pipeline with agent control node  

**Result:** No DB fetch for every message delivery! Batch processing reduces queries by 95%.
