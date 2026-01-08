#!/usr/bin/env python
"""Script to check pipeline status."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database import get_db_connection


def check_status():
    """Check current pipeline status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check leads
        print("\n" + "="*60)
        print("LEADS STATUS")
        print("="*60)
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM leads 
            GROUP BY status
        """)
        leads = cursor.fetchall()
        if leads:
            for lead in leads:
                print(f"  {lead['status']}: {lead['count']}")
        else:
            print("  No leads found")
        
        # Check messages
        print("\n" + "="*60)
        print("MESSAGES STATUS")
        print("="*60)
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM messages 
            GROUP BY status
        """)
        messages = cursor.fetchall()
        if messages:
            for msg in messages:
                print(f"  {msg['status']}: {msg['count']}")
        else:
            print("  No messages found")
        
        # Show lead details
        print("\n" + "="*60)
        print("LEAD DETAILS")
        print("="*60)
        cursor.execute("""
            SELECT full_name, email, status, company_size, 
                   pain_points, buying_triggers
            FROM leads
        """)
        lead = cursor.fetchone()
        if lead:
            print(f"  Name: {lead['full_name']}")
            print(f"  Email: {lead['email']}")
            print(f"  Status: {lead['status']}")
            print(f"  Company Size: {lead['company_size']}")
            print(f"  Pain Points: {lead['pain_points']}")
            print(f"  Buying Triggers: {lead['buying_triggers']}")
        
        print("\n" + "="*60)


if __name__ == "__main__":
    check_status()
