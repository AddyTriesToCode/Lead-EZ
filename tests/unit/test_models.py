"""Unit tests for Pydantic models."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from backend.models.lead import Lead, LeadCreate, LeadUpdate
from backend.models.message import Message, MessageCreate


class TestLeadModel:
    """Test cases for Lead model."""
    
    def test_lead_creation_with_all_fields(self):
        """Test creating a Lead with all required fields."""
        lead = Lead(
            id="test-123",
            full_name="John Doe",
            company_name="Tech Corp",
            role="CTO",
            industry="Technology",
            website="https://techcorp.com",
            email="john@techcorp.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            country="USA"
        )
        
        assert lead.id == "test-123"
        assert lead.full_name == "John Doe"
        assert lead.status == "NEW"  # Default value
    
    def test_lead_with_enrichment_fields(self):
        """Test Lead with optional enrichment fields."""
        lead = Lead(
            id="test-456",
            full_name="Jane Smith",
            company_name="Startup Inc",
            role="CEO",
            industry="Healthcare",
            website="https://startup.com",
            email="jane@startup.com",
            linkedin_url="https://linkedin.com/in/janesmith",
            country="UK",
            company_size="50-200",
            persona_tag="innovator",
            confidence_score=85
        )
        
        assert lead.company_size == "50-200"
        assert lead.persona_tag == "innovator"
        assert lead.confidence_score == 85
    
    def test_lead_create_validation(self):
        """Test LeadCreate schema validation."""
        lead_data = {
            "full_name": "Test User",
            "company_name": "Test Company",
            "role": "Manager",
            "industry": "Technology",
            "website": "https://test.com",
            "email": "test@test.com",
            "linkedin_url": "https://linkedin.com/in/test",
            "country": "USA"
        }
        
        lead_create = LeadCreate(**lead_data)
        assert lead_create.full_name == "Test User"
        assert lead_create.email == "test@test.com"
    
    def test_lead_create_missing_required_field(self):
        """Test that LeadCreate fails without required fields."""
        with pytest.raises(ValidationError):
            LeadCreate(
                full_name="Test User",
                # Missing other required fields
            )
    
    def test_lead_update_partial(self):
        """Test LeadUpdate with partial data."""
        update = LeadUpdate(
            status="ENRICHED",
            confidence_score=90
        )
        
        assert update.status == "ENRICHED"
        assert update.confidence_score == 90
        assert update.company_size is None
    
    def test_lead_update_all_optional(self):
        """Test that all LeadUpdate fields are optional."""
        update = LeadUpdate()
        
        assert update.status is None
        assert update.company_size is None
        assert update.persona_tag is None


class TestMessageModel:
    """Test cases for Message model."""
    
    def test_message_creation(self):
        """Test creating a Message with required fields."""
        message = Message(
            id="msg-123",
            lead_id="lead-456",
            channel="email",
            variant="A",
            content="Test message content"
        )
        
        assert message.id == "msg-123"
        assert message.lead_id == "lead-456"
        assert message.channel == "email"
        assert message.variant == "A"
        assert message.status == "PENDING"  # Default value
        assert message.retry_count == 0  # Default value
    
    def test_message_with_optional_fields(self):
        """Test Message with optional fields."""
        sent_time = datetime.now()
        message = Message(
            id="msg-789",
            lead_id="lead-123",
            channel="linkedin",
            variant="B",
            content="LinkedIn message",
            status="SENT",
            sent_at=sent_time,
            retry_count=2
        )
        
        assert message.status == "SENT"
        assert message.sent_at == sent_time
        assert message.retry_count == 2
    
    def test_message_with_error(self):
        """Test Message with error information."""
        message = Message(
            id="msg-error",
            lead_id="lead-999",
            channel="email",
            variant="A",
            content="Failed message",
            status="FAILED",
            error_message="SMTP connection failed",
            retry_count=3
        )
        
        assert message.status == "FAILED"
        assert message.error_message == "SMTP connection failed"
        assert message.retry_count == 3
    
    def test_message_create_validation(self):
        """Test MessageCreate schema validation."""
        message_data = {
            "lead_id": "lead-123",
            "channel": "email",
            "variant": "A",
            "content": "Test content"
        }
        
        message_create = MessageCreate(**message_data)
        assert message_create.lead_id == "lead-123"
        assert message_create.channel == "email"
    
    def test_message_create_missing_required_field(self):
        """Test that MessageCreate fails without required fields."""
        with pytest.raises(ValidationError):
            MessageCreate(
                lead_id="lead-123",
                channel="email"
                # Missing variant and content
            )
    
    def test_message_channels(self):
        """Test valid message channels."""
        for channel in ["email", "linkedin"]:
            message = Message(
                id=f"msg-{channel}",
                lead_id="lead-123",
                channel=channel,
                variant="A",
                content="Test"
            )
            assert message.channel == channel
    
    def test_message_variants(self):
        """Test valid message variants."""
        for variant in ["A", "B"]:
            message = Message(
                id=f"msg-{variant}",
                lead_id="lead-123",
                channel="email",
                variant=variant,
                content="Test"
            )
            assert message.variant == variant
