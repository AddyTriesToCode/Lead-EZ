from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Lead(BaseModel):
    """Pydantic schema for Lead validation and API responses."""
    
    id: str
    full_name: str
    company_name: str
    role: str
    industry: str
    website: str
    email: str
    linkedin_url: str
    country: str
    status: str = "NEW"
    
    # Enrichment fields
    company_size: Optional[str] = None
    persona_tag: Optional[str] = None
    pain_points: Optional[str] = None  # JSON string
    buying_triggers: Optional[str] = None  # JSON string
    confidence_score: Optional[int] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LeadCreate(BaseModel):
    """Schema for creating a new lead."""
    full_name: str
    company_name: str
    role: str
    industry: str
    website: str
    email: str
    linkedin_url: str
    country: str


class LeadUpdate(BaseModel):
    """Schema for updating a lead."""
    status: Optional[str] = None
    company_size: Optional[str] = None
    persona_tag: Optional[str] = None
    pain_points: Optional[str] = None
    buying_triggers: Optional[str] = None
    confidence_score: Optional[int] = None
