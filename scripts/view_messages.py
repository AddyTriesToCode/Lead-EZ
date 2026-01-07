"""View generated messages for a specific lead."""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import get_db_connection


def view_messages(limit=5):
    """View messages for the first N leads."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get leads with messages
        cursor.execute("""
            SELECT DISTINCT l.id, l.full_name, l.company_name, l.role, 
                   l.industry, l.persona_tag, l.pain_points, l.buying_triggers
            FROM leads l
            INNER JOIN messages m ON l.id = m.lead_id
            LIMIT ?
        """, (limit,))
        
        leads = cursor.fetchall()
        
        if not leads:
            print("No messages found in database.")
            return
        
        print("=" * 100)
        print("GENERATED MESSAGES")
        print("=" * 100)
        
        for i, lead in enumerate(leads, 1):
            print(f"\n{'='*100}")
            print(f"LEAD #{i}: {lead['full_name']} - {lead['role']} at {lead['company_name']}")
            print(f"Industry: {lead['industry']} | Persona: {lead['persona_tag']}")
            print(f"{'='*100}")
            
            # Get messages for this lead
            cursor.execute("""
                SELECT channel, variant, content, created_at
                FROM messages
                WHERE lead_id = ?
                ORDER BY channel, variant
            """, (lead['id'],))
            
            messages = cursor.fetchall()
            
            for msg in messages:
                print(f"\n{'-'*100}")
                print(f"[{msg['channel'].upper()} - Variant {msg['variant']}]")
                print(f"{'-'*100}")
                print(msg['content'])
                print(f"\n📊 Word count: {len(msg['content'].split())} words")
        
        print(f"\n{'='*100}")
        
        # Statistics
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        total = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(DISTINCT lead_id) as count FROM messages")
        unique_leads = cursor.fetchone()['count']
        
        print(f"\n📈 STATISTICS")
        print(f"   Total messages: {total}")
        print(f"   Unique leads: {unique_leads}")
        print(f"   Messages per lead: {total // unique_leads if unique_leads > 0 else 0}")
        print("=" * 100)


if __name__ == "__main__":
    # Change this number to view more or fewer leads
    view_messages(limit=3)
