from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Message(BaseModel):
    """Pydantic schema for Message validation and API responses."""
    
    id: str
    lead_id: str
    channel: str  # email or linkedin
    variant: str  # A or B
    content: str
    status: str = "PENDING"
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    lead_id: str
    channel: str
    variant: str
    content: str
