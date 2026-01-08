"""
MCP Server for Lead-EZ
======================

Model Context Protocol server that exposes tools for the entire lead pipeline:
- Lead generation
- Lead enrichment  
- Message generation
- Message review/approval
- Message sending (via queue)
- Status tracking

This server is designed to be called by n8n workflows.
"""

from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from datetime import datetime
from ..core.logger import logger
from ..core.config import settings
from ..core.database import get_db_connection
from ..services.lead_generator import LeadGenerator
from ..services.enricher import Enricher
from ..services.message_generator import MessageGenerator
from ..services.message_queue import get_message_queue
from ..models.lead import Lead
from ..agent.decision_engine import AgentDecisionEngine



# ============================================================================
# REQUEST MODELS
# ============================================================================

class GenerateLeadsRequest(BaseModel):
    count: int = 200
    save_to_db: bool = True
    seed: Optional[int] = 42  # Reproducible random seed


class EnrichLeadsRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    limit: Optional[int] = None
    mode: str = "offline"  # offline or ai


class GenerateMessagesRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    limit: Optional[int] = None  # None = no limit (process all matching leads)
    min_confidence_score: int = 60 


class ReviewMessagesRequest(BaseModel):
    message_ids: Optional[List[str]] = None


class SendMessagesRequest(BaseModel):
    message_ids: Optional[List[str]] = None
    use_queue: bool = True
    batch_size: int = 50
    dry_run: bool = True


class AgentDecisionRequest(BaseModel):
    lead_status: str
    message_status: Optional[str] = None
    lead_id: Optional[str] = None


# ============================================================================
# MCP SERVER
# ============================================================================

app = FastAPI(
    title="Lead-EZ MCP Server",
    description="Model Context Protocol server for lead generation pipeline",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Lead-EZ MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/tools")
async def list_tools():
    """List all available MCP tools."""
    return {
        "tools": [
            {
                "name": "generate_leads",
                "endpoint": "/tools/generate_leads",
                "method": "POST",
                "description": "Generate new leads using Faker"
            },
            {
                "name": "enrich_leads",
                "endpoint": "/tools/enrich_leads",
                "method": "POST",
                "description": "Enrich leads with pain points and triggers"
            },
            {
                "name": "generate_messages",
                "endpoint": "/tools/generate_messages",
                "method": "POST",
                "description": "Generate 4 message variants per lead"
            },
            {
                "name": "review_messages",
                "endpoint": "/tools/review_messages",
                "method": "POST",
                "description": "Review and approve/reject messages"
            },
            {
                "name": "send_messages",
                "endpoint": "/tools/send_messages",
                "method": "POST",
                "description": "Send approved messages via queue"
            },
            {
                "name": "agent_decide",
                "endpoint": "/tools/agent_decide",
                "method": "POST",
                "description": "Agent decision: determine next action based on status"
            },
            {
                "name": "get_stats",
                "endpoint": "/tools/get_stats",
                "method": "GET",
                "description": "Get pipeline statistics"
            },
            {
                "name": "get_leads",
                "endpoint": "/leads",
                "method": "GET",
                "description": "Get paginated list of leads with filters"
            }
        ]
    }


@app.post("/tools/generate_leads")
async def generate_leads(request: GenerateLeadsRequest):
    """Generate new leads."""
    try:
        logger.info(f"MCP Tool: generate_leads (count={request.count}, seed={request.seed})")
        
        generator = LeadGenerator(seed=request.seed)
        
        if request.save_to_db:
            result = generator.generate_and_save(request.count)
            return {
                "success": True,
                "action": "generate_leads",
                "generated": result["generated"],
                "saved": result["saved"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            leads = generator.generate_leads(request.count)
            return {
                "success": True,
                "action": "generate_leads",
                "generated": len(leads),
                "leads": leads,
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error in generate_leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/enrich_leads")
async def enrich_leads(request: EnrichLeadsRequest):
    """Enrich leads with pain points and triggers."""
    try:
        logger.info(f"MCP Tool: enrich_leads (mode={request.mode})")
        
        enricher = Enricher(mode=request.mode)
        result = await enricher.enrich_leads(
            lead_ids=request.lead_ids,
            limit=request.limit
        )
        
        return {
            "success": True,
            "action": "enrich_leads",
            "enriched": result["enriched"],
            "failed": result["failed"],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in enrich_leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/generate_messages")
async def generate_messages(request: GenerateMessagesRequest):
    """Generate messages for enriched leads."""
    try:
        logger.info(f"MCP Tool: generate_messages (min_confidence={request.min_confidence_score})")
        
        # Fetch enriched leads with confidence score filter
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, full_name, company_name, role, industry, 
                       persona_tag, pain_points, buying_triggers, confidence_score
                FROM leads 
                WHERE status = 'ENRICHED'
                AND confidence_score >= ?
            """
            params = [request.min_confidence_score]
            
            if request.lead_ids:
                placeholders = ",".join("?" * len(request.lead_ids))
                query += f" AND id IN ({placeholders})"
                params.extend(request.lead_ids)
            
            if request.limit:
                query += " LIMIT ?"
                params.append(request.limit)
            
            cursor.execute(query, params)
            leads = cursor.fetchall()
            
            # Count leads below threshold for reporting
            cursor.execute("""
                SELECT COUNT(*) as count FROM leads 
                WHERE status = 'ENRICHED' AND confidence_score < ?
            """, (request.min_confidence_score,))
            skipped_count = cursor.fetchone()["count"]
        
        # Generate messages
        generator = MessageGenerator()
        total_generated = 0
        
        for lead_row in leads:
            lead = Lead(
                id=lead_row["id"],
                full_name=lead_row["full_name"],
                company_name=lead_row["company_name"],
                role=lead_row["role"],
                industry=lead_row["industry"],
                persona_tag=lead_row["persona_tag"],
                pain_points=lead_row["pain_points"],
                buying_triggers=lead_row["buying_triggers"],
                email="",  # Not needed for generation
                website="",
                linkedin_url="",
                country="",
                status="ENRICHED"
            )
            
            messages = generator.generate_messages(lead)
            
            # Save to database
            with get_db_connection() as conn:
                cursor = conn.cursor()
                import uuid
                
                for msg in messages:
                    msg_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO messages (id, lead_id, channel, variant, content, status)
                        VALUES (?, ?, ?, ?, ?, 'PENDING')
                    """, (msg_id, lead.id, msg["channel"], msg["variant"], msg["content"]))
                
                # Keep lead status as ENRICHED (will change to SENT only in live mode)
                # No status update here - stays ENRICHED until actually sent
                
                conn.commit()
                total_generated += len(messages)
        
        return {
            "success": True,
            "action": "generate_messages",
            "leads_processed": len(leads),
            "leads_skipped": skipped_count,
            "messages_generated": total_generated,
            "min_confidence_score": request.min_confidence_score,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in generate_messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/review_messages")
async def review_messages(request: ReviewMessagesRequest):
    """Review messages and approve/reject them.
    
    Randomly selects one variant (A or B) per channel for each lead.
    """
    try:
        logger.info("MCP Tool: review_messages")
        
        # Fetch pending messages
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, lead_id, channel, variant, content
                FROM messages 
                WHERE status = 'PENDING'
            """
            params = []
            
            if request.message_ids:
                placeholders = ",".join("?" * len(request.message_ids))
                query += f" AND id IN ({placeholders})"
                params.extend(request.message_ids)
            
            cursor.execute(query, params)
            messages = cursor.fetchall()
        
        # Group messages by (lead_id, channel) for variant selection
        grouped = {}
        for msg in messages:
            key = (msg["lead_id"], msg["channel"])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(dict(msg))
        
        approved = 0
        rejected = 0
        
        # Randomly pick one variant per channel
        import random
        for (lead_id, channel), variants in grouped.items():
            # Randomly select one variant to approve
            selected_variant = random.choice(variants)
            
            for msg in variants:
                if msg["id"] == selected_variant["id"]:
                    new_status = "APPROVED"
                    approved += 1
                    logger.info(f"✓ Approved variant {msg['variant']} for {channel}")
                else:
                    new_status = "REJECTED"
                    rejected += 1
                    logger.debug(f"✗ Rejected variant {msg['variant']} for {channel}")
                
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE messages SET status = ? WHERE id = ?", 
                                 (new_status, msg["id"]))
                    conn.commit()
        
        return {
            "success": True,
            "action": "review_messages",
            "reviewed": len(messages),
            "approved": approved,
            "rejected": rejected,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in review_messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/send_messages")
async def send_messages(request: SendMessagesRequest):
    """Send approved messages using the message queue."""
    try:
        logger.info(f"MCP Tool: send_messages (use_queue={request.use_queue}, dry_run={request.dry_run})")
        
        if request.use_queue:
            # Use message queue for batch processing
            queue = get_message_queue(
                batch_size=request.batch_size,
                max_per_minute=settings.max_messages_per_minute
            )
            
            # Fetch batch into queue
            fetched = queue.fetch_batch(status="APPROVED")
            
            # Process queue with appropriate mode (dry_run or live)
            result = await queue.process_with_rate_limit(dry_run=request.dry_run)
            
            return {
                "success": True,
                "action": "send_messages",
                "mode": "dry_run" if request.dry_run else "live",
                "sent": result["sent"],
                "failed": result["failed"],
                "elapsed_seconds": result["elapsed_seconds"],
                "rate_per_minute": result["rate_per_minute"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Direct sending (not recommended)
            return {
                "success": False,
                "error": "Direct sending not implemented. Use use_queue=true"
            }
    
    except Exception as e:
        logger.error(f"Error in send_messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/agent_decide")
async def agent_decide(request: AgentDecisionRequest):
    """Agent decision: determine next action based on status."""
    try:
        decision = AgentDecisionEngine.decide_next_action(
            lead_status=request.lead_status,
            message_status=request.message_status
        )
        
        return {
            "success": True,
            "lead_id": request.lead_id,
            "current_lead_status": request.lead_status,
            "current_message_status": request.message_status,
            "decision": decision,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in agent_decide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads")
async def get_leads(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "DESC"
):
    """Get paginated list of leads with filters."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM leads WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            # Add sorting
            allowed_sort_fields = ["created_at", "updated_at", "confidence_score", "full_name"]
            if sort_by not in allowed_sort_fields:
                sort_by = "created_at"
            
            sort_order = "DESC" if sort_order.upper() == "DESC" else "ASC"
            query += f" ORDER BY {sort_by} {sort_order}"
            
            # Add pagination
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            leads = [dict(row) for row in cursor.fetchall()]
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM leads WHERE 1=1"
            count_params = []
            if status:
                count_query += " AND status = ?"
                count_params.append(status)
            
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()["total"]
        
        return {
            "success": True,
            "leads": leads,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(leads)) < total
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/get_stats")
async def get_stats():
    """Get pipeline statistics."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Lead stats with counts
            cursor.execute("SELECT status, COUNT(*) as count FROM leads GROUP BY status")
            lead_stats = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            # Total leads
            cursor.execute("SELECT COUNT(*) as total FROM leads")
            total_leads = cursor.fetchone()["total"]
            
            # Message stats with counts
            cursor.execute("SELECT status, COUNT(*) as count FROM messages GROUP BY status")
            message_stats = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            # Total messages
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total_messages = cursor.fetchone()["total"]
            
            # Recent activity - last updated lead
            cursor.execute("""
                SELECT updated_at, status FROM leads 
                WHERE updated_at IS NOT NULL 
                ORDER BY updated_at DESC LIMIT 1
            """)
            last_lead_update = cursor.fetchone()
            
            # Queue stats
            queue = get_message_queue()
            queue_stats = queue.get_stats()
        
        return {
            "success": True,
            "summary": {
                "total_leads": total_leads,
                "leads_enriched": lead_stats.get("ENRICHED", 0),
                "total_messages": total_messages,
                "messages_sent": message_stats.get("SENT", 0),
                "messages_failed": message_stats.get("FAILED", 0),
                "messages_pending": message_stats.get("PENDING", 0)
            },
            "leads": lead_stats,
            "messages": message_stats,
            "queue": queue_stats,
            "last_activity": {
                "timestamp": last_lead_update["updated_at"] if last_lead_update else None,
                "status": last_lead_update["status"] if last_lead_update else None
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SERVER STARTUP
# ============================================================================

def start_mcp_server(host: str = "localhost", port: int = 8001):
    """Start the MCP server."""
    logger.info(f"Starting MCP Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_mcp_server(
        host=settings.mcp_host,
        port=settings.mcp_port
    )
