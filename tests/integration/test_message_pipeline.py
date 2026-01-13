"""Integration tests for message generation pipeline."""
import pytest
import json
import tempfile
import os
from backend.services.lead_generator import LeadGenerator
from backend.services.enricher import Enricher
from backend.services.message_generator import MessageGenerator
from backend.models.lead import Lead
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


class TestMessageGenerationPipeline:
    """Integration tests for message generation pipeline."""
    
    def test_generate_messages_for_enriched_lead(self, temp_database):
        """Test generating messages for an enriched lead."""
        # Create enriched lead
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=1)
        
        enricher = Enricher(mode="offline")
        enriched_data = enricher.enrich_lead_offline(leads[0])
        enriched_lead = {**leads[0], **enriched_data}
        
        # Convert to Pydantic model
        lead_model = Lead(**enriched_lead)
        
        # Generate messages
        msg_generator = MessageGenerator()
        messages = msg_generator.generate_messages(lead_model)
        
        assert len(messages) == 4
        assert sum(1 for m in messages if m["channel"] == "email") == 2
        assert sum(1 for m in messages if m["channel"] == "linkedin") == 2
    
    def test_save_messages_to_database(self, temp_database):
        """Test saving generated messages to database."""
        # Generate and enrich lead
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=1)
        generator.save_to_database(leads)
        
        enricher = Enricher(mode="offline")
        enriched_data = enricher.enrich_lead_offline(leads[0])
        lead = {**leads[0], **enriched_data}
        
        # Generate messages
        lead_model = Lead(**lead)
        msg_generator = MessageGenerator()
        messages = msg_generator.generate_messages(lead_model)
        
        # Save messages to database
        import uuid
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for msg in messages:
                cursor.execute("""
                    INSERT INTO messages (
                        id, lead_id, channel, variant, content, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    lead["id"],
                    msg["channel"],
                    msg["variant"],
                    msg["content"],
                    "PENDING"
                ))
            conn.commit()
        
        # Verify in database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE lead_id = ?", (lead["id"],))
            db_messages = cursor.fetchall()
            
            assert len(db_messages) == 4
    
    def test_complete_pipeline_workflow(self, temp_database):
        """Test complete pipeline: generate -> enrich -> create messages -> save."""
        # Step 1: Generate leads
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=3)
        generator.save_to_database(leads)
        
        # Step 2: Enrich leads
        enricher = Enricher(mode="offline")
        enriched_leads = []
        for lead in leads:
            enriched_data = enricher.enrich_lead_offline(lead)
            enriched_leads.append({**lead, **enriched_data})
        
        # Update database with enrichment
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
        
        # Step 3: Generate messages for all enriched leads
        msg_generator = MessageGenerator()
        import uuid
        
        for lead in enriched_leads:
            lead_model = Lead(**lead)
            messages = msg_generator.generate_messages(lead_model)
            
            # Save messages
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for msg in messages:
                    cursor.execute("""
                        INSERT INTO messages (
                            id, lead_id, channel, variant, content, status
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        lead["id"],
                        msg["channel"],
                        msg["variant"],
                        msg["content"],
                        "PENDING"
                    ))
                conn.commit()
        
        # Step 4: Verify complete pipeline
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check leads
            cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'ENRICHED'")
            lead_count = cursor.fetchone()[0]
            assert lead_count == 3
            
            # Check messages (4 per lead)
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            assert message_count == 12
    
    def test_query_messages_by_channel(self, temp_database):
        """Test querying messages by channel."""
        # Setup: create lead and messages
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=1)
        generator.save_to_database(leads)
        
        enricher = Enricher(mode="offline")
        enriched_data = enricher.enrich_lead_offline(leads[0])
        lead = {**leads[0], **enriched_data}
        
        lead_model = Lead(**lead)
        msg_generator = MessageGenerator()
        messages = msg_generator.generate_messages(lead_model)
        
        # Save messages
        import uuid
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for msg in messages:
                cursor.execute("""
                    INSERT INTO messages (
                        id, lead_id, channel, variant, content, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    lead["id"],
                    msg["channel"],
                    msg["variant"],
                    msg["content"],
                    "PENDING"
                ))
            conn.commit()
        
        # Query email messages
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE channel = 'email'")
            email_messages = cursor.fetchall()
            assert len(email_messages) == 2
        
        # Query LinkedIn messages
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE channel = 'linkedin'")
            linkedin_messages = cursor.fetchall()
            assert len(linkedin_messages) == 2
    
    def test_query_messages_by_variant(self, temp_database):
        """Test querying messages by variant."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=1)
        generator.save_to_database(leads)
        
        enricher = Enricher(mode="offline")
        enriched_data = enricher.enrich_lead_offline(leads[0])
        lead = {**leads[0], **enriched_data}
        
        lead_model = Lead(**lead)
        msg_generator = MessageGenerator()
        messages = msg_generator.generate_messages(lead_model)
        
        # Save messages
        import uuid
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for msg in messages:
                cursor.execute("""
                    INSERT INTO messages (
                        id, lead_id, channel, variant, content, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    lead["id"],
                    msg["channel"],
                    msg["variant"],
                    msg["content"],
                    "PENDING"
                ))
            conn.commit()
        
        # Query variant A messages
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE variant = 'A'")
            variant_a = cursor.fetchall()
            assert len(variant_a) == 2
        
        # Query variant B messages
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE variant = 'B'")
            variant_b = cursor.fetchall()
            assert len(variant_b) == 2
    
    def test_update_message_status(self, temp_database):
        """Test updating message status."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=1)
        generator.save_to_database(leads)
        
        enricher = Enricher(mode="offline")
        enriched_data = enricher.enrich_lead_offline(leads[0])
        lead = {**leads[0], **enriched_data}
        
        lead_model = Lead(**lead)
        msg_generator = MessageGenerator()
        messages = msg_generator.generate_messages(lead_model)
        
        # Save messages
        import uuid
        message_ids = []
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for msg in messages:
                msg_id = str(uuid.uuid4())
                message_ids.append(msg_id)
                cursor.execute("""
                    INSERT INTO messages (
                        id, lead_id, channel, variant, content, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    msg_id,
                    lead["id"],
                    msg["channel"],
                    msg["variant"],
                    msg["content"],
                    "PENDING"
                ))
            conn.commit()
        
        # Update first message to SENT
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE messages SET status = 'SENT' WHERE id = ?",
                (message_ids[0],)
            )
            conn.commit()
        
        # Verify update
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM messages WHERE id = ?", (message_ids[0],))
            status = cursor.fetchone()["status"]
            assert status == "SENT"
            
            # Other messages should still be PENDING
            cursor.execute("SELECT COUNT(*) FROM messages WHERE status = 'PENDING'")
            pending_count = cursor.fetchone()[0]
            assert pending_count == 3
    
    def test_message_lead_relationship(self, temp_database):
        """Test the foreign key relationship between messages and leads."""
        generator = LeadGenerator(seed=42)
        leads = generator.generate_leads(count=2)
        generator.save_to_database(leads)
        
        enricher = Enricher(mode="offline")
        enriched_leads = []
        for lead in leads:
            enriched_data = enricher.enrich_lead_offline(lead)
            enriched_leads.append({**lead, **enriched_data})
        
        msg_generator = MessageGenerator()
        import uuid
        
        # Generate messages for both leads
        for lead in enriched_leads:
            lead_model = Lead(**lead)
            messages = msg_generator.generate_messages(lead_model)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for msg in messages:
                    cursor.execute("""
                        INSERT INTO messages (
                            id, lead_id, channel, variant, content, status
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        lead["id"],
                        msg["channel"],
                        msg["variant"],
                        msg["content"],
                        "PENDING"
                    ))
                conn.commit()
        
        # Verify each lead has 4 messages
        for lead in enriched_leads:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM messages WHERE lead_id = ?", (lead["id"],))
                count = cursor.fetchone()[0]
                assert count == 4
