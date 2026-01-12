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
        
        # Single file for all dry run messages
        self.dry_run_file = self.storage_path / "dry_run_messages.json"
        
        if not dry_run and settings.smtp_enabled:
            logger.info(f"MessageSender initialized in LIVE mode (SMTP: {settings.smtp_host}:{settings.smtp_port})")
        else:
            logger.info(f"MessageSender initialized in DRY RUN mode (storage: {self.dry_run_file})")
    
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
        """Save message to single JSON file (dry-run mode).
        
        All approved messages are appended to storage/messages/dry_run_messages.json
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Prepare message data for storage
            message_data = {
                "message_id": message["id"],
                "lead_id": message["lead_id"],
                "timestamp": timestamp,
                "saved_at": datetime.now().isoformat(),
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
            
            # Load existing messages or create new list
            if self.dry_run_file.exists():
                with open(self.dry_run_file, "r", encoding="utf-8") as f:
                    try:
                        all_messages = json.load(f)
                        if not isinstance(all_messages, list):
                            all_messages = []
                    except json.JSONDecodeError:
                        all_messages = []
            else:
                all_messages = []
            
            # Append new message
            all_messages.append(message_data)
            
            # Save back to file
            with open(self.dry_run_file, "w", encoding="utf-8") as f:
                json.dump(all_messages, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[DRY RUN] Appended {message['channel']} message for {message['lead_name']} to {self.dry_run_file.name} (total: {len(all_messages)})")
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
        """Save LinkedIn message to file for manual outreach.
        
        LinkedIn API integration requires OAuth and app setup.
        For now, save messages to a file that can be used for:
        1. Manual LinkedIn outreach
        2. Integration with LinkedIn automation tools
        3. Future LinkedIn API implementation
        """
        try:
            linkedin_file = self.storage_path / "linkedin_outreach.json"
            
            # Prepare message data
            message_data = {
                "message_id": message["id"],
                "lead_id": message["lead_id"],
                "timestamp": datetime.now().isoformat(),
                "channel": "linkedin",
                "variant": message["variant"],
                "lead": {
                    "name": message["lead_name"],
                    "company": message.get("company"),
                    "role": message.get("role"),
                    "linkedin_url": message.get("linkedin_url", "Not available")
                },
                "content": message["content"],
                "status": "READY_FOR_LINKEDIN_OUTREACH"
            }
            
            # Load existing messages or create new list
            if linkedin_file.exists():
                with open(linkedin_file, "r", encoding="utf-8") as f:
                    try:
                        all_messages = json.load(f)
                        if not isinstance(all_messages, list):
                            all_messages = []
                    except json.JSONDecodeError:
                        all_messages = []
            else:
                all_messages = []
            
            # Append new message
            all_messages.append(message_data)
            
            # Save back to file
            with open(linkedin_file, "w", encoding="utf-8") as f:
                json.dump(all_messages, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[LIVE] Saved LinkedIn message for {message['lead_name']} to {linkedin_file.name} (total: {len(all_messages)})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving LinkedIn message: {e}")
            return False
    
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
        # Count messages in the single dry run file
        stored_count = 0
        if self.dry_run and self.dry_run_file.exists():
            try:
                with open(self.dry_run_file, "r", encoding="utf-8") as f:
                    all_messages = json.load(f)
                    if isinstance(all_messages, list):
                        stored_count = len(all_messages)
            except (json.JSONDecodeError, Exception):
                stored_count = 0
        
        return {
            "mode": "dry_run" if self.dry_run else "live",
            "smtp_enabled": settings.smtp_enabled,
            "storage_path": str(self.storage_path),
            "dry_run_file": str(self.dry_run_file) if self.dry_run else None,
            "stored_messages": stored_count
        }


# Factory function
def create_sender(dry_run: bool = True) -> MessageSender:
    """Create a message sender instance."""
    return MessageSender(dry_run=dry_run)
