#!/usr/bin/env python
"""Script to generate leads using Faker and save to database."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.lead_generator import LeadGenerator
from backend.core.config import settings
from backend.core.logger import logger


def main():
    """Generate leads and save to database."""
    logger.info("=" * 50)
    logger.info("Lead Generation Script")
    logger.info(f"Using seed: {settings.random_seed}")
    logger.info("=" * 50)
    
    # Initialize generator
    generator = LeadGenerator(seed=settings.random_seed)
    
    # Generate and save leads
    result = generator.generate_and_save(count=settings.lead_count)
    
    logger.info("\n" + "=" * 50)
    logger.info("Summary:")
    logger.info(f"  Generated: {result['generated']} leads")
    logger.info(f"  Saved:     {result['saved']} leads")
    logger.info("=" * 50)
    
    # Show sample leads
    logger.info("\nSample leads:")
    for i, lead in enumerate(result['leads'][:5], 1):
        logger.info(f"\n{i}. {lead['full_name']}")
        logger.info(f"   Company:  {lead['company_name']}")
        logger.info(f"   Role:     {lead['role']}")
        logger.info(f"   Industry: {lead['industry']}")
        logger.info(f"   Email:    {lead['email']}")
        logger.info(f"   LinkedIn: {lead['linkedin_url']}")


if __name__ == "__main__":
    main()
