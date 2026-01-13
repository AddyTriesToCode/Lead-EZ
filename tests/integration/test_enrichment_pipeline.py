"""Integration tests for lead enrichment pipeline."""
import pytest
import pytest_asyncio
import json
import tempfile
import os
import asyncio
from backend.services.lead_generator import LeadGenerator
from backend.services.enricher import Enricher
from backend.core.database import get_db_connection
from backend.core.config import settings


@pytest.fixture
def temp_database():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_leads.db")
    
    # Override database URL for testing
    original_db_url = settings.database_url
    settings.database_url = f"sqlite:///{db_path}"
    
    # Create tables
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                company_name TEXT NOT NULL,
                role TEXT NOT NULL,
                industry TEXT NOT NULL,
                website TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                linkedin_url TEXT NOT NULL,
                country TEXT NOT NULL,
                status TEXT DEFAULT 'NEW',
                company_size TEXT,
                persona_tag TEXT,
                pain_points TEXT,
                buying_triggers TEXT,
                confidence_score INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    
    yield db_path
    
    # Cleanup
    settings.database_url = original_db_url
    os.remove(db_path)
    os.rmdir(temp_dir)


class TestEnrichmentPipeline:
    """Integration tests for lead enrichment."""
    
    def test_enrich_single_lead(self, temp_database):
        """Test enriching a single lead."""
        # Generate and save lead
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=1)
        generator.save_to_database(leads)
        
        # Enrich the lead using offline method
        enricher = Enricher(mode="offline")
        lead_dict = leads[0]
        enriched_data = enricher.enrich_lead_offline(lead_dict)
        
        # Verify enrichment fields
        assert enriched_data["company_size"] in ["small", "medium", "enterprise"]
        assert enriched_data["persona_tag"] is not None
        assert enriched_data["pain_points"] is not None
        assert enriched_data["buying_triggers"] is not None
        assert enriched_data["confidence_score"] >= 0
        assert enriched_data["confidence_score"] <= 100
    
    def test_enrich_multiple_leads(self, temp_database):
        """Test enriching multiple leads."""
        # Generate and save leads
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=10)
        generator.save_to_database(leads)
        
        # Enrich all leads using offline method
        enricher = Enricher(mode="offline")
        enriched_leads = []
        for lead in leads:
            enriched_data = enricher.enrich_lead_offline(lead)
            enriched_leads.append({**lead, **enriched_data})
        
        assert len(enriched_leads) == 10
        
        # Verify all leads are enriched
        for lead in enriched_leads:
            assert lead["company_size"] is not None
            assert lead["persona_tag"] is not None
            assert lead["confidence_score"] is not None
    
    def test_enrichment_preserves_original_data(self, temp_database):
        """Test that enrichment doesn't modify original lead data."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=1)
        original_lead = leads[0].copy()
        generator.save_to_database(leads)
        
        # Enrich
        enricher = Enricher(mode="offline")
        enriched_data = enricher.enrich_lead_offline(leads[0])
        enriched = {**leads[0], **enriched_data}
        
        # Verify original fields are unchanged
        assert enriched["id"] == original_lead["id"]
        assert enriched["full_name"] == original_lead["full_name"]
        assert enriched["company_name"] == original_lead["company_name"]
        assert enriched["email"] == original_lead["email"]
        assert enriched["role"] == original_lead["role"]
    
    def test_save_enriched_leads_to_database(self, temp_database):
        """Test saving enriched leads to database."""
        # Generate and save leads
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=5)
        generator.save_to_database(leads)
        
        # Enrich leads
        enricher = Enricher(mode="offline")
        enriched_leads = []
        for lead in leads:
            enriched_data = enricher.enrich_lead_offline(lead)
            enriched_leads.append({**lead, **enriched_data})
        
        # Save enrichment data to database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for lead in enriched_leads:
                cursor.execute("""
                    UPDATE leads SET
                        company_size = ?,
                        persona_tag = ?,
                        pain_points = ?,
                        buying_triggers = ?,
                        confidence_score = ?,
                        status = 'ENRICHED'
                    WHERE id = ?
                """, (
                    lead["company_size"],
                    lead["persona_tag"],
                    lead["pain_points"],
                    lead["buying_triggers"],
                    lead["confidence_score"],
                    lead["id"]
                ))
            conn.commit()
        
        # Verify enrichment in database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE status = 'ENRICHED'")
            db_leads = cursor.fetchall()
            
            assert len(db_leads) == 5
            for db_lead in db_leads:
                assert db_lead["company_size"] is not None
                assert db_lead["persona_tag"] is not None
                assert db_lead["confidence_score"] is not None
    
    def test_enrichment_json_fields(self, temp_database):
        """Test that pain_points and triggers are valid JSON."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=3)
        
        enricher = Enricher(mode="offline")
        for lead in leads:
            enriched_data = enricher.enrich_lead_offline(lead)
            
            # Verify JSON fields can be parsed
            pain_points = json.loads(enriched_data["pain_points"])
            triggers = json.loads(enriched_data["buying_triggers"])
            
            assert isinstance(pain_points, list)
            assert isinstance(triggers, list)
            assert len(pain_points) > 0
            assert len(triggers) > 0
    
    def test_persona_tag_matches_role(self, temp_database):
        """Test that persona tags are generated for roles."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=20)
        
        enricher = Enricher(mode="offline")
        for lead in leads:
            enriched_data = enricher.enrich_lead_offline(lead)
            # Persona tag should be a non-empty string
            assert enriched_data["persona_tag"] is not None
            assert len(enriched_data["persona_tag"]) > 0
    
    def test_confidence_score_calculation(self, temp_database):
        """Test that confidence scores are calculated reasonably."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=10)
        
        enricher = Enricher(mode="offline")
        scores = []
        for lead in leads:
            enriched_data = enricher.enrich_lead_offline(lead)
            scores.append(enriched_data["confidence_score"])
        
        # All scores should be within valid range
        assert all(0 <= score <= 100 for score in scores)
        
        # There should be some variation in scores
        assert len(set(scores)) > 1
    
    def test_complete_enrichment_workflow(self, temp_database):
        """Test complete workflow: generate -> save -> enrich -> update."""
        # Step 1: Generate leads
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=10)
        
        # Step 2: Save to database
        saved = generator.save_to_database(leads)
        assert saved == 10
        
        # Step 3: Enrich leads
        enricher = Enricher(mode="offline")
        enriched_leads = []
        for lead in leads:
            enriched_data = enricher.enrich_lead_offline(lead)
            enriched_leads.append({**lead, **enriched_data})
        
        # Step 4: Update database with enrichment
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for lead in enriched_leads:
                cursor.execute("""
                    UPDATE leads SET
                        company_size = ?,
                        persona_tag = ?,
                        pain_points = ?,
                        buying_triggers = ?,
                        confidence_score = ?,
                        status = 'ENRICHED'
                    WHERE id = ?
                """, (
                    lead["company_size"],
                    lead["persona_tag"],
                    lead["pain_points"],
                    lead["buying_triggers"],
                    lead["confidence_score"],
                    lead["id"]
                ))
            conn.commit()
        
        # Step 5: Verify complete workflow
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM leads 
                WHERE status = 'ENRICHED' 
                AND company_size IS NOT NULL
                AND confidence_score IS NOT NULL
            """)
            count = cursor.fetchone()[0]
            assert count == 10
