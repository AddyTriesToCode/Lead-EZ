# Lead-EZ Pipeline Workflow (Corrected)

## Complete Pipeline Flow

### 1. Lead Generation
- Generates N leads with realistic data
- Status: `NEW`

### 2. Lead Enrichment
- Enriches leads with persona tags, pain points, and buying triggers
- Assigns confidence scores (0-100)
- Status: `NEW` → `ENRICHED`

### 3. Message Generation
- **Only for leads with confidence score ≥ 60**
- Generates **4 messages per lead**:
  - Email Variant A
  - Email Variant B
  - LinkedIn Variant A
  - LinkedIn Variant B
- All messages start with status: `PENDING`

### 4. Message Review
- Randomly selects **1 of 2 variants per channel** for each lead
- **Result: 2 approved messages per lead** (1 email + 1 LinkedIn)
- Selected messages: `PENDING` → `APPROVED`
- Rejected messages: `PENDING` → `REJECTED`

### 5. Message Sending

#### Dry Run Mode (`dryRun: true`)
- Fetches all **APPROVED** messages from database
- Saves them to `storage/messages/dry_run_messages.json`
- Updates message status: `APPROVED` → `SENT`
- **No actual delivery attempted**

#### Live Run Mode (`dryRun: false`)
- Fetches all **APPROVED** messages from database
- **Email messages**:
  - Attempts to send via SMTP
  - On success: `APPROVED` → `SENT`, lead becomes `CONTACTED`
  - On failure: Retries up to max_retries, then marks as `FAILED`
- **LinkedIn messages**:
  - **Skipped** (not implemented yet)
  - Marked as `REJECTED` with note "LinkedIn not implemented"

### 6. Archive to History
- Copies all **SENT** and **APPROVED** messages to history table
- **Retains data in leads/messages tables** (for viewing results)
- Working tables cleared only when next pipeline starts

## Key Changes Made

### ✅ Fixed Issues:

1. **Message Queue**: Now fetches `APPROVED` messages (not `PENDING`)
2. **LinkedIn in Live Mode**: Now skips LinkedIn messages instead of saving them to storage
3. **Working Tables**: Retained after pipeline completes (not cleared)
4. **Dry Run**: Properly saves approved messages to JSON file

### Message Flow Summary:

```
Lead (confidence ≥ 60)
    ↓
4 Messages Generated (PENDING)
    ↓
Review: 2 Approved, 2 Rejected
    ↓
DRY RUN: Save 2 to JSON → SENT
LIVE RUN: Send 1 email → SENT, Skip 1 LinkedIn → REJECTED
```

## Expected Results

For **10 leads** with all above confidence threshold:
- **Generated**: 40 messages (4 per lead)
- **Approved**: 20 messages (2 per lead)
- **Dry Run Saved**: 20 messages to JSON
- **Live Run Sent**: ~10 email messages, 10 LinkedIn skipped
