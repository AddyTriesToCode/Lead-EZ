# SendGrid Webhook Configuration

This guide explains how to set up SendGrid webhooks to track email bounces and delivery status.

## What Are Webhooks?

SendGrid webhooks send real-time notifications about email events:
- **bounce**: Email bounced (invalid recipient, full mailbox, etc.)
- **dropped**: SendGrid rejected the email (spam, unsubscribed, etc.)
- **delivered**: Email successfully delivered to recipient's inbox
- **spamreport**: Recipient marked email as spam

## Setup Steps

### 1. Expose Your Webhook Endpoint

Your webhook endpoint is: `POST http://your-server:8001/webhooks/sendgrid`

**For local development**, use a tunneling service to expose localhost:

#### Option A: ngrok (Recommended)
```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8001
```

You'll get a public URL like: `https://abc123.ngrok.io`

Your webhook URL becomes: `https://abc123.ngrok.io/webhooks/sendgrid`

#### Option B: localtunnel
```bash
npm install -g localtunnel
lt --port 8001
```

### 2. Configure SendGrid Webhooks

1. Go to: https://app.sendgrid.com/settings/mail_settings
2. Click **Event Webhook** (under Mail Settings)
3. Toggle **Event Webhook Status** to **ON**
4. Set **HTTP POST URL**: `https://your-ngrok-url.ngrok.io/webhooks/sendgrid`
5. Select events to track:
   - ☑️ Bounced
   - ☑️ Dropped
   - ☑️ Delivered (optional, for confirmation)
   - ☑️ Spam Reports (optional)
6. Click **Save**

### 3. Test the Webhook

SendGrid provides a test button to verify your endpoint is reachable.

Alternatively, send an email to a known invalid address:
```python
# In your test script
invalid_lead = {
    "email": "invalid@example.invalid",  # This will bounce
    "name": "Test User"
}
```

### 4. Monitor Webhook Events

Check your MCP server logs:
```bash
# You'll see logs like:
2026-01-09 10:15:30 - leadez - INFO - Received 1 SendGrid webhook events
2026-01-09 10:15:30 - leadez - WARNING - Email bounce for invalid@example.invalid: 550 User unknown
2026-01-09 10:15:30 - leadez - INFO - Message abc-123 marked as BOUNCED
2026-01-09 10:15:30 - leadez - INFO - Lead xyz-456 marked as UNCONTACTED (all messages bounced)
```

## How It Works

When SendGrid sends a bounce event:

1. **Webhook received**: `POST /webhooks/sendgrid` receives bounce data
2. **Find message**: Looks up the most recent SENT message for that email
3. **Update message**: Sets status to `BOUNCED` with error reason
4. **Check lead**: If ALL messages for a lead bounced, set lead status to `UNCONTACTED`
5. **Log**: Records event in application logs

## Message Status Flow

```
APPROVED → SENT → BOUNCED (if webhook reports bounce)
           ↓
        CONTACTED (if delivered successfully)
```

## Lead Status Flow

```
ENRICHED → CONTACTED (at least 1 message delivered)
        → UNCONTACTED (all messages bounced/failed)
```

## Troubleshooting

### Webhook not receiving events
- Check ngrok is running and forwarding to port 8001
- Verify MCP server is running on port 8001
- Test webhook from SendGrid dashboard

### Events received but not processed
- Check MCP server logs for errors
- Verify the email address matches a lead in your database
- Ensure message was in SENT status before bounce

### Need to replay events
SendGrid stores webhook events for 30 days. You can replay them from:
https://app.sendgrid.com/settings/mail_settings → Event Webhook → Event History

## Production Deployment

For production, replace ngrok with:
- Your actual domain: `https://api.yourdomain.com/webhooks/sendgrid`
- Use HTTPS (required by SendGrid)
- Consider webhook signature verification for security (add to future implementation)

## Database Schema

Messages table tracks bounces:
```sql
status TEXT  -- Can be: PENDING, APPROVED, SENT, BOUNCED, FAILED
error_message TEXT  -- Stores bounce reason (e.g., "bounce: 550 User unknown")
```

Leads table reflects contact status:
```sql
status TEXT  -- Can be: NEW, ENRICHED, CONTACTED, UNCONTACTED
```
