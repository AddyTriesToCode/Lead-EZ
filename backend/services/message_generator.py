"""Message generation service for cold emails and LinkedIn DMs."""
import json
import random
from typing import Dict, List, Tuple
from backend.models.lead import Lead


class MessageGenerator:
    """Generate personalized cold emails and LinkedIn DMs."""
    
    def __init__(self):
        self.ctas = [
            "book a quick 15-minute call",
            "schedule a brief 10-minute chat",
            "grab 30 minutes to discuss",
            "connect for a 15-minute conversation",
            "set aside 10 minutes for an initial call",
            "I would appreciate 15 minutes for a quick call"

        ]
    
    def generate_messages(self, lead: Lead) -> List[Dict[str, str]]:
        """
        Generate 4 messages per lead:
        - 2 cold email variations (A/B)
        - 2 LinkedIn DM variations (A/B)
        
        Args:
            lead: Lead object with enriched data
            
        Returns:
            List of message dictionaries with channel, variant, and content
        """
        messages = []
        
        # Parse enriched data
        pain_points = json.loads(lead.pain_points) if lead.pain_points else []
        triggers = json.loads(lead.buying_triggers) if lead.buying_triggers else []
        
        # Generate Email Variant A
        messages.append({
            "channel": "email",
            "variant": "A",
            "content": self._generate_email_a(lead, pain_points, triggers)
        })
        
        # Generate Email Variant B
        messages.append({
            "channel": "email",
            "variant": "B",
            "content": self._generate_email_b(lead, pain_points, triggers)
        })
        
        # Generate LinkedIn Variant A
        messages.append({
            "channel": "linkedin",
            "variant": "A",
            "content": self._generate_linkedin_a(lead, pain_points, triggers)
        })
        
        # Generate LinkedIn Variant B
        messages.append({
            "channel": "linkedin",
            "variant": "B",
            "content": self._generate_linkedin_b(lead, pain_points, triggers)
        })
        
        return messages
    
    def _generate_email_a(self, lead: Lead, pain_points: List[str], triggers: List[str]) -> str:
        """Generate cold email variant A (direct, pain-point focused)."""
        pain_point = pain_points[0] if pain_points else "operational efficiency challenges"
        trigger = triggers[0] if triggers else "recent changes"
        cta = random.choice(self.ctas)
        
        # Template A: Pain-first approach
        email = f"""Subject: {lead.company_name} - {pain_point.split(' and ')[0]}

Hi {lead.full_name.split()[0]},

I noticed {lead.company_name} is dealing with {pain_point.lower()}. Many {lead.industry.lower()} {self._get_role_type(lead.role)} face this, especially with {trigger.lower()}.

We've helped similar companies reduce these challenges by 40-60% through targeted automation and process optimization.

Given your role as {lead.role}, I'd love to share how we've solved this for other {lead.persona_tag} leaders.

Would you be open to {cta} this week?

Best regards"""
        
        return self._truncate_to_words(email, 120)
    
    def _generate_email_b(self, lead: Lead, pain_points: List[str], triggers: List[str]) -> str:
        """Generate cold email variant B (opportunity-focused)."""
        trigger = triggers[0] if triggers else "recent developments"
        pain_point = pain_points[1] if len(pain_points) > 1 else pain_points[0] if pain_points else "process inefficiencies"
        cta = random.choice(self.ctas)
        
        # Template B: Trigger-first approach
        email = f"""Subject: Quick question about {lead.company_name}

{lead.full_name.split()[0]},

I see {lead.company_name} is experiencing {trigger.lower()}. This typically creates opportunities to address {pain_point.lower()}.

We specialize in helping {lead.industry.lower()} organizations optimize operations during these transitions. Recent clients in similar situations saw 35-50% improvement in key metrics.

As {lead.role}, you might find value in how we approach {pain_point.split()[0].lower()}.

Open to {cta} to explore if there's a fit?

Regards"""
        
        return self._truncate_to_words(email, 120)
    
    def _generate_linkedin_a(self, lead: Lead, pain_points: List[str], triggers: List[str]) -> str:
        """Generate LinkedIn DM variant A (casual, problem-focused)."""
        pain_point = pain_points[0] if pain_points else "operational challenges"
        cta = random.choice(self.ctas)
        
        # Template A: Problem-solution
        dm = f"""Hi {lead.full_name.split()[0]}, saw you're leading {lead.role} at {lead.company_name}. We've helped {lead.industry.lower()} leaders tackle {pain_point.split(',')[0].lower()}. Worth {cta}?"""
        
        return self._truncate_to_words(dm, 60)
    
    def _generate_linkedin_b(self, lead: Lead, pain_points: List[str], triggers: List[str]) -> str:
        """Generate LinkedIn DM variant B (direct value prop)."""
        trigger = triggers[0] if triggers else "recent changes"
        cta = random.choice(self.ctas)
        
        # Template B: Trigger-value
        dm = f"""Hi {lead.full_name.split()[0]}, noticed {trigger.split(' or ')[0].lower()} at {lead.company_name}. We help {lead.persona_tag} leaders in {lead.industry.lower()} optimize during transitions. {cta.capitalize()}?"""
        
        return self._truncate_to_words(dm, 60)
    
    def _get_role_type(self, role: str) -> str:
        """Extract role type for messaging."""
        role_lower = role.lower()
        if 'vp' in role_lower or 'vice president' in role_lower:
            return "VPs"
        elif 'director' in role_lower:
            return "directors"
        elif 'chief' in role_lower or 'ceo' in role_lower or 'cfo' in role_lower or 'cto' in role_lower:
            return "executives"
        elif 'manager' in role_lower:
            return "managers"
        elif 'head' in role_lower:
            return "heads"
        else:
            return "leaders"
    
    def _truncate_to_words(self, text: str, max_words: int) -> str:
        """Truncate text to maximum word count."""
        words = text.split()
        if len(words) <= max_words:
            return text
        
        truncated = ' '.join(words[:max_words])
        # Try to end at a sentence
        if '.' in truncated:
            sentences = truncated.split('.')
            # Keep all complete sentences
            return '.'.join(sentences[:-1]) + '.'
        
        return truncated + '...'
