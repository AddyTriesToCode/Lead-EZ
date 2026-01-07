"""
n8n Agent Control Logic
=======================

This module provides the decision-making logic for the n8n agent workflow.
The agent examines lead/message status fields and determines which MCP tool 
endpoint to call next in the pipeline.

PIPELINE STAGES:
1. NEW -> generate_leads -> GENERATED
2. GENERATED -> enrich_leads -> ENRICHED  
3. ENRICHED -> generate_messages -> MESSAGED
4. MESSAGED -> review_messages -> APPROVED/REJECTED
5. APPROVED -> send_messages -> SENT
6. FAILED -> retry logic
"""

from typing import Dict, List, Optional
from datetime import datetime


class AgentDecisionEngine:
    """Decision engine that determines next action based on status."""
    
    # Pipeline stage definitions
    STAGES = {
        "NEW": {
            "next_action": "generate_leads",
            "mcp_endpoint": "/tools/generate_leads",
            "description": "Generate new leads"
        },
        "GENERATED": {
            "next_action": "enrich_leads",
            "mcp_endpoint": "/tools/enrich_leads",
            "description": "Enrich lead data with pain points and triggers"
        },
        "ENRICHED": {
            "next_action": "generate_messages",
            "mcp_endpoint": "/tools/generate_messages",
            "description": "Generate 4 message variants per lead"
        },
        "MESSAGED": {
            "next_action": "review_messages",
            "mcp_endpoint": "/tools/review_messages",
            "description": "Review messages for quality and compliance"
        },
        "APPROVED": {
            "next_action": "send_messages",
            "mcp_endpoint": "/tools/send_messages",
            "description": "Send approved messages via queue"
        },
        "SENT": {
            "next_action": "track_responses",
            "mcp_endpoint": "/tools/track_responses",
            "description": "Monitor for replies and engagement"
        },
        "FAILED": {
            "next_action": "retry_or_escalate",
            "mcp_endpoint": "/tools/retry_failed",
            "description": "Retry failed messages or escalate"
        }
    }
    
    @staticmethod
    def decide_next_action(lead_status: str, message_status: Optional[str] = None) -> Dict:
        """Determine the next action based on current status.
        
        Args:
            lead_status: Current lead status (NEW, GENERATED, ENRICHED, etc.)
            message_status: Optional message status (PENDING, APPROVED, SENT, FAILED)
            
        Returns:
            Dict with next_action, mcp_endpoint, and parameters
        """
        # If we have message status, prioritize message-based decisions
        if message_status:
            if message_status == "PENDING":
                return {
                    "action": "review_messages",
                    "endpoint": "/tools/review_messages",
                    "method": "POST",
                    "params": {"auto_approve": False},
                    "description": "Review pending messages"
                }
            elif message_status == "APPROVED":
                return {
                    "action": "send_messages",
                    "endpoint": "/tools/send_messages",
                    "method": "POST",
                    "params": {"use_queue": True, "batch_size": 50},
                    "description": "Send approved messages via queue"
                }
            elif message_status == "FAILED":
                return {
                    "action": "retry_failed",
                    "endpoint": "/tools/retry_failed",
                    "method": "POST",
                    "params": {"max_retries": 3},
                    "description": "Retry failed messages"
                }
            elif message_status == "SENT":
                return {
                    "action": "complete",
                    "endpoint": None,
                    "method": None,
                    "params": {},
                    "description": "Message delivery complete"
                }
        
        # Lead-based decisions
        stage = AgentDecisionEngine.STAGES.get(lead_status)
        if stage:
            return {
                "action": stage["next_action"],
                "endpoint": stage["mcp_endpoint"],
                "method": "POST",
                "params": {},
                "description": stage["description"]
            }
        
        # Unknown status
        return {
            "action": "error",
            "endpoint": None,
            "method": None,
            "params": {},
            "description": f"Unknown status: {lead_status}"
        }
    
    @staticmethod
    def batch_decide(items: List[Dict]) -> Dict[str, List[Dict]]:
        """Decide actions for a batch of leads/messages.
        
        Args:
            items: List of items with 'lead_status' and optional 'message_status'
            
        Returns:
            Dict mapping action names to lists of items needing that action
        """
        actions = {}
        
        for item in items:
            lead_status = item.get("lead_status", "NEW")
            message_status = item.get("message_status")
            
            decision = AgentDecisionEngine.decide_next_action(lead_status, message_status)
            action = decision["action"]
            
            if action not in actions:
                actions[action] = []
            
            actions[action].append({
                **item,
                "next_endpoint": decision["endpoint"],
                "next_method": decision["method"],
                "next_params": decision["params"]
            })
        
        return actions
    
    @staticmethod
    def should_proceed(lead_status: str, message_status: Optional[str] = None, 
                      retry_count: int = 0, max_retries: int = 3) -> bool:
        """Determine if processing should continue.
        
        Args:
            lead_status: Current lead status
            message_status: Optional message status
            retry_count: Number of retry attempts
            max_retries: Maximum allowed retries
            
        Returns:
            True if should proceed, False if should stop
        """
        # Stop conditions
        if lead_status == "SENT" and message_status == "SENT":
            return False  # Successfully completed
        
        if message_status == "FAILED" and retry_count >= max_retries:
            return False  # Exceeded retry limit
        
        if lead_status in ["INVALID", "BLOCKED", "UNSUBSCRIBED"]:
            return False  # Should not contact
        
        return True
    
    @staticmethod
    def get_priority(lead_status: str, confidence_score: int = 50) -> int:
        """Calculate processing priority for a lead.
        
        Higher confidence and earlier stages get higher priority.
        
        Args:
            lead_status: Current lead status
            confidence_score: Lead confidence score (0-100)
            
        Returns:
            Priority score (higher = more urgent)
        """
        # Base priority from stage
        stage_priority = {
            "NEW": 100,
            "GENERATED": 90,
            "ENRICHED": 80,
            "MESSAGED": 70,
            "APPROVED": 60,  # Highest priority for sending
            "SENT": 10,
            "FAILED": 50
        }.get(lead_status, 0)
        
        # Boost for high confidence leads
        confidence_boost = confidence_score / 10
        
        return int(stage_priority + confidence_boost)


# ============================================================================
# N8N CODE NODE IMPLEMENTATION
# ============================================================================

def n8n_agent_node_code():
    """
    Copy this code into an n8n Code node (JavaScript/Python).
    
    This code should be used in a Code node that:
    1. Receives lead/message data
    2. Decides the next MCP endpoint to call
    3. Outputs the decision to an HTTP Request node
    """
    
    # Python version (for Python Code node)
    python_code = '''
# Input: items from previous node
# Expected fields: lead_status, message_status (optional), lead_id, confidence_score

from datetime import datetime

def decide_next_action(lead_status, message_status=None):
    """Decide which MCP endpoint to call next."""
    
    # Message-based decisions take priority
    if message_status:
        if message_status == "PENDING":
            return {
                "action": "review_messages",
                "endpoint": "http://localhost:8001/tools/review_messages",
                "method": "POST"
            }
        elif message_status == "APPROVED":
            return {
                "action": "send_messages",
                "endpoint": "http://localhost:8001/tools/send_messages",
                "method": "POST"
            }
        elif message_status == "FAILED":
            return {
                "action": "retry_failed",
                "endpoint": "http://localhost:8001/tools/retry_failed",
                "method": "POST"
            }
        elif message_status == "SENT":
            return {"action": "complete", "endpoint": None}
    
    # Lead-based decisions
    actions = {
        "NEW": ("generate_leads", "http://localhost:8001/tools/generate_leads"),
        "GENERATED": ("enrich_leads", "http://localhost:8001/tools/enrich_leads"),
        "ENRICHED": ("generate_messages", "http://localhost:8001/tools/generate_messages"),
        "MESSAGED": ("review_messages", "http://localhost:8001/tools/review_messages"),
        "APPROVED": ("send_messages", "http://localhost:8001/tools/send_messages"),
    }
    
    if lead_status in actions:
        action, endpoint = actions[lead_status]
        return {"action": action, "endpoint": endpoint, "method": "POST"}
    
    return {"action": "error", "endpoint": None}

# Process all items
output = []
for item in items:
    lead_status = item.get("json", {}).get("lead_status", "NEW")
    message_status = item.get("json", {}).get("message_status")
    
    decision = decide_next_action(lead_status, message_status)
    
    output.append({
        "json": {
            **item.get("json", {}),
            "next_action": decision["action"],
            "next_endpoint": decision["endpoint"],
            "next_method": decision.get("method", "POST"),
            "timestamp": datetime.now().isoformat()
        }
    })

return output
'''
    
    # JavaScript version (for JavaScript Code node)
    javascript_code = '''
// Input: $input.all() - array of items from previous node

function decideNextAction(leadStatus, messageStatus) {
    // Message-based decisions take priority
    if (messageStatus) {
        if (messageStatus === "PENDING") {
            return {
                action: "review_messages",
                endpoint: "http://localhost:8001/tools/review_messages",
                method: "POST"
            };
        } else if (messageStatus === "APPROVED") {
            return {
                action: "send_messages",
                endpoint: "http://localhost:8001/tools/send_messages",
                method: "POST"
            };
        } else if (messageStatus === "FAILED") {
            return {
                action: "retry_failed",
                endpoint: "http://localhost:8001/tools/retry_failed",
                method: "POST"
            };
        } else if (messageStatus === "SENT") {
            return { action: "complete", endpoint: null };
        }
    }
    
    // Lead-based decisions
    const actions = {
        "NEW": { action: "generate_leads", endpoint: "http://localhost:8001/tools/generate_leads" },
        "GENERATED": { action: "enrich_leads", endpoint: "http://localhost:8001/tools/enrich_leads" },
        "ENRICHED": { action: "generate_messages", endpoint: "http://localhost:8001/tools/generate_messages" },
        "MESSAGED": { action: "review_messages", endpoint: "http://localhost:8001/tools/review_messages" },
        "APPROVED": { action: "send_messages", endpoint: "http://localhost:8001/tools/send_messages" },
    };
    
    if (leadStatus in actions) {
        return { ...actions[leadStatus], method: "POST" };
    }
    
    return { action: "error", endpoint: null };
}

// Process all items
const output = [];
for (const item of $input.all()) {
    const leadStatus = item.json.lead_status || "NEW";
    const messageStatus = item.json.message_status;
    
    const decision = decideNextAction(leadStatus, messageStatus);
    
    output.push({
        json: {
            ...item.json,
            next_action: decision.action,
            next_endpoint: decision.endpoint,
            next_method: decision.method || "POST",
            timestamp: new Date().toISOString()
        }
    });
}

return output;
'''
    
    return {
        "python": python_code,
        "javascript": javascript_code
    }


# Export for use in other modules
__all__ = ["AgentDecisionEngine", "n8n_agent_node_code"]
