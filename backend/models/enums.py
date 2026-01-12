from enum import Enum


class LeadStatus(str, Enum):
    NEW = "NEW"
    ENRICHED = "ENRICHED"
    MESSAGED = "MESSAGED"  # Deprecated - kept for backwards compatibility
    CONTACTED = "CONTACTED"  # Successfully contacted
    UNCONTACTED = "UNCONTACTED"  # Failed to contact after retries
    SENT = "SENT"  # Deprecated - use CONTACTED instead
    FAILED = "FAILED"  # Deprecated - use UNCONTACTED instead


class CompanySize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    ENTERPRISE = "enterprise"


class MessageChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"


class MessageStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENT = "SENT"
    BOUNCED = "BOUNCED"  # Email bounced (invalid recipient)
    FAILED = "FAILED"
