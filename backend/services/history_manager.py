"""
History Manager - Archives pipeline run data to history table and clears working tables.
"""
import uuid
from datetime import datetime
from typing import Dict
from ..core.logger import logger
from ..core.database import get_db_connection


class HistoryManager:
    """Manages archiving pipeline data to history table."""
    
    @staticmethod
    def archive_pipeline_run(pipeline_run_id: str, dry_run: bool = True) -> Dict:
        """
        Archive current pipeline run data to history table WITHOUT clearing working tables.
        Working tables (leads/messages) are only cleared at the START of a new pipeline run.
        
        Args:
            pipeline_run_id: Unique identifier for this pipeline run
            dry_run: Whether this was a dry run or live run
            
        Returns:
            Dict with archived counts
        """
        try:
            logger.info(f"Starting archive for pipeline run {pipeline_run_id}")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Archive: Join leads and messages, insert into history
                # Archive SENT messages (successfully sent) and APPROVED messages (approved but not yet sent)
                # Exclude REJECTED, PENDING, FAILED, and BOUNCED messages
                cursor.execute("""
                    INSERT INTO history (
                        id, pipeline_run_id, lead_id, full_name, company_name, role, 
                        industry, website, email, linkedin_url, country, 
                        persona_tag, pain_points, buying_triggers, confidence_score,
                        message_id, channel, variant, message_content, message_status,
                        sent_at, dry_run, created_at
                    )
                    SELECT 
                        ? || '_' || l.id || '_' || m.id as id,
                        ? as pipeline_run_id,
                        l.id as lead_id,
                        l.full_name,
                        l.company_name,
                        l.role,
                        l.industry,
                        l.website,
                        l.email,
                        l.linkedin_url,
                        l.country,
                        l.persona_tag,
                        l.pain_points,
                        l.buying_triggers,
                        l.confidence_score,
                        m.id as message_id,
                        m.channel,
                        m.variant,
                        m.content as message_content,
                        m.status as message_status,
                        m.sent_at,
                        ? as dry_run,
                        CURRENT_TIMESTAMP as created_at
                    FROM leads l
                    INNER JOIN messages m ON l.id = m.lead_id
                    WHERE m.status IN ('SENT', 'APPROVED')
                """, (pipeline_run_id, pipeline_run_id, dry_run))
                
                archived_count = cursor.rowcount
                
                # DO NOT clear leads and messages tables here
                # They will be cleared at the START of the next pipeline run
                # This allows viewing the results after pipeline completes
                
                conn.commit()
                
                logger.info(f"Archived {archived_count} records to history (working tables retained)")
                
                return {
                    "success": True,
                    "pipeline_run_id": pipeline_run_id,
                    "archived_records": archived_count,
                    "working_tables_retained": True
                }
                
        except Exception as e:
            logger.error(f"Error archiving pipeline run: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_history(pipeline_run_id: str = None, limit: int = 100) -> Dict:
        """
        Get history records, optionally filtered by pipeline run.
        Only returns SENT and APPROVED messages (excludes REJECTED, PENDING, FAILED, BOUNCED).
        
        Args:
            pipeline_run_id: Optional pipeline run ID to filter by
            limit: Maximum number of records to return
            
        Returns:
            Dict with history records
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if pipeline_run_id:
                    cursor.execute("""
                        SELECT * FROM history 
                        WHERE pipeline_run_id = ?
                        AND message_status IN ('SENT', 'APPROVED')
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (pipeline_run_id, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM history 
                        WHERE message_status IN ('SENT', 'APPROVED')
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))
                
                records = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "success": True,
                    "count": len(records),
                    "records": records
                }
                
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            return {
                "success": False,
                "error": str(e),
                "records": []
            }
    
    @staticmethod
    def get_pipeline_runs(limit: int = 50) -> Dict:
        """Get list of all pipeline runs."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT DISTINCT pipeline_run_id, dry_run, created_at,
                           COUNT(*) as record_count
                    FROM history
                    GROUP BY pipeline_run_id
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                
                runs = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "success": True,
                    "count": len(runs),
                    "runs": runs
                }
                
        except Exception as e:
            logger.error(f"Error fetching pipeline runs: {e}")
            return {
                "success": False,
                "error": str(e),
                "runs": []
            }
