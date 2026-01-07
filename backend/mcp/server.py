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
import dotenv
import os
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
    count: int = 100
    save_to_db: bool = True


class EnrichLeadsRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    limit: Optional[int] = None
    mode: str = "offline"  # offline or ai


class GenerateMessagesRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    limit: Optional[int] = None
    min_confidence_score: int = os.getenv("MIN_CONFIDENCE_SCORE")  # Only generate messages for leads with confidence > threshold


class ReviewMessagesRequest(BaseModel):
    message_ids: Optional[List[str]] = None
    auto_approve: bool = False
    min_quality_score: int = 70


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
            }
        ]
    }


@app.post("/tools/generate_leads")
async def generate_leads(request: GenerateLeadsRequest):
    """Generate new leads."""
    try:
        logger.info(f"MCP Tool: generate_leads (count={request.count})")
        
        generator = LeadGenerator()
        
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
        result = enricher.enrich_leads(
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
                
                # Update lead status
                cursor.execute("""
                    UPDATE leads SET status = 'MESSAGED' WHERE id = ?
                """, (lead.id,))
                
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
    """Review messages and approve/reject them."""
    try:
        logger.info(f"MCP Tool: review_messages (auto_approve={request.auto_approve})")
        
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
        
        approved = 0
        rejected = 0
        
        # Review logic
        for msg in messages:
            if request.auto_approve:
                # Auto-approve all
                quality_score = 100
                approved += 1
                new_status = "APPROVED"
            else:
                # Simple quality checks
                content = msg["content"]
                word_count = len(content.split())
                
                # Check word limits
                if msg["channel"] == "email" and word_count > 120:
                    quality_score = 50
                elif msg["channel"] == "linkedin" and word_count > 60:
                    quality_score = 50
                else:
                    quality_score = 80
                
                # Check for CTA
                if any(cta in content.lower() for cta in ["call", "chat", "discuss", "connect"]):
                    quality_score += 10
                
                # Decide
                if quality_score >= request.min_quality_score:
                    approved += 1
                    new_status = "APPROVED"
                else:
                    rejected += 1
                    new_status = "REJECTED"
            
            # Update status
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE messages SET status = ? WHERE id = ?
                """, (new_status, msg["id"]))
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
            
            # Mock sender function
            async def mock_sender(message: Dict) -> bool:
                """Simulate sending (replace with actual email/LinkedIn logic)."""
                logger.info(f"Sending {message['channel']} to {message['lead_name']}")
                return True
            
            # Process queue
            result = await queue.process_with_rate_limit(mock_sender, dry_run=request.dry_run)
            
            return {
                "success": True,
                "action": "send_messages",
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


@app.get("/tools/get_stats")
async def get_stats():
    """Get pipeline statistics."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Lead stats
            cursor.execute("SELECT status, COUNT(*) as count FROM leads GROUP BY status")
            lead_stats = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            # Message stats
            cursor.execute("SELECT status, COUNT(*) as count FROM messages GROUP BY status")
            message_stats = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            # Queue stats
            queue = get_message_queue()
            queue_stats = queue.get_stats()
        
        return {
            "success": True,
            "leads": lead_stats,
            "messages": message_stats,
            "queue": queue_stats,
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
