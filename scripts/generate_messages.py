"""Generate personalized messages for all enriched leads."""
import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import get_db_connection
from backend.models.lead import Lead
from backend.services.message_generator import MessageGenerator


def create_messages_table():
    """Create messages table if it doesn't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
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
        print("✓ Messages table ready")


def get_enriched_leads():
    """Fetch all enriched leads from database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, company_name, role, industry, website, email, 
                   linkedin_url, country, status, company_size, persona_tag, 
                   pain_points, buying_triggers, confidence_score, created_at, updated_at
            FROM leads
            WHERE status = 'ENRICHED'
            AND pain_points IS NOT NULL
            AND buying_triggers IS NOT NULL
        """)
        
        rows = cursor.fetchall()
        leads = []
        
        for row in rows:
            lead = Lead(
                id=row['id'],
                full_name=row['full_name'],
                company_name=row['company_name'],
                role=row['role'],
                industry=row['industry'],
                website=row['website'],
                email=row['email'],
                linkedin_url=row['linkedin_url'],
                country=row['country'],
                status=row['status'],
                company_size=row['company_size'],
                persona_tag=row['persona_tag'],
                pain_points=row['pain_points'],
                buying_triggers=row['buying_triggers'],
                confidence_score=row['confidence_score'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            leads.append(lead)
        
        return leads


def save_messages(lead_id: str, messages: list):
    """Save generated messages to database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if messages already exist for this lead
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE lead_id = ?", (lead_id,))
        existing_count = cursor.fetchone()['count']
        
        if existing_count > 0:
            return False  # Skip if messages already generated
        
        for msg in messages:
            message_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO messages (id, lead_id, channel, variant, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                lead_id,
                msg['channel'],
                msg['variant'],
                msg['content'],
                datetime.utcnow()
            ))
        
        return True


def main():
    """Generate messages for all enriched leads."""
    print("=" * 80)
    print("MESSAGE GENERATION")
    print("=" * 80)
    
    # Create table
    create_messages_table()
    
    # Get enriched leads
    print("\n📊 Fetching enriched leads...")
    leads = get_enriched_leads()
    print(f"Found {len(leads)} enriched leads")
    
    if not leads:
        print("\n⚠️  No enriched leads found. Run scripts/enrich_leads.py first.")
        return
    
    # Initialize generator
    generator = MessageGenerator()
    
    # Generate messages
    print("\n✍️  Generating personalized messages...")
    print("-" * 80)
    
    total_generated = 0
    skipped = 0
    
    for i, lead in enumerate(leads, 1):
        try:
            # Generate messages
            messages = generator.generate_messages(lead)
            
            # Save to database
            if save_messages(lead.id, messages):
                total_generated += 4  # 2 emails + 2 LinkedIn DMs
                
                # Show sample for first 3 leads
                if i <= 3:
                    print(f"\n{i}. {lead.full_name} ({lead.company_name})")
                    print(f"   Role: {lead.role} | Industry: {lead.industry}")
                    print(f"   Persona: {lead.persona_tag}")
                    
                    for msg in messages:
                        print(f"\n   [{msg['channel'].upper()} - Variant {msg['variant']}]")
                        preview = msg['content'][:150] + "..." if len(msg['content']) > 150 else msg['content']
                        print(f"   {preview}")
            else:
                skipped += 1
        
        except Exception as e:
            print(f"❌ Error generating messages for {lead.full_name}: {str(e)}")
    
    print("\n" + "=" * 80)
    print(f"✅ Message Generation Complete!")
    print(f"   Total messages generated: {total_generated}")
    print(f"   Leads processed: {len(leads) - skipped}")
    print(f"   Skipped (already have messages): {skipped}")
    print("=" * 80)
    
    # Show statistics
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE channel = 'email'")
        email_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE channel = 'linkedin'")
        linkedin_count = cursor.fetchone()['count']
        
        print(f"\n📧 Email messages: {email_count}")
        print(f"💼 LinkedIn messages: {linkedin_count}")


if __name__ == "__main__":
    main()
