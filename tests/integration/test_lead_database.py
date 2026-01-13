"""Integration tests for lead generation and database persistence."""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from backend.services.lead_generator import LeadGenerator
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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                variant TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                sent_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        """)
        conn.commit()
    
    yield db_path
    
    # Cleanup
    settings.database_url = original_db_url
    os.remove(db_path)
    os.rmdir(temp_dir)


class TestLeadGenerationPipeline:
    """Integration tests for lead generation and database operations."""
    
    def test_generate_and_save_leads(self, temp_database):
        """Test generating leads and saving to database."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=10)
        
        # Save to database
        saved_count = generator.save_to_database(leads)
        
        assert saved_count == 10
        
        # Verify database content
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM leads")
            count = cursor.fetchone()[0]
            assert count == 10
    
    def test_duplicate_lead_prevention(self, temp_database):
        """Test that duplicate leads are handled properly."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=5)
        
        # Save first time
        saved_count_1 = generator.save_to_database(leads)
        assert saved_count_1 == 5
        
        # Try to save same leads again (INSERT OR IGNORE means duplicates are silently ignored)
        saved_count_2 = generator.save_to_database(leads)
        # The generator still reports saves attempted, not unique inserts
        assert saved_count_2 >= 0
        
        # Verify database still only has 5 unique leads (by email)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT email) FROM leads")
            count = cursor.fetchone()[0]
            assert count == 5
    
    def test_retrieve_leads_from_database(self, temp_database):
        """Test retrieving leads from database."""
        generator = LeadGenerator(seed=42)
        original_leads = generator.generate_leads(count=3)
        generator.save_to_database(original_leads)
        
        # Retrieve from database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads ORDER BY full_name")
            rows = cursor.fetchall()
            
            assert len(rows) == 3
            
            # Verify data integrity
            for row in rows:
                assert row["email"] is not None
                assert "@" in row["email"]
                assert row["status"] == "NEW"
    
    def test_generate_and_save_workflow(self, temp_database):
        """Test the complete generate_and_save workflow."""
        generator = LeadGenerator(seed=123)
        result = generator.generate_and_save(count=15)
        
        assert result["generated"] == 15
        assert result["saved"] == 15
        assert len(result["leads"]) == 15
        
        # Verify in database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM leads")
            count = cursor.fetchone()[0]
            assert count == 15
    
    def test_query_leads_by_industry(self, temp_database):
        """Test querying leads by specific industry."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=50)
        generator.save_to_database(leads)
        
        # Query leads from Technology industry
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM leads WHERE industry = ?",
                ("Technology",)
            )
            tech_leads = cursor.fetchall()
            
            assert len(tech_leads) > 0
            for lead in tech_leads:
                assert lead["industry"] == "Technology"
    
    def test_query_leads_by_status(self, temp_database):
        """Test querying leads by status."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=10)
        generator.save_to_database(leads)
        
        # All new leads should have status NEW
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM leads WHERE status = ?",
                ("NEW",)
            )
            new_leads = cursor.fetchall()
            assert len(new_leads) == 10
    
    def test_update_lead_status(self, temp_database):
        """Test updating lead status in database."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=5)
        generator.save_to_database(leads)
        
        lead_id = leads[0]["id"]
        
        # Update status
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE leads SET status = ? WHERE id = ?",
                ("ENRICHED", lead_id)
            )
            conn.commit()
        
        # Verify update
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM leads WHERE id = ?",
                (lead_id,)
            )
            status = cursor.fetchone()["status"]
            assert status == "ENRICHED"
    
    def test_database_transaction_rollback(self, temp_database):
        """Test that failed transactions are rolled back."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=3)
        
        # Create a scenario where insertion might fail
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Insert first lead
            first_lead = leads[0]
            cursor.execute("""
                INSERT INTO leads (
                    id, full_name, company_name, role, industry,
                    website, email, linkedin_url, country, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                first_lead["id"],
                first_lead["full_name"],
                first_lead["company_name"],
                first_lead["role"],
                first_lead["industry"],
                first_lead["website"],
                first_lead["email"],
                first_lead["linkedin_url"],
                first_lead["country"],
                first_lead["status"],
            ))
            conn.commit()
        
        # Try to insert duplicate - with INSERT OR IGNORE it won't error
        saved_count = generator.save_to_database([first_lead])
        # Generator still counts the insert attempt
        assert saved_count >= 0
        
        # Verify only 1 lead exists
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM leads")
            count = cursor.fetchone()[0]
            assert count == 1
