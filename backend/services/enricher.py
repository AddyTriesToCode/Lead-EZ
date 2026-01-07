import json
import random
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import httpx
from ..core.logger import logger
from ..core.database import get_db_connection


class Enricher:
    """Enriches leads with company size, personas, pain points, and buying triggers.
    
    Supports two modes:
    1. Offline mode (heuristics and rule-based logic)
    2. AI mode (using local LLM via Ollama - optional)
    """
    
    def __init__(self, mode: str = "offline"):
        """Initialize enricher.
        
        Args:
            mode: "offline" (rule-based) or "ai" (LLM-powered)
        """
        self.mode = mode
        self.data_dir = Path(__file__).parent.parent / "data"
        
        # Load rule data
        self.personas = self._load_json("personas.json")
        self.pain_points = self._load_json("pain_points.json")
        self.triggers = self._load_json("triggers.json")
        
        logger.info(f"Enricher initialized in {mode} mode")
    
    def _load_json(self, filename: str) -> dict:
        """Load JSON data file."""
        file_path = self.data_dir / filename
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _estimate_company_size(self, company_name: str, country: str) -> str:
        """Estimate company size based on heuristics.
        
        RULE-BASED LOGIC:
        - Company name has "Inc", "LLC", "Ltd" → likely small-medium
        - Company name has "PLC", "Corp", "Group" → likely medium-enterprise
        - USA, Germany companies → more likely enterprise
        - Random factor for realism
        """
        name_lower = company_name.lower()
        
        # Heuristic scoring
        score = 50  # Start at medium
        
        if any(x in name_lower for x in ["plc", "corp", "group", "global", "international"]):
            score += 30
        
        if any(x in name_lower for x in ["llc", "ltd", "inc"]):
            score -= 20
        
        if country in ["USA", "Germany", "UK"]:
            score += 15
        
        if country in ["India", "Singapore"]:
            score -= 10
        
        # Add randomness
        score += random.randint(-15, 15)
        
        # Convert score to size
        if score < 40:
            return "small"
        elif score < 70:
            return "medium"
        else:
            return "enterprise"
    
    def _get_persona_tag(self, role: str, industry: str) -> str:
        """Get persona tag from role and industry mapping.
        
        RULE-BASED: Uses personas.json mappings
        """
        industry_roles = self.personas.get(industry, {})
        role_data = industry_roles.get(role, {})
        return role_data.get("persona", f"{role} Professional")
    
    def _get_seniority(self, role: str, industry: str) -> str:
        """Get seniority level from role.
        
        RULE-BASED: Uses personas.json mappings
        """
        industry_roles = self.personas.get(industry, {})
        role_data = industry_roles.get(role, {})
        return role_data.get("seniority", "Manager")
    
    def _select_pain_points(self, industry: str) -> List[str]:
        """Select 2-3 relevant pain points.
        
        RULE-BASED: Randomly selects from industry-specific pain points
        """
        all_points = self.pain_points.get(industry, [
            "Operational efficiency and cost optimization",
            "Digital transformation and technology adoption",
            "Competitive market pressures"
        ])
        
        # Select 2-3 pain points
        count = random.randint(2, 3)
        return random.sample(all_points, min(count, len(all_points)))
    
    def _select_buying_triggers(self, industry: str) -> List[str]:
        """Select 1-2 buying triggers.
        
        RULE-BASED: Randomly selects from industry-specific triggers
        """
        all_triggers = self.triggers.get(industry, [
            "Budget planning cycle approaching",
            "Competitive pressure increasing"
        ])
        
        # Select 1-2 triggers
        count = random.randint(1, 2)
        return random.sample(all_triggers, min(count, len(all_triggers)))
    
    def _calculate_confidence_score(self, company_size: str, seniority: str) -> int:
        """Calculate confidence score based on enrichment data.
        
        RULE-BASED SCORING:
        - Enterprise + C-level/VP: 80-95
        - Medium + Director/VP: 65-80
        - Small + Manager: 50-65
        - Others: 40-60
        """
        score = 50  # Base score
        
        # Company size bonus
        if company_size == "enterprise":
            score += 25
        elif company_size == "medium":
            score += 15
        else:
            score += 5
        
        # Seniority increases confidence
        if seniority == "C-level":
            score += 20
        elif seniority == "VP":
            score += 15
        elif seniority == "Director":
            score += 10
        else:
            score += 5
        
        # Random variance
        score += random.randint(-5, 5)
        
        # Clamp to 0-100
        return max(0, min(100, score))
    
    def enrich_lead_offline(self, lead: Dict) -> Dict:
        """Enrich a single lead using offline/rule-based logic.
        
        This is the PRIMARY enrichment mode.
        All logic is deterministic and rule-based - no external APIs.
        """
        company_size = self._estimate_company_size(lead["company_name"], lead["country"])
        persona_tag = self._get_persona_tag(lead["role"], lead["industry"])
        seniority = self._get_seniority(lead["role"], lead["industry"])
        pain_points = self._select_pain_points(lead["industry"])
        buying_triggers = self._select_buying_triggers(lead["industry"])
        confidence_score = self._calculate_confidence_score(company_size, seniority)
        
        return {
            "company_size": company_size,
            "persona_tag": persona_tag,
            "pain_points": json.dumps(pain_points),
            "buying_triggers": json.dumps(buying_triggers),
            "confidence_score": confidence_score
        }
    
    async def enrich_lead_ai_async(self, lead: Dict, client: httpx.AsyncClient) -> Dict:
        """Async AI enrichment for parallel processing."""
        lead_id = lead.get("id", "unknown")
        lead_name = lead.get("full_name", "unknown")
        
        try:
            from ..core.config import settings
            
            if settings.llm_provider != "ollama":
                logger.debug(f"LLM provider not ollama, using offline for {lead_name}")
                offline_result = self.enrich_lead_offline(lead)
                offline_result["lead_id"] = lead_id
                return offline_result
            
            prompt = f"""Analyze this business lead and provide enrichment data:

Company: {lead['company_name']}
Role: {lead['role']}
Industry: {lead['industry']}
Country: {lead['country']}

You must respond with ONLY a valid JSON object, no other text. Use this exact format:
{{
  "company_size": "small, medium or enterprise",
  "persona_tag": "descriptive persona",
  "pain_points": ["challenge1", "challenge2", "challenge3"],
  "buying_triggers": ["trigger1", "trigger2"],
  "confidence_score": between 0 to 100 based on how likely the user is to reply
}}

JSON response:"""

            response = await client.post(
                f"{settings.llm_base_url}/api/generate",
                json={
                    "model": settings.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                enrichment_text = result.get("response", "").strip()
                
                if "```json" in enrichment_text:
                    enrichment_text = enrichment_text.split("```json")[1].split("```")[0].strip()
                elif "```" in enrichment_text:
                    enrichment_text = enrichment_text.split("```")[1].split("```")[0].strip()
                
                enrichment_data = json.loads(enrichment_text)
                
                logger.debug(f"Successfully enriched {lead_name} with AI")
                return {
                    "lead_id": lead_id,
                    "company_size": enrichment_data.get("company_size", "medium"),
                    "persona_tag": enrichment_data.get("persona_tag", "Professional"),
                    "pain_points": json.dumps(enrichment_data.get("pain_points", [])),
                    "buying_triggers": json.dumps(enrichment_data.get("buying_triggers", [])),
                    "confidence_score": enrichment_data.get("confidence_score", 50)
                }
            else:
                logger.warning(f"Ollama returned {response.status_code} for {lead_name}, using offline")
                offline_result = self.enrich_lead_offline(lead)
                offline_result["lead_id"] = lead_id
                return offline_result
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout enriching {lead_name}, using offline fallback")
            offline_result = self.enrich_lead_offline(lead)
            offline_result["lead_id"] = lead_id
            return offline_result
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {lead_name}: {e}, using offline fallback")
            offline_result = self.enrich_lead_offline(lead)
            offline_result["lead_id"] = lead_id
            return offline_result
        except Exception as e:
            logger.error(f"AI enrichment failed for {lead_name}: {e}, using offline fallback")
            offline_result = self.enrich_lead_offline(lead)
            offline_result["lead_id"] = lead_id
            return offline_result
    
    def enrich_lead_ai(self, lead: Dict) -> Dict:
        """Enrich a single lead using AI/LLM (optional) - synchronous wrapper.
        
        This mode uses Ollama (local LLM) to generate more contextual insights.
        Falls back to offline mode if Ollama is not available.
        """
        try:
            from ..core.config import settings
            
            # Check if Ollama is available
            if settings.llm_provider != "ollama":
                logger.warning("AI mode requested but LLM provider not set to ollama, falling back to offline")
                return self.enrich_lead_offline(lead)
            
            # Prepare prompt
            prompt = f"""Analyze this business lead and provide enrichment data:

Company: {lead['company_name']}
Role: {lead['role']}
Industry: {lead['industry']}
Country: {lead['country']}

You must respond with ONLY a valid JSON object, no other text. Use this exact format:
{{
  "company_size": "small, medium or enterprise",
  "persona_tag": "descriptive persona",
  "pain_points": ["challenge1", "challenge2", "challenge3"],
  "buying_triggers": ["trigger1", "trigger2"],
  "confidence_score": between 0 to 100 with company size bonus and Role seniority bonus
}}

JSON response:"""

            # Call Ollama
            response = httpx.post(
                f"{settings.llm_base_url}/api/generate",
                json={
                    "model": settings.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                enrichment_text = result.get("response", "").strip()
                
                # Log the raw response for debugging
                logger.debug(f"LLM response: {enrichment_text[:200]}")
                
                # Try to extract JSON if wrapped in markdown or text
                if "```json" in enrichment_text:
                    enrichment_text = enrichment_text.split("```json")[1].split("```")[0].strip()
                elif "```" in enrichment_text:
                    enrichment_text = enrichment_text.split("```")[1].split("```")[0].strip()
                
                # Parse JSON from response
                enrichment_data = json.loads(enrichment_text)
                
                # Convert to database format
                return {
                    "company_size": enrichment_data.get("company_size", "medium"),
                    "persona_tag": enrichment_data.get("persona_tag", "Professional"),
                    "pain_points": json.dumps(enrichment_data.get("pain_points", [])),
                    "buying_triggers": json.dumps(enrichment_data.get("buying_triggers", [])),
                    "confidence_score": enrichment_data.get("confidence_score", 50)
                }
            else:
                logger.warning(f"Ollama returned status {response.status_code}, falling back to offline")
                return self.enrich_lead_offline(lead)
                
        except Exception as e:
            logger.error(f"AI enrichment failed: {e}, falling back to offline mode")
            return self.enrich_lead_offline(lead)
    
    async def _enrich_batch_async(self, leads: List[Dict]) -> List[Dict]:
        """Process a batch of leads concurrently using async."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [self.enrich_lead_ai_async(lead, client) for lead in leads]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions that weren't caught
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Batch task {i} failed with exception: {result}")
                    # Fallback to offline for this lead
                    offline_result = self.enrich_lead_offline(leads[i])
                    offline_result["lead_id"] = leads[i]["id"]
                    processed_results.append(offline_result)
                else:
                    processed_results.append(result)
            
            return processed_results
    
    def enrich_leads(self, lead_ids: Optional[List[str]] = None, limit: Optional[int] = None) -> Dict:
        """Enrich multiple leads.
        
        Args:
            lead_ids: Specific lead IDs to enrich (if None, enriches all NEW leads)
            limit: Maximum number of leads to enrich
            
        Returns:
            Dict with enrichment results and statistics
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get leads to enrich
            if lead_ids:
                placeholders = ','.join('?' * len(lead_ids))
                query = f"""
                    SELECT id, full_name, company_name, role, industry, 
                           email, country, status
                    FROM leads
                    WHERE id IN ({placeholders}) AND status = 'NEW'
                """
                cursor.execute(query, lead_ids)
            else:
                query = """
                    SELECT id, full_name, company_name, role, industry,
                           email, country, status
                    FROM leads
                    WHERE status = 'NEW'
                """
                if limit:
                    query += f" LIMIT {limit}"
                cursor.execute(query)
            
            leads = cursor.fetchall()
            
            if not leads:
                logger.info("No leads found to enrich")
                return {"enriched": 0, "failed": 0, "leads": []}
            
            logger.info(f"Enriching {len(leads)} leads using {self.mode} mode...")
            
            enriched_count = 0
            failed_count = 0
            enriched_leads = []
            
            # Process in batches for better performance
            # Smaller batch size to avoid overwhelming Ollama
            batch_size = 5 if self.mode == "ai" else 50
            
            logger.info(f"Processing in batches of {batch_size}...")
            
            for batch_start in range(0, len(leads), batch_size):
                batch = leads[batch_start:batch_start + batch_size]
                batch_dicts = [dict(lead) for lead in batch]
                
                # Enrich batch
                if self.mode == "ai":
                    # Process batch in parallel with async
                    batch_enrichments = asyncio.run(self._enrich_batch_async(batch_dicts))
                else:
                    # Sequential for offline mode
                    batch_enrichments = [self.enrich_lead_offline(lead) for lead in batch_dicts]
                
                # Update database
                for lead_dict, enrichment in zip(batch_dicts, batch_enrichments):
                    try:
                        lead_id = lead_dict["id"]
                        
                        # Verify enrichment has required fields
                        if not all(k in enrichment for k in ["company_size", "persona_tag", "pain_points", "buying_triggers", "confidence_score"]):
                            logger.error(f"Incomplete enrichment data for {lead_id}: {enrichment.keys()}")
                            failed_count += 1
                            continue
                        
                        cursor.execute("""
                            UPDATE leads
                            SET company_size = ?,
                                persona_tag = ?,
                                pain_points = ?,
                                buying_triggers = ?,
                                confidence_score = ?,
                                status = 'ENRICHED',
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (
                            enrichment["company_size"],
                            enrichment["persona_tag"],
                            enrichment["pain_points"],
                            enrichment["buying_triggers"],
                            enrichment["confidence_score"],
                            lead_id
                        ))
                        
                        if cursor.rowcount == 0:
                            logger.warning(f"No rows updated for lead {lead_id}")
                        
                        enriched_count += 1
                        enriched_leads.append({
                            "id": lead_id,
                            "name": lead_dict["full_name"],
                            "company": lead_dict["company_name"],
                            "company_size": enrichment["company_size"],
                            "persona_tag": enrichment["persona_tag"],
                            "confidence_score": enrichment["confidence_score"]
                        })
                        
                    except Exception as e:
                        logger.error(f"Error updating lead {lead_dict.get('id', 'unknown')}: {e}", exc_info=True)
                        failed_count += 1
                
                conn.commit()
                logger.info(f"Enriched {enriched_count}/{len(leads)} leads")
            
            logger.info(f"Enrichment complete: {enriched_count} enriched, {failed_count} failed")
            
            return {
                "enriched": enriched_count,
                "failed": failed_count,
                "leads": enriched_leads
            }
