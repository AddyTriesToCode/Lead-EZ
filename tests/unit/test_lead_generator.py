"""Unit tests for LeadGenerator service."""
import pytest
from backend.services.lead_generator import LeadGenerator


class TestLeadGenerator:
    """Test cases for LeadGenerator."""
    
    def test_initialization_with_seed(self):
        """Test that generator initializes with a seed."""
        generator = LeadGenerator(seed=42)
        assert generator.fake is not None
    
    def test_generate_valid_email(self):
        """Test email generation format."""
        generator = LeadGenerator(seed=42)
        email = generator._generate_valid_email("John Doe", "Acme Corp")
        
        assert "@" in email
        assert email.startswith("john.doe@")
        assert email.endswith(".com")
        assert " " not in email
    
    def test_generate_linkedin_url(self):
        """Test LinkedIn URL generation format."""
        generator = LeadGenerator(seed=42)
        url = generator._generate_linkedin_url("Jane Smith")
        
        assert url.startswith("https://www.linkedin.com/in/")
        assert "jane-smith" in url
        assert "-" in url.split("/")[-1]
    
    def test_generate_website(self):
        """Test website URL generation format."""
        generator = LeadGenerator(seed=42)
        website = generator._generate_website("Tech Innovations Inc")
        
        assert website.startswith("https://www.")
        assert website.endswith(".com")
        assert " " not in website
    
    def test_generate_single_lead(self):
        """Test generating a single lead with all required fields."""
        generator = LeadGenerator(seed=42)
        lead = generator.generate_lead()
        
        # Check all required fields exist
        required_fields = [
            "id", "full_name", "company_name", "role", "industry",
            "website", "email", "linkedin_url", "country", "status"
        ]
        for field in required_fields:
            assert field in lead
            assert lead[field] is not None
            assert lead[field] != ""
        
        # Validate data types
        assert isinstance(lead["id"], str)
        assert isinstance(lead["full_name"], str)
        assert lead["status"] == "NEW"
    
    def test_generate_multiple_leads(self):
        """Test generating multiple leads."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=10)
        
        assert len(leads) == 10
        
        # Check all leads have unique IDs
        ids = [lead["id"] for lead in leads]
        assert len(ids) == len(set(ids))
    
    def test_industry_role_matching(self):
        """Test that generated roles match their industries."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=50)
        
        for lead in leads:
            industry = lead["industry"]
            role = lead["role"]
            
            # Verify role is valid for the industry
            assert industry in generator.INDUSTRY_ROLES
            assert role in generator.INDUSTRY_ROLES[industry]
    
    def test_deterministic_generation(self):
        """Test that same seed produces same sequence of leads."""
        gen1 = LeadGenerator(seed=123)
        leads1 = gen1.generate_leads(count=5)
        
        gen2 = LeadGenerator(seed=123)
        leads2 = gen2.generate_leads(count=5)
        
        # With same seed, the sequence should match (excluding UUIDs)
        for i in range(5):
            # IDs will be different (UUID), but other fields should match
            assert leads1[i]["full_name"] == leads2[i]["full_name"]
            assert leads1[i]["company_name"] == leads2[i]["company_name"]
            assert leads1[i]["role"] == leads2[i]["role"]
            assert leads1[i]["industry"] == leads2[i]["industry"]
    
    def test_country_values(self):
        """Test that generated countries are from the predefined list."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=20)
        
        for lead in leads:
            assert lead["country"] in generator.COUNTRIES
