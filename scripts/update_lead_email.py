#!/usr/bin/env python
"""Script to update a lead's email address."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database import get_db_connection


def update_email(lead_name: str, new_email: str):
    """Update the email of a specific lead."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Update email
        cursor.execute("""
            UPDATE leads 
            SET email = ?
            WHERE full_name = ?
        """, (new_email, lead_name))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ Updated email for '{lead_name}' to '{new_email}'")
        else:
            print(f"❌ No lead found with name '{lead_name}'")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update a lead's email")
    parser.add_argument("name", help="Full name of the lead")
    parser.add_argument("email", help="New email address")
    
    args = parser.parse_args()
    
    update_email(args.name, args.email)
