"""Unit tests for MessageGenerator service."""
import pytest
import json
from backend.services.message_generator import MessageGenerator
from backend.models.lead import Lead
from datetime import datetime


class TestMessageGenerator:
    """Test cases for MessageGenerator."""
    
    @pytest.fixture
    def sample_lead(self):
        """Create a sample lead for testing."""
        return Lead(
            id="test-123",
            full_name="John Doe",
            company_name="Tech Corp",
            role="CTO",
            industry="Technology",
            website="https://techcorp.com",
            email="john.doe@techcorp.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            country="USA",
            status="NEW",
            company_size="50-200",
            persona_tag="innovator",
            pain_points=json.dumps(["scaling challenges", "technical debt"]),
            buying_triggers=json.dumps(["recent funding", "team expansion"]),
            confidence_score=85
        )
    
    def test_initialization(self):
        """Test that MessageGenerator initializes with CTAs."""
        generator = MessageGenerator()
        assert len(generator.ctas) > 0
        assert all(isinstance(cta, str) for cta in generator.ctas)
    
    def test_generate_four_messages_per_lead(self, sample_lead):
        """Test that 4 messages are generated per lead."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        assert len(messages) == 4
    
    def test_message_structure(self, sample_lead):
        """Test that each message has correct structure."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        for message in messages:
            assert "channel" in message
            assert "variant" in message
            assert "content" in message
            assert message["channel"] in ["email", "linkedin"]
            assert message["variant"] in ["A", "B"]
            assert len(message["content"]) > 0
    
    def test_email_variants_generated(self, sample_lead):
        """Test that both email variants are generated."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        email_messages = [m for m in messages if m["channel"] == "email"]
        assert len(email_messages) == 2
        
        variants = [m["variant"] for m in email_messages]
        assert "A" in variants
        assert "B" in variants
    
    def test_linkedin_variants_generated(self, sample_lead):
        """Test that both LinkedIn variants are generated."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        linkedin_messages = [m for m in messages if m["channel"] == "linkedin"]
        assert len(linkedin_messages) == 2
        
        variants = [m["variant"] for m in linkedin_messages]
        assert "A" in variants
        assert "B" in variants
    
    def test_message_personalization(self, sample_lead):
        """Test that messages include lead-specific information."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        for message in messages:
            content = message["content"]
            # Check for personalization elements
            assert sample_lead.full_name.split()[0] in content or sample_lead.company_name in content
    
    def test_email_has_subject_line(self, sample_lead):
        """Test that email messages have subject lines."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        email_messages = [m for m in messages if m["channel"] == "email"]
        for message in email_messages:
            assert "Subject:" in message["content"]
    
    def test_linkedin_no_subject_line(self, sample_lead):
        """Test that LinkedIn messages don't have subject lines."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        linkedin_messages = [m for m in messages if m["channel"] == "linkedin"]
        for message in linkedin_messages:
            assert "Subject:" not in message["content"]
    
    def test_message_includes_cta(self, sample_lead):
        """Test that messages include a call-to-action."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        # At least some messages should contain CTAs
        has_cta = False
        for message in messages:
            content = message["content"].lower()
            for cta in generator.ctas:
                if cta.lower() in content:
                    has_cta = True
                    break
        
        assert has_cta
    
    def test_lead_without_enrichment(self):
        """Test message generation for lead without enrichment data."""
        lead = Lead(
            id="test-456",
            full_name="Jane Smith",
            company_name="Startup Inc",
            role="CEO",
            industry="Technology",
            website="https://startup.com",
            email="jane@startup.com",
            linkedin_url="https://linkedin.com/in/janesmith",
            country="UK",
            status="NEW"
        )
        
        generator = MessageGenerator()
        messages = generator.generate_messages(lead)
        
        # Should still generate 4 messages even without enrichment
        assert len(messages) == 4
        
        # Messages should have default content
        for message in messages:
            assert len(message["content"]) > 0
    
    def test_message_variants_are_different(self, sample_lead):
        """Test that variant A and B messages are different."""
        generator = MessageGenerator()
        messages = generator.generate_messages(sample_lead)
        
        email_a = next(m for m in messages if m["channel"] == "email" and m["variant"] == "A")
        email_b = next(m for m in messages if m["channel"] == "email" and m["variant"] == "B")
        
        # Variants should have different content
        assert email_a["content"] != email_b["content"]
        
        linkedin_a = next(m for m in messages if m["channel"] == "linkedin" and m["variant"] == "A")
        linkedin_b = next(m for m in messages if m["channel"] == "linkedin" and m["variant"] == "B")
        
        assert linkedin_a["content"] != linkedin_b["content"]
