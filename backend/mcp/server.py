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
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
from datetime import datetime
from ..core.logger import logger
from ..core.config import settings
from ..core.database import get_db_connection
from ..services.lead_generator import LeadGenerator
from ..services.enricher import Enricher
from ..services.message_generator import MessageGenerator
from ..services.message_queue import get_message_queue
from ..services.history_manager import HistoryManager
from ..models.lead import Lead
from ..agent.decision_engine import AgentDecisionEngine



# ============================================================================
# REQUEST MODELS
# ============================================================================

class GenerateLeadsRequest(BaseModel):
    count: int = None
    save_to_db: bool = True
    seed: Optional[int] = None  # Random seed for reproducibility (auto-generated if not provided)


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

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        # Generate random seed if not provided
        import random
        seed_value = request.seed if request.seed is not None else random.randint(1, 9999)
        
        logger.info(f"MCP Tool: generate_leads (count={request.count}, seed={seed_value})")
        
        generator = LeadGenerator(seed=seed_value)
        
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
            
            # Leads above confidence threshold (>= 60)
            cursor.execute("SELECT COUNT(*) as count FROM leads WHERE confidence_score >= 60")
            leads_above_threshold = cursor.fetchone()["count"]
            
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
            
            # Calculate total approved (APPROVED + SENT, since SENT messages were previously approved)
            total_approved = message_stats.get("APPROVED", 0) + message_stats.get("SENT", 0)
            
            # Calculate leads_enriched (ENRICHED + CONTACTED, since CONTACTED leads were previously enriched)
            leads_enriched = lead_stats.get("ENRICHED", 0) + lead_stats.get("CONTACTED", 0)
        
        return {
            "success": True,
            "summary": {
                "total_leads": total_leads,
                "leads_enriched": leads_enriched,
                "leads_above_threshold": leads_above_threshold,
                "total_messages": total_messages,
                "messages_sent": message_stats.get("SENT", 0),
                "messages_failed": message_stats.get("FAILED", 0),
                "messages_pending": message_stats.get("PENDING", 0)
            },
            "leads": lead_stats,
            "messages": {**message_stats, "APPROVED": total_approved},
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


@app.post("/webhooks/sendgrid")
async def sendgrid_webhook(request: Request):
    """Handle SendGrid webhook events (bounce, dropped, spam report)."""
    try:
        events = await request.json()
        logger.info(f"Received {len(events)} SendGrid webhook events")
        
        processed = 0
        for event in events:
            event_type = event.get("event")
            email = event.get("email")
            message_id_header = event.get("message_id")  # SendGrid's message ID
            reason = event.get("reason", "")
            
            # Handle bounce/dropped/spam report events
            if event_type in ["bounce", "dropped", "spamreport"]:
                logger.warning(f"Email {event_type} for {email}: {reason}")
                
                # Find message by recipient email
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Find the most recent SENT message for this email
                    cursor.execute("""
                        SELECT m.id, m.lead_id 
                        FROM messages m
                        JOIN leads l ON m.lead_id = l.id
                        WHERE l.email = ? AND m.status = 'SENT' AND m.channel = 'email'
                        ORDER BY m.sent_at DESC
                        LIMIT 1
                    """, (email,))
                    
                    message = cursor.fetchone()
                    
                    if message:
                        msg_id = message["id"]
                        lead_id = message["lead_id"]
                        
                        # Update message status to BOUNCED
                        cursor.execute("""
                            UPDATE messages 
                            SET status = 'BOUNCED', error_message = ?
                            WHERE id = ?
                        """, (f"{event_type}: {reason}", msg_id))
                        
                        # Check if all messages for this lead have bounced
                        cursor.execute("""
                            SELECT COUNT(*) as total,
                                   SUM(CASE WHEN status = 'BOUNCED' THEN 1 ELSE 0 END) as bounced
                            FROM messages
                            WHERE lead_id = ? AND channel = 'email'
                        """, (lead_id,))
                        
                        stats = cursor.fetchone()
                        
                        # If all email messages bounced, mark lead as UNCONTACTED
                        if stats["total"] == stats["bounced"]:
                            cursor.execute("""
                                UPDATE leads 
                                SET status = 'UNCONTACTED', updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (lead_id,))
                            logger.info(f"Lead {lead_id} marked as UNCONTACTED (all messages bounced)")
                        
                        conn.commit()
                        processed += 1
                        logger.info(f"Message {msg_id} marked as BOUNCED")
                    else:
                        logger.warning(f"No SENT message found for bounced email: {email}")
            
            elif event_type == "delivered":
                # Confirmation that email was actually delivered
                logger.info(f"Email delivered to {email}")
        
        return {
            "success": True,
            "processed": processed,
            "total_events": len(events)
        }
    
    except Exception as e:
        logger.error(f"Error processing SendGrid webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/run_pipeline")
async def run_pipeline(request: dict = None):
    """Run the entire pipeline from start to finish.
    
    This endpoint executes all pipeline stages sequentially:
    1. Generate leads
    2. Enrich leads
    3. Generate messages
    4. Review messages
    5. Send messages (if not dry run)
    6. Archive to history
    """
    try:
        # Extract configuration parameters from request
        config = request or {}
        lead_count = int(config.get("leadCount", 100))
        seed = int(config.get("seed")) if config.get("seed") else None
        enrichment_mode = config.get("enrichmentMode", "offline")
        
        # Get or generate pipeline_run_id
        pipeline_run_id = config.get("pipelineRunId")
        if not pipeline_run_id:
            import uuid
            pipeline_run_id = f"run_{int(__import__('time').time() * 1000)}_{str(uuid.uuid4())[:8]}"
        
        # Handle dryRun as boolean (could be string "true"/"false" or bool)
        dry_run_value = config.get("dryRun", True)
        if isinstance(dry_run_value, str):
            dry_run = dry_run_value.lower() in ("true", "1", "yes")
        else:
            dry_run = bool(dry_run_value)
        
        logger.info(f"MCP Tool: run_pipeline - Starting pipeline {pipeline_run_id} (leadCount={lead_count}, seed={seed}, mode={enrichment_mode}, dryRun={dry_run})")
        
        # Clear working tables at start of new pipeline run
        logger.info("Clearing working tables for new pipeline run...")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages")
            cursor.execute("DELETE FROM leads")
            conn.commit()
        
        # Track results from each stage
        pipeline_results = {
            "generate_leads": None,
            "enrich_leads": None,
            "generate_messages": None,
            "review_messages": None,
            "send_messages": None
        }
        
        # Stage 1: Generate leads
        logger.info(f"Stage 1/5: Generating {lead_count} leads...")
        pipeline_results["generate_leads"] = await generate_leads(GenerateLeadsRequest(
            count=lead_count,
            seed=seed,
            save_to_db=True
        ))
        
        # Stage 2: Enrich leads
        logger.info("Stage 2/5: Enriching leads...")
        pipeline_results["enrich_leads"] = await enrich_leads(EnrichLeadsRequest(
            mode=enrichment_mode,
            limit=lead_count  # Enrich all the leads we just generated
        ))
        
        # Stage 3: Generate messages
        logger.info("Stage 3/5: Generating messages...")
        pipeline_results["generate_messages"] = await generate_messages(GenerateMessagesRequest(
            limit=lead_count,  # Generate messages for all enriched leads
            min_confidence_score=60
        ))
        
        # Stage 4: Review messages
        logger.info("Stage 4/5: Reviewing messages...")
        pipeline_results["review_messages"] = await review_messages(ReviewMessagesRequest())
        
        # Stage 5: Send messages (with appropriate mode)
        if dry_run:
            logger.info("Stage 5/5: Saving messages to JSON file (dry run mode)...")
            pipeline_results["send_messages"] = await send_messages(SendMessagesRequest(
                use_queue=True,
                batch_size=50,
                dry_run=True  # Save to storage/messages/dry_run_messages.json
            ))
        else:
            logger.info("Stage 5/5: Sending messages via SMTP (live mode)...")
            pipeline_results["send_messages"] = await send_messages(SendMessagesRequest(
                use_queue=True,
                batch_size=50,
                dry_run=False  # Actually send via email/LinkedIn
            ))
        
        logger.info(f"Pipeline {pipeline_run_id} completed successfully!")
        
        # Archive data to history (working tables retained)
        logger.info(f"Archiving pipeline {pipeline_run_id} to history...")
        archive_result = HistoryManager.archive_pipeline_run(
            pipeline_run_id=pipeline_run_id,
            dry_run=dry_run
        )
        
        if archive_result["success"]:
            logger.info(f"Successfully archived {archive_result['archived_records']} records to history (working tables retained)")
        else:
            logger.error(f"Failed to archive data: {archive_result.get('error')}")
        
        return {
            "success": True,
            "message": "Pipeline completed all stages",
            "config": {
                "leadCount": lead_count,
                "seed": seed,
                "enrichmentMode": enrichment_mode,
                "dryRun": dry_run
            },
            "results": pipeline_results,
            "archive": archive_result,
            "pipeline_run_id": pipeline_run_id,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in run_pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/archive_pipeline")
async def archive_pipeline(request: dict = None):
    """Archive current pipeline data to history and clear working tables."""
    try:
        config = request or {}
        pipeline_run_id = config.get("pipeline_run_id", str(__import__('uuid').uuid4()))
        dry_run = config.get("dry_run", True)
        
        logger.info(f"Archiving pipeline run {pipeline_run_id}")
        
        result = HistoryManager.archive_pipeline_run(
            pipeline_run_id=pipeline_run_id,
            dry_run=dry_run
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in archive_pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/get_history")
async def get_history(pipeline_run_id: Optional[str] = None, limit: int = 100):
    """Get history records, optionally filtered by pipeline run."""
    try:
        result = HistoryManager.get_history(pipeline_run_id=pipeline_run_id, limit=limit)
        return result
        
    except Exception as e:
        logger.error(f"Error in get_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/get_pipeline_runs")
async def get_pipeline_runs(limit: int = 50):
    """Get list of all pipeline runs from history."""
    try:
        result = HistoryManager.get_pipeline_runs(limit=limit)
        return result
        
    except Exception as e:
        logger.error(f"Error in get_pipeline_runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/clear_dry_run_messages")
async def clear_dry_run_messages():
    """Clear the dry run messages file."""
    try:
        from pathlib import Path
        dry_run_file = Path("storage/messages/dry_run_messages.json")
        
        if dry_run_file.exists():
            dry_run_file.unlink()
            logger.info("Cleared dry run messages file")
            return {
                "success": True,
                "message": "Dry run messages cleared"
            }
        else:
            return {
                "success": True,
                "message": "No dry run messages file found"
            }
    except Exception as e:
        logger.error(f"Error clearing dry run messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/clear_working_tables")
async def clear_working_tables():
    """Clear leads and messages tables to start fresh pipeline run."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Clear messages first (foreign key constraint)
            cursor.execute("DELETE FROM messages")
            deleted_messages = cursor.rowcount
            
            # Clear leads
            cursor.execute("DELETE FROM leads")
            deleted_leads = cursor.rowcount
            
            conn.commit()
            
        logger.info(f"Cleared working tables: {deleted_leads} leads, {deleted_messages} messages")
        return {
            "success": True,
            "deleted_leads": deleted_leads,
            "deleted_messages": deleted_messages
        }
    except Exception as e:
        logger.error(f"Error clearing working tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/get_dry_run_messages")
async def get_dry_run_messages():
    """Get all dry run messages from the storage file."""
    try:
        from pathlib import Path
        dry_run_file = Path("storage/messages/dry_run_messages.json")
        
        if not dry_run_file.exists():
            return {
                "success": True,
                "messages": [],
                "count": 0
            }
        
        with open(dry_run_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
            if not isinstance(messages, list):
                messages = []
        
        return {
            "success": True,
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error reading dry run messages: {e}")
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
