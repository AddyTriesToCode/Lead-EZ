# Lead-EZ: MCP-Powered Lead Gen + Enrichment + Outreach System
A fully automated lead generation and outreach system powered by the **Model Context Protocol (MCP)**. This system orchestrates end-to-end lead workflows through intelligent agent-driven automation using n8n, with real-time monitoring via a React frontend.

---

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the System](#running-the-system)
- [Configuration](#configuration)
- [Pipeline Workflow](#pipeline-workflow)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Assignment Requirements Checklist](#assignment-requirements-checklist)

---

## 🎯 Overview

Lead-EZ is a complete lead generation and outreach automation system that demonstrates:

- **MCP-based orchestration**: All operations exposed as MCP tools
- **Agent-driven workflow**: n8n agent makes intelligent decisions based on pipeline state
- **Full-stack monitoring**: React dashboard tracks progress in real-time
- **Dual-mode operation**: Dry-run (safe testing) and live-run (actual sending)
- **Smart enrichment**: Rule-based enrichment and an optional AI enrichment ; with confidence scoring
- **Personalized messaging**: A/B tested emails and LinkedIn DMs with contextual personalization
- **Production-ready**: Rate limiting, retry logic, error handling, and structured logging

### What It Does

1. **Generates upto 250 realistic leads in a single run**, with valid contact information
2. **Enriches leads** with pain points, buying triggers, personas, and confidence scores
3. **Creates personalized messages** (4 variations per lead: 2 emails + 2 LinkedIn DMs)
4. **Sends messages** via SMTP (emails) and simulates LinkedIn outreach
5. **Tracks everything** through a clean React UI with real-time status updates

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    n8n Workflow Engine                       │
│              (Orchestration + Agent Logic)                   │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐        │
│  │  Webhook   │    │   Agent    │    │  Schedule  │        │
│  │  Trigger   │───▶│  Decision  │◀───│  Trigger   │        │
│  └────────────┘    │   Engine   │    └────────────┘        │
│                    └──────┬─────┘                            │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  MCP Server (FastAPI)                        │
│                   Port 8001                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tools:                                               │  │
│  │  • generate_leads    • enrich_leads                  │  │
│  │  • generate_messages • review_messages               │  │
│  │  • send_messages     • get_stats                     │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬───────────────────────────────────┬────────────┘
             │                                   │
             ▼                                   ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│   Backend Services      │           │   SQLite Database       │
│  • Lead Generator       │ ◀───────▶│  • leads table          │
│  • Enricher             │           |  • messages table       │
│  • Message Generator    │           │  • history table        │
│  • Message Queue        │           │  • pipeline_runs table  |  
|  • Message Sender       │           |(for further development)|                      
└─────────────────────────┘           └─────────────────────────┘
             │
             │ SMTP/Storage
             ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│  Message Delivery       │          │   React Frontend        │
│  • Dry-run: JSON files  │          │  • Dashboard            │
│  • Live: SMTP + LinkedIn│◀───────▶│  • History Viewer       │
│  • Rate limiting        │          │  • Real-time Stats      │
│  • Retry logic          │          └─────────────────────────┘
└─────────────────────────┘          
```

### Key Components

| **Component** | **Technology**     | **Purpose**                                       |
|               |                    |                                                   |
| Orchestration | n8n                | Agent workflow engine with decision logic         |
| MCP Server    | FastAPI            | Exposes tools for pipeline operations             |
| Backend       | Python             | Business logic and services                       |
| Database      | SQLite             | Persistent storage for leads,messages and history | 
| Frontend      | React+Vite         | Real-time monitoring dashboard                    |
| Message Queue | In-memory + SQLite | Rate-limited batch processing                     |

---

## ✨ Features

### 🎯 Lead Generation
- ✅ Generates **upto 250 realistic leads in 1 run** using Faker
- ✅ Industry-specific role matching (10 industries, 5+ roles each)
- ✅ **Reproducible** with random seed support
- ✅ Syntactically valid emails, websites, and LinkedIn URLs
- ✅ Consistent, credible data patterns

### 🧠 Lead Enrichment
- ✅ **Dual-mode enrichment**:
  - **Offline mode**: Rule-based heuristics (no API calls)
  - **AI mode**: Ollama integration with automatic fallback
- ✅ Company size estimation (small/medium/enterprise)
- ✅ Persona tagging based on role and industry
- ✅ 2-3 contextual pain points per lead
- ✅ 1-2 buying triggers per lead
- ✅ Confidence scoring (0-100)

### 💬 Message Generation
- ✅ Messages generated only for leads approved (min 60% confidence)
- ✅ **4 personalized messages per approved lead**:
  - 2 email variations (A/B testing)
  - 2 LinkedIn DM variations (A/B testing)
- ✅ References enriched insights (pain points, triggers, persona)
- ✅ Word limits enforced: 120 words (email), 60 words (LinkedIn)
- ✅ Clear CTAs in every message
- ✅ No hallucinated facts

### 📤 Message Sending
- ✅ **Dry-run mode**: Saves to JSON (100% safe testing)
- ✅ **Live mode**: Real SMTP email delivery
- ✅ LinkedIn outreach simulation (stored in the app storage)
- ✅ **Retry logic**: Up to 2 retries with exponential backoff
- ✅ **Rate limiting**: Configurable (default: 10/minute)
- ✅ Structured error logging

### 🎛️ Frontend Dashboard
- ✅ Real-time pipeline metrics
- ✅ Pipeline status tracking
- ✅ **"Run Pipeline" button** with configurations:
    - ✅ Number of leads to generate (upto 250) **REQUIRED PARAM**
    - ✅ Seed value for reprodcible generation **OPTIONAL PARAM**
    - ✅ Rule-based enrichment / LLM(mistral) powered enrichment
    - ✅ Dry-run / Live-run toggle
    - ✅ History viewer with filtering
- ✅ Export capabilities

### 🤖 MCP + Agent Integration
- ✅ Full MCP server implementation with exposed tools
- ✅ n8n agent with intelligent decision-making capability
- ✅ State-based tool selection
- ✅ Webhook + scheduled triggers
- ✅ Comprehensive error handling

---

## 🛠️ Technology Stack

### Backend
- **Python 3.11+**: Core language
- **FastAPI**: MCP server framework
- **SQLite**: Database (zero configuration)
- **Faker**: Realistic data generation
- **httpx**: Async HTTP client for faster AI enrichment
- **Pydantic**: Data validation

### Frontend
- **React 18.3**: UI framework
- **Vite**: Build tool
- **JavaScript/JSX**: Frontend logic
- **CSS3**: Styling

### Orchestration
- **n8n**: Workflow automation engine
- **MCP (Model Context Protocol)**: Tool standardization

### Free Tier Resources
- **Ollama**: Local LLM for AI enrichment 
- **SendGrid**: Cloud based SMTP service
---

## 📦 Prerequisites

### Required
- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Node.js 18+** ([Download](https://nodejs.org/))
- **npm** or **yarn** (comes with Node.js)
- **Git** ([Download](https://git-scm.com/))

### Optional
- **Ollama** ([Download](https://ollama.ai/)) - For AI enrichment mode
- **n8n Desktop** or npm package ([Docs](https://docs.n8n.io/hosting/installation/npm/))
---
## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Lead-EZ
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
cd ..
```

### 4. Database Initialization
```bash
# Initialize SQLite database with schema
python scripts/init_db.py
```

### 5. Configuration
```bash
# Copy example environment file
cp .env.example .env
# Edit .env with your settings 
```

### 6. Install n8n
```bash
npm install -g n8n
```
---

## ▶️ Running the System

#### Step 1: Start the MCP Server
```bash
# Activate virtual environment (if not already active)
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Start MCP server on port 8001
python -m backend.mcp.server
```

**Expected output:**
```
leadez - INFO - Starting MCP Server on localhost:8001
INFO:     Started server process [27584]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8001 (Press CTRL+C to quit)
```

#### Step 2: Start n8n Workflow Engine

Open a **new terminal** and run:
```bash
n8n
```

**Expected output:**
```
n8n ready on http://localhost:5678
```

**Import the workflow:**
1. Open browser: http://localhost:5678
2. Click **"Workflows"** → **"Import from File"**
3. Select: `automation/n8n_agent_workflow.json`
4. Click **"Save"**
5. Click **"Publish"**

#### Step 3: Start the Frontend

Open a **new terminal** and run:
```bash
cd frontend
npm run dev
```

**Expected output:**
```
  VITE ready in _ ms
  ➜  Local:   http://localhost:3000/
```

#### Step 4: Run the Pipeline

1. Open browser: http://localhost:3000/
2. Configure pipeline:
   - **Number of Leads**: MANDATORY (only between 1 to 250)
   - **Random Seed**: OPTIONAL for reproducibility. (Leaving blank sends random value between 1-999).
   - **Enrichment Mode**: OFFLINE(Rule-based and Faster), AI(Using mistral and comparatively slower) 
   - **Run Mode**: DRY-RUN (messages drafted in storage), LIVE (attempt SMTP and LinkedIn message delivery)
3. Click **"Run Pipeline"**
4. Watch real-time progress in the dashboard


## 🔧 Configuration

### Environment Variables

Edit `.env` to customize behavior:

```bash
# ============================================
# DATABASE
# ============================================
DATABASE_URL=sqlite:///./database/leads.db
DATABASE_TYPE=sqlite
# ============================================
# MCP SERVER
# ============================================
MCP_HOST=localhost
MCP_PORT=8001
# ============================================
# EMAIL (SMTP) - For Live Mode
# ============================================
 SMTP_HOST=smtp.sendgrid.net
 SMTP_PORT=587
 SMTP_USER=apikey
 SMTP_PASSWORD=your-sendgrid-api-key #REPLACE
 SMTP_FROM=verified-sender@yourdomain.com #REPLACE
 SMTP_ENABLED=true
 SMTP_USE_TLS=true
# ============================================
# RATE LIMITING
# ============================================
MAX_MESSAGES_PER_MINUTE=10    # Rate limit
MAX_RETRIES=2                 # Retry failed messages up to 2 times
RETRY_DELAY_SECONDS=5         # Wait 5s between retries
# ============================================
# AI ENRICHMENT (OPTIONAL)
# ============================================
LLM_PROVIDER=ollama           # Options: none, ollama, openai
LLM_MODEL=mistral             # Ollama model name
LLM_BASE_URL=http://localhost:11434
# Frontend Settings
# -----------------
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
# -----------------
# n8n Settings 
# -----------------
N8N_HOST=localhost
N8N_PORT=5678
N8N_PROTOCOL=http
```
---

## 🔄 Pipeline Workflow

### Automated Pipeline Stages

The n8n agent automatically progresses leads through these stages:

```
┌─────────────┐
│  1. NEW     │  Lead generated
└──────┬──────┘
       │
       ▼ enrich_leads (MCP tool)
┌─────────────┐
│ 2. ENRICHED │  Company size, pain points, triggers, confidence score added
└──────┬──────┘
       │
       ▼ generate_messages (MCP tool)
┌────────────────────┐
│ 3.Leads:ENRICHED   │  4 messages for each lead(2 per channel) created with status: PENDING
│   Messages:PENDING │
└──────┬─────────────┘
       │
       ▼ review_messages (MCP tool)
┌───────────────────────────────┐
│ 4. Leads: ENRICHED            │    One message per channel is APPROVED and other REJECTED, giving us 2 messages per lead
│    Messages:APPROVED/REJECTED |
└──────┬────────────────────────┘
       │
       ▼ send_messages (MCP tool)
┌─────────────────────┐ 
│ 5. Leads :CONTACTED │  Messages sent (or saved in dry-run)
│    Messages:SENT    │
└─────────────────────┘
```

### Agent Decision Logic

The n8n workflow contains an agent that examines pipeline state and decides which MCP tool to call next:

```javascript
// Simplified agent logic (from n8n workflow)
if (messages.APPROVED > 0) {
  action = 'send_messages';
} else if (messages.PENDING > 0) {
  action = 'review_messages';
} else if (leads.ENRICHED > 0) {
  action = 'generate_messages';
} else if (leads.NEW > 0) {
  action = 'enrich_leads';
} else {
  action = 'generate_leads';
}
```

### MCP Tools Reference

| Tool                | Endpoint                  | Purpose                      | 
|---------------------|---------------------------|------------------------------|
| `generate_leads`    | `/tools/generate_leads`   | Create realistic leads       | 
| `enrich_leads`      | `/tools/enrich_leads`     | Add context to leads         | 
| `generate_messages` | `/tools/generate_messages`| Create personalized messages | 
| `review_messages`   | `/tools/review_messages`  | Auto-approve messages        | 
| `send_messages`     | `/tools/send_messages`    | Deliver via SMTP/storage     |
| `get_stats`         | `/tools/get_stats`        | Pipeline metrics             |

---


## 📁 Project Structure

```
Lead-EZ/
├── automation/
│   └── n8n_agent_workflow.json        # n8n workflow export )
│
├── backend/
│   ├── agent/
│   │   └── decision_engine.py         # Agent decision logic
│   ├── api/                           # REST API endpoints (future)
│   ├── core/
│   │   ├── config.py                  # Settings management
│   │   ├── database.py                # SQLite connection
│   │   └── logger.py                  # Structured logging
│   ├── data/
│   │   ├── personas.json              # Industry-role-persona mappings
│   │   ├── pain_points.json           # Industry-specific pain points
│   │   └── triggers.json              # Buying trigger templates
│   ├── mcp/
│   │   └── server.py                  # MCP Server 
│   ├── models/
│   │   ├── lead.py                    # Lead data model
│   │   ├── message.py                 # Message data model
│   │   └── enums.py                   # Status enums
│   ├── services/
│   │   ├── lead_generator.py          # Lead generation with Faker
│   │   ├── enricher.py                # Dual-mode enrichment
│   │   ├── message_generator.py       # Personalized messaging
│   │   ├── message_queue.py           # Rate-limited queue
│   │   ├── message_sender.py          # SMTP + dry-run delivery
│   │   └── history_manager.py         # Pipeline history tracking
│   └── requirements.txt               # Python dependencies
│
├── database/
│   ├── leads.db                       # SQLite database (auto-created)
│   └── migrations/                    # Schema migrations (future)
│
├── docs/
│   ├── N8N_SETUP.md                   # n8n configuration guide
│   ├── AGENT_AND_QUEUE.md             # Agent architecture
│   ├── MESSAGE_GENERATION.md          # Message personalization logic
│   ├── CONFIDENCE_FILTERING.md        # Scoring algorithm
│   └── SENDGRID_WEBHOOKS.md           # Email tracking 
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx          # Main monitoring UI
│   │   │   └── History.jsx            # Pipeline history viewer
│   │   ├── services/
│   │   │   └── api.js                 # Backend API client
│   │   ├── styles/                    # CSS stylesheets
│   │   └── App.jsx                    # Root component
│   ├── package.json                   # Node dependencies
│   └── vite.config.js                 # Vite configuration
│
├── scripts/
│   ├── init_db.py                     # Database schema setup
│   ├── generate_leads.py              # Manual lead generation
│   ├── enrich_leads.py                # Manual enrichment
│   ├── generate_messages.py           # Manual message generation
│   ├── view_leads.py                  # View all leads
│   ├── view_dry_run_messages.py       # View saved messages
│   ├── export_messages.py             # Export to CSV
│   ├── debug_messages.py              # Debug message content
│   ├── check_pipeline_status.py       # Status checker
│   ├── empty_database.py              # Clear all data
│   └── test_pipeline.py               # End-to-end test
│
├── storage/
│   ├── logs/                          # Application logs
│   ├── messages/
│   │   └── dry_run_messages.json      # Saved messages (dry-run mode)
│   └── leads/                         # Lead exports (optional)
│
├── tests/
│   ├── unit/                          # Unit tests 
│   └── integration/                   # Integration tests
│
├── .env.example                       # Environment template
├── .gitignore                         # Git ignore rules
├── README.md                          # This file
├── TESTING_INSTRUCTIONS.md            # Quick testing guide
└── WORKFLOW_CORRECTED.md              # Workflow documentation
```

---

## 📚 API Documentation

### MCP Server Endpoints

Base URL: `http://localhost:8001`

#### GET `/`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "service": "Lead-EZ MCP Server",
  "version": "1.0.0"
}
```

#### POST `/tools/generate_leads`
Generate synthetic leads

**Request:**
```json
{
  "count": 200,
  "seed": 42,
  "save_to_db": true
}
```

**Response:**
```json
{
  "success": true,
  "action": "generate_leads",
  "leads_generated": 200,
  "leads_saved": 200,
  "seed": 42
}
```

#### POST `/tools/enrich_leads`
Enrich leads with context

**Request:**
```json
{
  "mode": "offline",
  "limit": 50
}
```

**Response:**
```json
{
  "success": true,
  "action": "enrich_leads",
  "leads_enriched": 50,
  "mode": "offline"
}
```

#### POST `/tools/generate_messages`
Create personalized messages

**Request:**
```json
{
  "min_confidence_score": 60,
  "limit": 50
}
```

**Response:**
```json
{
  "success": true,
  "action": "generate_messages",
  "leads_processed": 50,
  "messages_generated": 200,
  "avg_confidence": 72.5
}
```

#### POST `/tools/send_messages`
Send or save messages

**Request:**
```json
{
  "dry_run": true,
  "use_queue": true,
  "batch_size": 50
}
```

**Response:**
```json
{
  "success": true,
  "action": "send_messages",
  "messages_sent": 200,
  "messages_failed": 0,
  "mode": "dry_run"
}
```

#### GET `/tools/get_stats`
Get pipeline statistics

**Response:**
```json
{
  "summary": {
    "total_leads": 200,
    "leads_enriched": 200,
    "leads_above_threshold": 180,
    "total_messages": 800,
    "messages_sent": 720,
    "messages_failed": 0
  },
  "leads": {
    "NEW": 0,
    "ENRICHED": 200,
    "CONTACTED": 180
  },
  "messages": {
    "PENDING": 0,
    "APPROVED": 0,
    "SENT": 720
  }
}
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. n8n Workflow Not Executing

**Problem:** Webhook returns 404 or workflow doesn't run

**Solution:**
1. Ensure workflow is **activated** (toggle in top-right)
2. Check webhook URL matches: `http://localhost:5678/webhook/run-pipeline`
3. Re-import workflow: Delete old one, import fresh from `automation/n8n_agent_workflow.json`

#### 2. Frontend Can't Connect to Backend

**Error:** `Backend Error: Failed to connect`

**Solution:**
1. Verify MCP server is running on port 8001
2. Check CORS settings in `backend/core/config.py`
3. Ensure `.env` has correct `VITE_API_URL=http://localhost:8000`

#### 3. Database Lock Error

**Error:** `database is locked`

**Solution:**
```bash
# Close all connections and restart
python scripts/empty_database.py  # Optional: clear data
python scripts/init_db.py         # Reinitialize schema
```

#### 4. AI Enrichment Fails

**Error:** `Ollama connection failed`

**Solution:**
1. Check Ollama is running: `ollama serve`
2. Verify model is installed: `ollama pull mistral`
3. Fallback to offline mode: Set `enrichmentMode: 'offline'` in frontend

#### 5. No Messages Generated

**Problem:** Enriched leads but 0 messages

**Solution:**
- Check confidence scores: `python scripts/view_leads.py`
- Lower threshold in `.env`: `MIN_CONFIDENCE_SCORE=40`
- Or in frontend: Set "Min Confidence" to 40

### Debug Mode

Enable verbose logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Restart MCP server to see detailed logs
```

### Logs Location

- **Backend logs**: `storage/logs/leadez.log`
- **n8n logs**: Console output where n8n is running
- **Frontend logs**: Browser console (F12)

---

## ✅ Assignment Requirements Checklist

### ✅ Required Orchestration (n8n + Agent)
- ✅ n8n workflow export JSON provided: `automation/n8n_agent_workflow.json`
- ✅ Agent decision engine implemented: `backend/agent/decision_engine.py`
- ✅ Agent step in n8n that calls MCP tools based on state
- ✅ Documentation of workflow configuration: `docs/N8N_SETUP.md`
- ✅ Retry, rate limiting, and failure handling implemented

### ✅ Lead Generation (200+ Leads)
- ✅ Python script generates 200+ leads: `backend/services/lead_generator.py`
- ✅ All required fields present: name, company, role, industry, website, email, LinkedIn, country
- ✅ Syntactically valid emails, URLs, and websites
- ✅ Industry-role matching for consistency
- ✅ Reproducible with random seed parameter
- ✅ Validation logic documented in code comments

### ✅ Lead Enrichment
- ✅ **Offline mode**: Rule-based heuristics (no external APIs)
- ✅ **AI mode**: Ollama integration with automatic fallback
- ✅ Company size estimation (small/medium/enterprise)
- ✅ Persona tags (e.g., "VP Ops", "Data Leader")
- ✅ 2-3 pain points per lead
- ✅ 1-2 buying triggers per lead
- ✅ Confidence score (0-100)
- ✅ Clear documentation of rule-based vs AI logic in code

### ✅ Message Personalization
- ✅ Cold email (max 120 words) with 2 variations (A/B)
- ✅ LinkedIn DM (max 60 words) with 2 variations (A/B)
- ✅ References at least one enriched insight per message
- ✅ Clear CTA in every message
- ✅ No hallucinated company facts (uses only lead data)

### ✅ Message Sending
- ✅ **Dry-run mode**: Writes to `storage/messages/dry_run_messages.json`
- ✅ **Live mode**: SMTP email via configurable server
- ✅ LinkedIn DM simulation (compliant, no bots/scraping)
- ✅ Retry logic: 2 retries with configurable delay
- ✅ Rate limiting: 10 messages/minute (configurable)
- ✅ Error handling with structured logs in `storage/logs/`

### ✅ Frontend Monitoring
- ✅ Built with Vite + React (free, open-source)
- ✅ Shows total leads generated
- ✅ Shows leads enriched
- ✅ Shows messages generated
- ✅ Shows messages sent
- ✅ Shows failed messages
- ✅ Shows queue status/job progress
- ✅ Table view of leads with status and last action
- ✅ **"Run Pipeline" button**
- ✅ **Dry Run / Live Run toggle**

### ✅ MCP Implementation
- ✅ MCP server implementation: `backend/mcp/server.py`
- ✅ Required tools exposed:
  - ✅ `generate_leads`
  - ✅ `enrich_leads`
  - ✅ `generate_messages`
  - ✅ `send_outreach` (via `send_messages`)
  - ✅ `get_status` and `get_metrics` (via `get_stats`)
- ✅ MCP client/agent connects and invokes tools
- ✅ State persistence via SQLite
- ✅ Structured tool inputs/outputs with Pydantic schemas
- ✅ Pipeline status tracking: NEW → ENRICHED → MESSAGED → SENT → FAILED

### ✅ Data Storage
- ✅ SQLite database with schema: `database/leads.db`
- ✅ Pipeline status tracking implemented
- ✅ History table for audit trail

### ✅ Deliverables
- ✅ **README.md**: Comprehensive setup and usage guide
- ✅ **Source code**: All components present and documented
- ✅ **n8n workflow export**: `automation/n8n_agent_workflow.json`
- ✅ **.env.example**: Template for configuration
- ✅ **Demo video**: 5 minute demo video 

### ✅ Bonus Features
- ✅ Configurable personas and targeting: `backend/data/*.json`
- ✅ Export leads/messages to CSV: `scripts/export_messages.py`
- ⚠️ Unit tests: Test directories created, tests TODO
- ❌ Streaming progress updates (WebSockets): Not implemented
