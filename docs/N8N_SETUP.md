# n8n Setup Guide

## Overview

The Lead-EZ system uses **n8n** as the orchestration layer. The n8n workflow acts as an intelligent agent that:
- Makes decisions based on pipeline state
- Calls MCP tool endpoints in the right order
- Handles retries and error cases
- Can be triggered on-demand or run on schedule

---

## Installation

### Option 1: npm (Recommended)

```bash
npm install -g n8n
```

### Option 2: Docker

```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

---

## Starting n8n

```bash
n8n
```

This starts n8n at **http://localhost:5678**

---

## Importing the Workflow

1. Open n8n at http://localhost:5678
2. Click **"Workflows"** in the sidebar
3. Click **"Import from File"**
4. Select: `automation/n8n_agent_workflow.json`
5. Click **"Save"**

---

## Workflow Overview

### **Triggers**

The workflow has **two triggers**:

1. **Webhook Trigger** (Manual)
   - URL: `http://localhost:5678/webhook/run-pipeline`
   - Method: POST
   - Use: On-demand execution from frontend

2. **Schedule Trigger** (Automatic)
   - Runs: Every 5 minutes
   - Use: Autonomous background processing

### **Workflow Steps**

```
┌─────────────────┐
│ Webhook/Schedule│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Get Stats      │ → Fetch current pipeline state
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent Decision  │ → Determine next action
└────────┬────────┘
         │
         ▼
    ┌────┴────┐
    │  Wait?  │
    └─┬─────┬─┘
      │     │
   Yes│     │No
      │     │
      ▼     ▼
   [Wait] [Call MCP Tool]
             │
             ▼
         [Log Result]
             │
             ▼
      [Respond to Webhook]
```

### **Agent Decision Logic**

The workflow prioritizes actions in this order:

1. **Send approved messages** (APPROVED > 0)
2. **Review pending messages** (PENDING > 0)
3. **Generate messages** (ENRICHED > 0, confidence ≥ 60)
4. **Enrich leads** (NEW > 0)
5. **Generate leads** (inventory low: NEW < 10, ENRICHED < 20)

---

## Activating the Workflow

### For Scheduled Execution

1. In n8n, open the imported workflow
2. Toggle the **"Active"** switch in the top-right
3. The workflow will now run every 5 minutes automatically

### For Manual/Webhook Execution

The webhook is always available once the workflow is saved. No need to activate for webhook triggers.

---

## Testing the Webhook

### From Terminal

```bash
curl -X POST http://localhost:5678/webhook/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{"trigger": "test"}'
```

### From Frontend

Click the **"🚀 Run Pipeline"** button in the dashboard.

---

## Configuration

### Change Schedule Interval

1. Open the workflow in n8n
2. Click the **"Schedule Trigger"** node
3. Modify the **"Trigger Interval"** field
4. Save the workflow

### Adjust Agent Parameters

1. Open the workflow in n8n
2. Click the **"Agent Decision Node"**
3. Edit the JavaScript code
4. Common changes:
   - Confidence threshold: Change `min_confidence_score: 60`
   - Batch sizes: Change `limit: 50`
   - Dry run mode: Change `dry_run: false`

### Change MCP Server URL

If your MCP server runs on a different port:

1. Open the workflow
2. Click **"Get Pipeline Stats"** node
3. Change URL from `http://localhost:8001` to your URL
4. Update all other HTTP Request nodes similarly

---

## Monitoring

### View Executions

1. In n8n, click **"Executions"** in the sidebar
2. See history of all workflow runs
3. Click any execution to see:
   - Which nodes ran
   - Input/output data
   - Execution time
   - Errors (if any)

### Debug Mode

1. Open the workflow
2. Click **"Execute Workflow"** button
3. Watch nodes execute in real-time
4. Inspect data at each step

---

## Troubleshooting

### "Webhook not found" error

**Cause**: Workflow not saved or n8n restarted  
**Fix**: Re-import the workflow and save it

### "Connection refused" to MCP server

**Cause**: MCP server not running  
**Fix**: 
```bash
cd E:\AIML-Projects\Lead-EZ
python -m backend.mcp.server
```

### Workflow runs but nothing happens

**Cause**: No leads in pipeline  
**Fix**: Run "Generate Leads" from frontend first

### Executions fail with timeout

**Cause**: MCP operations taking too long  
**Fix**: Reduce batch sizes in agent decision logic

---

## Architecture

```
┌──────────────┐
│   Frontend   │ → Triggers webhook on button click
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   n8n        │ → Orchestrates workflow
│   (Agent)    │ → Makes decisions
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  MCP Server  │ → Executes tools
│  (Port 8001) │ → Manages pipeline
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Database   │ → Stores leads/messages
│   (SQLite)   │
└──────────────┘
```

---

## Best Practices

1. **Keep n8n running**: Use `pm2` or systemd for production
2. **Monitor executions**: Check n8n dashboard regularly
3. **Adjust intervals**: Don't run too frequently (default 5min is good)
4. **Use dry-run first**: Test with `dry_run: true` before live mode
5. **Set up error notifications**: Add email/Slack nodes for failures

---

## Production Deployment

### Using PM2

```bash
# Install PM2
npm install -g pm2

# Start n8n with PM2
pm2 start n8n --name "lead-ez-n8n"

# Auto-start on reboot
pm2 startup
pm2 save
```

### Using Docker Compose

```yaml
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    volumes:
      - ~/.n8n:/home/node/.n8n
    restart: always
```

---

## Next Steps

1. ✅ Install n8n
2. ✅ Import workflow
3. ✅ Test webhook
4. ✅ Activate schedule
5. ✅ Monitor executions

For questions, see the [n8n documentation](https://docs.n8n.io/)
