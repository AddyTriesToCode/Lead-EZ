"""Export generated messages to CSV for review."""
import sys
from pathlib import Path
import csv
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import get_db_connection


def export_messages_to_csv(output_file=None):
    """Export all messages to CSV file."""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"storage/messages/generated_messages_{timestamp}.csv"
    
    # Ensure directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get all messages with lead data
        cursor.execute("""
            SELECT 
                l.full_name,
                l.company_name,
                l.role,
                l.industry,
                l.email,
                l.linkedin_url,
                l.persona_tag,
                m.channel,
                m.variant,
                m.content,
                m.created_at
            FROM messages m
            INNER JOIN leads l ON m.lead_id = l.id
            ORDER BY l.full_name, m.channel, m.variant
        """)
        
        messages = cursor.fetchall()
        
        if not messages:
            print("No messages found to export.")
            return
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Lead Name',
                'Company',
                'Role',
                'Industry',
                'Email',
                'LinkedIn URL',
                'Persona',
                'Channel',
                'Variant',
                'Message Content',
                'Word Count',
                'Generated At'
            ])
            
            # Data rows
            for msg in messages:
                word_count = len(msg['content'].split())
                writer.writerow([
                    msg['full_name'],
                    msg['company_name'],
                    msg['role'],
                    msg['industry'],
                    msg['email'],
                    msg['linkedin_url'],
                    msg['persona_tag'],
                    msg['channel'].upper(),
                    msg['variant'],
                    msg['content'],
                    word_count,
                    msg['created_at']
                ])
        
        print("=" * 80)
        print("MESSAGE EXPORT COMPLETE")
        print("=" * 80)
        print(f"\n✅ Exported {len(messages)} messages")
        print(f"📁 File: {output_file}")
        print(f"📊 Size: {Path(output_file).stat().st_size / 1024:.2f} KB")
        print("\n" + "=" * 80)
        
        return output_file


if __name__ == "__main__":
    export_messages_to_csv()
