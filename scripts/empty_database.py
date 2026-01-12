#!/usr/bin/env python
"""Script to empty leads and messages tables from the database."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database import get_db_connection
from backend.core.logger import logger


def empty_database():
    """Empty leads and messages tables."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get counts before deletion
            cursor.execute("SELECT COUNT(*) FROM messages")
            messages_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM leads")
            leads_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM history")
            history_count=cursor.fetchone()[0]
            
            print("\n" + "="*60)
            print("DATABASE CLEANUP")
            print("="*60)
            print(f"Current counts:")
            print(f"  Messages: {messages_count}")
            print(f"  Leads: {leads_count}")
            print(f"  History: {history_count}")
            print()
            
            # Confirm deletion
            if messages_count > 0 or leads_count > 0:
                response = input("Are you sure you want to delete all data? (yes/no): ")
                if response.lower() != "yes":
                    print("Aborted.")
                    return
            
            # Delete messages first (foreign key constraint)
            cursor.execute("DELETE FROM messages")
            deleted_messages = cursor.rowcount
            
            # Delete leads
            cursor.execute("DELETE FROM leads")
            deleted_leads = cursor.rowcount

            cursor.execute("DELETE FROM history")
            deleted_history = cursor.rowcount

        
            
            conn.commit()
            
            print()
            print("Deletion complete:")
            print(f"  ✅ Deleted {deleted_messages} messages")
            print(f"  ✅ Deleted {deleted_leads} leads")
            print(f"  ✅ Deleted {deleted_history} messages from hisrtory")
            print("="*60)
            
            logger.info(f"Database emptied: {deleted_leads} leads, {deleted_messages} messages deleted, {deleted_history} messages deleted from history" )
            
    except Exception as e:
        logger.error(f"Error emptying database: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    empty_database()
