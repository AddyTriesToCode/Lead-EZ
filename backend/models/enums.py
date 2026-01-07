from enum import Enum


class LeadStatus(str, Enum):
    NEW = "NEW"
    ENRICHED = "ENRICHED"
    MESSAGED = "MESSAGED"
    SENT = "SENT"
    FAILED = "FAILED"


class CompanySize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    ENTERPRISE = "enterprise"


class MessageChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"


class MessageStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
