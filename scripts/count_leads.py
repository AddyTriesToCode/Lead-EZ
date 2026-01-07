#!/usr/bin/env python
"""Check database stats."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database import get_db_connection

with get_db_connection() as conn:
    cursor = conn.cursor()
    
    # Total leads
    cursor.execute("SELECT COUNT(*) FROM leads")
    total = cursor.fetchone()[0]
    
    # By status
    cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
    by_status = cursor.fetchall()
    
    print(f"Total leads: {total}")
    print("\nBy status:")
    for row in by_status:
        print(f"  {row[0]}: {row[1]}")
