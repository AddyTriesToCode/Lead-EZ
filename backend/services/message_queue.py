"""Message queue service for batch processing and rate-limited delivery."""
import asyncio
import time
from collections import deque
from typing import List, Dict, Optional
from datetime import datetime
from ..core.logger import logger
from ..core.database import get_db_connection
from ..core.config import settings
from .message_sender import create_sender


class MessageQueue:
    """In-memory queue for batch-processing messages with rate limiting."""
    
    def __init__(self, batch_size: int = 50, max_per_minute: int = None):
        """Initialize the message queue.
        
        Args:
            batch_size: Number of messages to fetch from DB at once
            max_per_minute: Rate limit for sending (None uses settings default)
        """
        self.batch_size = batch_size
        self.max_per_minute = max_per_minute or settings.max_messages_per_minute
        self.queue = deque()
        self.processing = False
        self.stats = {
            "total_fetched": 0,
            "total_sent": 0,
            "total_failed": 0,
            "batch_count": 0
        }
        logger.info(f"MessageQueue initialized: batch_size={batch_size}, rate_limit={self.max_per_minute}/min")
    
    def fetch_batch(self, status: str = "PENDING", channel: Optional[str] = None) -> int:
        """Fetch a batch of messages from database into the queue.
        
        Args:
            status: Message status to fetch (default: PENDING)
            channel: Optional channel filter (email or linkedin)
            
        Returns:
            Number of messages fetched
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                query = """
                    SELECT m.id, m.lead_id, m.channel, m.variant, m.content, m.status,
                           l.full_name, l.email, l.company_name, l.role
                    FROM messages m
                    JOIN leads l ON m.lead_id = l.id
                    WHERE m.status = ?
                """
                params = [status]
                
                if channel:
                    query += " AND m.channel = ?"
                    params.append(channel)
                
                query += " ORDER BY m.created_at ASC LIMIT ?"
                params.append(self.batch_size)
                
                cursor.execute(query, params)
                messages = cursor.fetchall()
                
                # Add to queue
                for msg in messages:
                    self.queue.append({
                        "id": msg["id"],
                        "lead_id": msg["lead_id"],
                        "channel": msg["channel"],
                        "variant": msg["variant"],
                        "content": msg["content"],
                        "status": msg["status"],
                        "lead_name": msg["full_name"],
                        "lead_email": msg["email"],
                        "company": msg["company_name"],
                        "role": msg["role"]
                    })
                
                fetched = len(messages)
                self.stats["total_fetched"] += fetched
                self.stats["batch_count"] += 1
                
                logger.info(f"Fetched batch #{self.stats['batch_count']}: {fetched} messages (queue size: {len(self.queue)})")
                return fetched
                
        except Exception as e:
            logger.error(f"Error fetching message batch: {e}")
            return 0
    
    def get_next(self) -> Optional[Dict]:
        """Get the next message from the queue.
        
        Returns:
            Message dict or None if queue is empty
        """
        if self.queue:
            return self.queue.popleft()
        return None
    
    def size(self) -> int:
        """Return current queue size."""
        return len(self.queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self.queue) == 0
    
    def auto_refill(self, min_threshold: int = 10) -> int:
        """Automatically refill queue when below threshold.
        
        Args:
            min_threshold: Refill when queue size drops below this
            
        Returns:
            Number of messages fetched (0 if no refill needed)
        """
        if len(self.queue) < min_threshold:
            logger.debug(f"Queue below threshold ({len(self.queue)} < {min_threshold}), refilling...")
            return self.fetch_batch()
        return 0
    
    async def process_with_rate_limit(self, dry_run: bool = True) -> Dict:
        """Process messages from queue with rate limiting.
        
        Args:
            dry_run: If True, save to storage. If False, actually send via SMTP.
            
        Returns:
            Processing statistics
        """
        self.processing = True
        sent = 0
        failed = 0
        start_time = time.time()
        
        # Create sender with appropriate mode
        sender = create_sender(dry_run=dry_run)
        
        # Calculate delay between messages for rate limiting
        delay_seconds = 60.0 / self.max_per_minute
        
        mode = "DRY RUN (saving to storage)" if dry_run else "LIVE (sending via SMTP)"
        logger.info(f"Starting message processing in {mode} (rate: {self.max_per_minute}/min, delay: {delay_seconds:.2f}s)")
        
        try:
            while not self.is_empty():
                # Auto-refill if needed
                self.auto_refill(min_threshold=10)
                
                message = self.get_next()
                if not message:
                    break
                
                try:
                    # Send message using sender module
                    success = await sender.send_message(message)
                    
                    # Update message status (keep APPROVED in dry run mode)
                    if dry_run:
                        # In dry run mode, keep messages as APPROVED (don't change status)
                        if success:
                            logger.info(f"[DRY RUN] Message {message['id']} saved to storage, keeping status=APPROVED")
                        else:
                            self._update_message_status(message["id"], "FAILED", error="Dry run save failed")
                    else:
                        # In live mode, update status to SENT or FAILED
                        self._update_message_status(
                            message["id"],
                            "SENT" if success else "FAILED",
                            error=None if success else "Delivery failed"
                        )
                        
                        # Update lead status to SENT after first successful message (live mode only)
                        if success:
                            self._update_lead_status(message["lead_id"], "SENT")
                    
                    if success:
                        sent += 1
                        self.stats["total_sent"] += 1
                    else:
                        failed += 1
                        self.stats["total_failed"] += 1
                    
                    # Rate limiting delay
                    await asyncio.sleep(delay_seconds)
                    
                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {e}")
                    self._update_message_status(message["id"], "FAILED", error=str(e))
                    failed += 1
                    self.stats["total_failed"] += 1
            
            elapsed = time.time() - start_time
            logger.info(f"Processing complete: {sent} sent, {failed} failed in {elapsed:.1f}s")
            
            return {
                "sent": sent,
                "failed": failed,
                "elapsed_seconds": elapsed,
                "rate_per_minute": (sent / elapsed * 60) if elapsed > 0 else 0
            }
            
        finally:
            self.processing = False
    
    def _update_message_status(self, message_id: str, status: str, error: Optional[str] = None):
        """Update message status in database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if error:
                    cursor.execute("""
                        UPDATE messages 
                        SET status = ?, error_message = ?, retry_count = retry_count + 1
                        WHERE id = ?
                    """, (status, error, message_id))
                else:
                    cursor.execute("""
                        UPDATE messages 
                        SET status = ?, sent_at = ?
                        WHERE id = ?
                    """, (status, datetime.now(), message_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating message status: {e}")
    
    def _update_lead_status(self, lead_id: str, status: str):
        """Update lead status in database after sending messages."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE leads 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, lead_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating lead status: {e}")
    
    def batch_update_statuses(self, updates: List[Dict]) -> int:
        """Batch update multiple message statuses.
        
        Args:
            updates: List of dicts with 'id', 'status', 'error' keys
            
        Returns:
            Number of messages updated
        """
        if not updates:
            return 0
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                for update in updates:
                    msg_id = update["id"]
                    status = update["status"]
                    error = update.get("error")
                    
                    if error:
                        cursor.execute("""
                            UPDATE messages 
                            SET status = ?, error_message = ?, retry_count = retry_count + 1
                            WHERE id = ?
                        """, (status, error, msg_id))
                    else:
                        cursor.execute("""
                            UPDATE messages 
                            SET status = ?, sent_at = ?
                            WHERE id = ?
                        """, (status, datetime.now(), msg_id))
                
                conn.commit()
                logger.info(f"Batch updated {len(updates)} message statuses")
                return len(updates)
                
        except Exception as e:
            logger.error(f"Error in batch update: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get queue statistics."""
        return {
            **self.stats,
            "current_queue_size": len(self.queue),
            "is_processing": self.processing
        }
    
    def clear(self):
        """Clear the queue (use with caution)."""
        self.queue.clear()
        logger.warning("Queue cleared")


# Singleton instance
_queue_instance = None


def get_message_queue(batch_size: int = 50, max_per_minute: int = None) -> MessageQueue:
    """Get or create the global message queue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = MessageQueue(batch_size, max_per_minute)
    return _queue_instance
