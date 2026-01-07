"""Test script to verify confidence score filtering for message generation."""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database import get_db_connection
from backend.core.logger import logger


def check_confidence_filtering():
    """Check leads by confidence score and message generation eligibility."""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get distribution of leads by confidence score and status
        cursor.execute("""
            SELECT 
                status,
                CASE 
                    WHEN confidence_score >= 75 THEN 'eligible'
                    WHEN confidence_score < 75 THEN 'below_threshold'
                    ELSE 'no_score'
                END as eligibility,
                COUNT(*) as count,
                AVG(confidence_score) as avg_score,
                MIN(confidence_score) as min_score,
                MAX(confidence_score) as max_score
            FROM leads
            GROUP BY status, eligibility
            ORDER BY status, eligibility
        """)
        
        results = cursor.fetchall()
        
        print("\n" + "="*80)
        print("CONFIDENCE SCORE DISTRIBUTION BY STATUS")
        print("="*80)
        print(f"{'Status':<15} {'Eligibility':<20} {'Count':<10} {'Avg':<10} {'Min':<10} {'Max':<10}")
        print("-"*80)
        
        for row in results:
            print(f"{row['status']:<15} {row['eligibility']:<20} {row['count']:<10} "
                  f"{row['avg_score']:<10.1f} {row['min_score']:<10} {row['max_score']:<10}")
                  
        
        # Check ENRICHED leads specifically
        cursor.execute("""
            SELECT COUNT(*) as total FROM leads WHERE status = 'ENRICHED'
        """)
        total_enriched = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT COUNT(*) as eligible FROM leads 
            WHERE status = 'ENRICHED' AND confidence_score >= 75
        """)
        eligible = cursor.fetchone()['eligible']
        
        cursor.execute("""
            SELECT COUNT(*) as below FROM leads 
            WHERE status = 'ENRICHED' AND confidence_score < 75
        """)
        below_threshold = cursor.fetchone()['below']
        
        print("\n" + "="*80)
        print("ENRICHED LEADS - MESSAGE GENERATION ELIGIBILITY")
        print("="*80)
        print(f"Total ENRICHED leads:               {total_enriched}")
        print(f"Eligible (confidence >= 75):        {eligible} ({eligible/total_enriched*100 if total_enriched > 0 else 0:.1f}%)")
        print(f"Below threshold (confidence < 75):  {below_threshold} ({below_threshold/total_enriched*100 if total_enriched > 0 else 0:.1f}%)")
        print("="*80)
        
        # Show sample leads below threshold
        if below_threshold > 0:
            cursor.execute("""
                SELECT full_name, company_name, role, confidence_score, status
                FROM leads 
                WHERE status = 'ENRICHED' AND confidence_score < 75
                ORDER BY confidence_score ASC
                LIMIT 10
            """)
            
            low_confidence_leads = cursor.fetchall()
            
            print("\n" + "="*80)
            print("SAMPLE LEADS BELOW THRESHOLD (would be skipped)")
            print("="*80)
            for lead in low_confidence_leads:
                print(f"{lead['full_name']:<25} | {lead['company_name']:<20} | "
                      f"{lead['role']:<20} | Score: {lead['confidence_score']}")
            print("="*80)
        
        # Show sample leads above threshold
        if eligible > 0:
            cursor.execute("""
                SELECT full_name, company_name, role, confidence_score, status
                FROM leads 
                WHERE status = 'ENRICHED' AND confidence_score >= 75
                ORDER BY confidence_score DESC
                LIMIT 10
            """)
            
            high_confidence_leads = cursor.fetchall()
            
            print("\n" + "="*80)
            print("SAMPLE LEADS ABOVE THRESHOLD (eligible for messages)")
            print("="*80)
            for lead in high_confidence_leads:
                print(f"{lead['full_name']:<25} | {lead['company_name']:<20} | "
                      f"{lead['role']:<20} | Score: {lead['confidence_score']}")
            print("="*80)
        
        print(f"\n✅ Only leads with confidence >= 75 will get messages generated")
        print(f"💡 To change threshold: Set MIN_CONFIDENCE_SCORE env var or modify config.py\n")


if __name__ == "__main__":
    check_confidence_filtering()
