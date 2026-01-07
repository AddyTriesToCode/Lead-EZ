import uuid
import json
from typing import List, Dict
from faker import Faker
from ..core.logger import logger
from ..core.database import get_db_connection


class LeadGenerator:
    """Generates realistic, valid leads using Faker with industry-role matching."""
    
    # Industry → Role mappings
    INDUSTRY_ROLES = {
        "Technology": ["CTO", "VP Engineering", "Head of IT", "Data Leader", "DevOps Manager"],
        "Healthcare": ["Chief Medical Officer", "Hospital Administrator", "Director of Operations", "VP Patient Care"],
        "Finance": ["CFO", "VP Finance", "Treasury Director", "Risk Management Head", "Compliance Officer"],
        "Manufacturing": ["VP Operations", "Supply Chain Director", "Production Manager", "Procurement Head"],
        "Retail": ["VP Merchandising", "Store Operations Director", "Head of E-commerce", "Inventory Manager"],
        "Education": ["Dean", "VP Academic Affairs", "Director of IT", "Enrollment Director"],
        "Real Estate": ["VP Property Management", "Development Director", "Asset Manager", "Leasing Director"],
        "Logistics": ["VP Supply Chain", "Logistics Manager", "Warehouse Director", "Transportation Head"],
        "Marketing": ["CMO", "VP Marketing", "Head of Digital", "Brand Director", "Marketing Operations Manager"],
        "Construction": ["Project Manager", "VP Construction", "Site Director", "Estimating Director"],
    }
    
    COUNTRIES = ["India", "USA", "UK", "Germany", "France", "Australia", "Netherlands", "Singapore"]
    
    def __init__(self, seed: int = 42):
        """Initialize generator with random seed for reproducibility."""
        Faker.seed(seed)
        self.fake = Faker()
        
    def _generate_valid_email(self, name: str, company: str) -> str:
        """Generate syntactically valid email."""
        first = name.split()[0].lower()
        last = name.split()[-1].lower()
        domain = company.lower().replace(" ", "").replace(",", "")[:15]
        return f"{first}.{last}@{domain}.com"
    
    def _generate_linkedin_url(self, name: str) -> str:
        """Generate syntactically valid LinkedIn URL."""
        username = name.lower().replace(" ", "-")
        return f"https://www.linkedin.com/in/{username}-{self.fake.random_int(100, 999)}"
    
    def _generate_website(self, company: str) -> str:
        """Generate syntactically valid company website."""
        domain = company.lower().replace(" ", "").replace(",", "")[:20]
        return f"https://www.{domain}.com"
    
    def generate_lead(self) -> Dict:
        """Generate a single realistic lead."""
        # Pick industry and matching role
        industry = self.fake.random_element(list(self.INDUSTRY_ROLES.keys()))
        role = self.fake.random_element(self.INDUSTRY_ROLES[industry])
        
        # Generate personal info
        full_name = self.fake.name()
        company_name = self.fake.company()
        country = self.fake.random_element(self.COUNTRIES)
        
        # Generate valid contact info
        email = self._generate_valid_email(full_name, company_name)
        linkedin_url = self._generate_linkedin_url(full_name)
        website = self._generate_website(company_name)
        
        return {
            "id": str(uuid.uuid4()),
            "full_name": full_name,
            "company_name": company_name,
            "role": role,
            "industry": industry,
            "website": website,
            "email": email,
            "linkedin_url": linkedin_url,
            "country": country,
            "status": "NEW",
        }
    
    def generate_leads(self, count: int = 200) -> List[Dict]:
        """Generate multiple leads."""
        logger.info(f"Generating {count} leads...")
        leads = []
        
        for i in range(count):
            try:
                lead = self.generate_lead()
                leads.append(lead)
                
                if (i + 1) % 50 == 0:
                    logger.info(f"Generated {i + 1}/{count} leads")
                    
            except Exception as e:
                logger.error(f"Error generating lead {i + 1}: {e}")
                
        logger.info(f"Successfully generated {len(leads)} leads")
        return leads
    
    def save_to_database(self, leads: List[Dict]) -> int:
        """Save leads to SQLite database."""
        logger.info(f"Saving {len(leads)} leads to database...")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            saved = 0
            
            for lead in leads:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO leads (
                            id, full_name, company_name, role, industry,
                            website, email, linkedin_url, country, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        lead["id"],
                        lead["full_name"],
                        lead["company_name"],
                        lead["role"],
                        lead["industry"],
                        lead["website"],
                        lead["email"],
                        lead["linkedin_url"],
                        lead["country"],
                        lead["status"],
                    ))
                    saved += 1
                except Exception as e:
                    logger.error(f"Error saving lead {lead['email']}: {e}")
            
            conn.commit()
            logger.info(f"Saved {saved}/{len(leads)} leads to database")
            return saved
    
    def generate_and_save(self, count: int = 200) -> Dict:
        """Generate leads and save to database."""
        leads = self.generate_leads(count)
        saved = self.save_to_database(leads)
        
        return {
            "generated": len(leads),
            "saved": saved,
            "leads": leads
        }
