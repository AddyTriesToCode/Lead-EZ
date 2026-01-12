# Lead-EZ Frontend

React + Vite dashboard for monitoring the Lead-EZ pipeline.

## Features

- 📊 Real-time pipeline statistics
- 👥 Lead table with status tracking
- 🎮 Interactive pipeline controls
- 🔄 Auto-refresh (5 second intervals)
- 🧪 Dry Run / Live Mode toggle
- 📦 Queue status monitoring
- 🌙 Dark theme UI

## Setup

### Install Dependencies

```bash
cd frontend
npm install
```

### Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

## Prerequisites

Make sure the MCP server is running:

```bash
cd ..
python -m backend.mcp.server
```

The frontend connects to the backend at `http://localhost:8001`

## Configuration

The API base URL is configured in `src/services/api.js`:

```javascript
const BASE_URL = 'http://localhost:8001'
```

## Features Overview

### Stats Cards
- Total Leads
- Enriched Leads
- Messages Generated
- Messages Sent
- Failed Messages
- Pending Review

### Pipeline Control
Run each pipeline step manually:
1. Generate Leads
2. Enrich Leads
3. Generate Messages
4. Review Messages
5. Send Messages

### Leads Table
- Filter by status
- View confidence scores
- Sort and search
- Real-time updates

### Queue Status
- Current queue size
- Total fetched/sent/failed
- Processing status indicator
