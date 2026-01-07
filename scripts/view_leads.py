#!/usr/bin/env python
"""Script to view leads from the database."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database import get_db_connection


def view_leads(limit: int = 20):
    """View leads from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        
        # Get leads
        cursor.execute("""
            SELECT id, full_name, company_name, role, industry, 
                   email, country, status
            FROM leads
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        leads = cursor.fetchall()
        
        print(f"\n{'='*80}")
        print(f"Total Leads in Database: {total}")
        print(f"Showing first {len(leads)} leads:")
        print(f"{'='*80}\n")
        
        for i, lead in enumerate(leads, 1):
            print(f"{i}. {lead['full_name']}")
            print(f"   Company:  {lead['company_name']}")
            print(f"   Role:     {lead['role']}")
            print(f"   Industry: {lead['industry']}")
            print(f"   Email:    {lead['email']}")
            print(f"   Country:  {lead['country']}")
            print(f"   Status:   {lead['status']}")
            print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="View leads from database")
    parser.add_argument("-n", "--limit", type=int, default=20, help="Number of leads to show")
    
    args = parser.parse_args()
    view_leads(args.limit)
