"""Message sender with dry-run (file storage) and live-run (SMTP) modes."""
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from ..core.logger import logger
from ..core.config import settings


class MessageSender:
    """Handles message delivery via email (SMTP) or saves to storage in dry-run mode."""
    
    def __init__(self, dry_run: bool = True):
        """Initialize sender.
        
        Args:
            dry_run: If True, save messages to files. If False, actually send them.
        """
        self.dry_run = dry_run
        self.storage_path = Path("storage/messages")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        if not dry_run and settings.smtp_enabled:
            logger.info(f"MessageSender initialized in LIVE mode (SMTP: {settings.smtp_host}:{settings.smtp_port})")
        else:
            logger.info(f"MessageSender initialized in DRY RUN mode (storage: {self.storage_path})")
    
    async def send_message(self, message: Dict) -> bool:
        """Send a message or save to storage.
        
        Args:
            message: Message dict with id, channel, content, lead_email, lead_name, etc.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.dry_run:
                return await self._save_to_storage(message)
            else:
                if message["channel"] == "email":
                    return await self._send_email(message)
                elif message["channel"] == "linkedin":
                    return await self._send_linkedin(message)
                else:
                    logger.error(f"Unknown channel: {message['channel']}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending message {message['id']}: {e}")
            return False
    
    async def _save_to_storage(self, message: Dict) -> bool:
        """Save message to storage file (dry-run mode).
        
        File format: storage/messages/{timestamp}_{channel}_{lead_name}.json
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            lead_name_safe = message["lead_name"].replace(" ", "_").replace("/", "_")
            filename = f"{timestamp}_{message['channel']}_{message['variant']}_{lead_name_safe}.json"
            filepath = self.storage_path / filename
            
            # Prepare message data for storage
            message_data = {
                "message_id": message["id"],
                "lead_id": message["lead_id"],
                "timestamp": timestamp,
                "channel": message["channel"],
                "variant": message["variant"],
                "lead": {
                    "name": message["lead_name"],
                    "email": message.get("lead_email"),
                    "company": message.get("company"),
                    "role": message.get("role")
                },
                "content": message["content"],
                "status": "DRY_RUN_SAVED"
            }
            
            # Save to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(message_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[DRY RUN] Saved {message['channel']} message to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving message to storage: {e}")
            return False
    
    async def _send_email(self, message: Dict) -> bool:
        """Send email via SMTP (live mode)."""
        if not settings.smtp_enabled:
            logger.warning("SMTP not enabled in settings, cannot send email")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = self._extract_subject(message["content"])
            msg["From"] = settings.smtp_from
            msg["To"] = message["lead_email"]
            
            # Add content (assume plain text for now)
            body = MIMEText(message["content"], "plain")
            msg.attach(body)
            
            # Connect and send
            if settings.smtp_use_tls:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            
            # Login if credentials provided
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"[LIVE] Sent email to {message['lead_email']} ({message['lead_name']})")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def _send_linkedin(self, message: Dict) -> bool:
        """Send LinkedIn message (live mode).
        
        TODO: Implement LinkedIn API or browser automation.
        For now, this is a placeholder that saves to storage with TODO marker.
        """
        logger.warning("LinkedIn sending not implemented yet, saving to storage instead")
        
        # Save with special marker
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        lead_name_safe = message["lead_name"].replace(" ", "_").replace("/", "_")
        filename = f"{timestamp}_linkedin_TODO_{lead_name_safe}.json"
        filepath = self.storage_path / filename
        
        message_data = {
            "message_id": message["id"],
            "lead_id": message["lead_id"],
            "timestamp": timestamp,
            "channel": "linkedin",
            "variant": message["variant"],
            "lead": {
                "name": message["lead_name"],
                "email": message.get("lead_email"),
                "company": message.get("company"),
                "role": message.get("role")
            },
            "content": message["content"],
            "status": "PENDING_LINKEDIN_IMPLEMENTATION",
            "note": "LinkedIn sending not implemented - manual action required"
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(message_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[LIVE] LinkedIn message saved to {filename} - manual sending required")
        return True
    
    def _extract_subject(self, content: str) -> str:
        """Extract subject line from email content.
        
        Assumes first line or first 50 characters is the subject.
        """
        lines = content.strip().split("\n")
        if lines:
            subject = lines[0].strip()
            # Remove common prefixes
            for prefix in ["Subject:", "subject:", "SUBJECT:"]:
                if subject.startswith(prefix):
                    subject = subject[len(prefix):].strip()
            return subject[:100]  # Limit subject length
        return "Message from Lead-EZ"
    
    def get_stats(self) -> Dict:
        """Get sender statistics."""
        # Count files in storage
        message_files = list(self.storage_path.glob("*.json"))
        
        return {
            "mode": "dry_run" if self.dry_run else "live",
            "smtp_enabled": settings.smtp_enabled,
            "storage_path": str(self.storage_path),
            "stored_messages": len(message_files)
        }


# Factory function
def create_sender(dry_run: bool = True) -> MessageSender:
    """Create a message sender instance."""
    return MessageSender(dry_run=dry_run)
