#!/usr/bin/env python
"""Script to enrich leads with company size, personas, pain points, and triggers."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.enricher import Enricher
from backend.core.logger import logger


def main():
    """Enrich leads."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich leads")
    parser.add_argument("-m", "--mode", choices=["offline", "ai"], default="offline",
                        help="Enrichment mode: offline (rule-based) or ai (LLM)")
    parser.add_argument("-n", "--limit", type=int, default=None,
                        help="Maximum number of leads to enrich")
    
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("Lead Enrichment Script")
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info("=" * 50)
    
    # Initialize enricher
    enricher = Enricher(mode=args.mode)
    
    # Enrich leads
    result = enricher.enrich_leads(limit=args.limit)
    
    logger.info("\n" + "=" * 50)
    logger.info("Enrichment Summary:")
    logger.info(f"  Enriched: {result['enriched']} leads")
    logger.info(f"  Failed:   {result['failed']} leads")
    logger.info("=" * 50)
    
    # Show sample enriched leads
    if result['leads']:
        logger.info("\nSample enriched leads:")
        for i, lead in enumerate(result['leads'][:5], 1):
            logger.info(f"\n{i}. {lead['name']} - {lead['company']}")
            logger.info(f"   Company Size: {lead['company_size']}")
            logger.info(f"   Persona:      {lead['persona_tag']}")
            logger.info(f"   Confidence:   {lead['confidence_score']}/100")


if __name__ == "__main__":
    main()
