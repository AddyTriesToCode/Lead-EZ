# Testing the Pipeline Fix

The issue has been identified and fixed. Here's what to do:

## Steps to Test:

1. **Ensure n8n has the latest workflow**:
   - Open n8n at http://localhost:5678
   - Delete the existing "Lead-EZ Agent Pipeline" workflow
   - Click "Import from File"
   - Select `automation/n8n_agent_workflow.json`
   - Click "Save"

2. **Open the frontend**:
   - Go to http://localhost:3001
   - Open browser console (F12)

3. **Test the pipeline**:
   - Set "Number of Leads" to **10**
   - Click "Run Pipeline"
   - Check the console logs - you should see:
     ```
     🔍 api.runPipeline called with params: {leadCount: 10, ...}
     🔍 Final config being sent: {leadCount: 10, ...}
     ```

4. **Verify the results**:
   ```bash
   python scripts/debug_messages.py
   ```
   Should show: **10 leads, 40 messages**

## What Was Fixed:

1. **Frontend API** (`api.js`):
   - Changed `params.leadCount || 200` to `params.leadCount !== undefined ? params.leadCount : 200`
   - This ensures the actual value is passed instead of defaulting to 200

2. **n8n Workflow** (`n8n_agent_workflow.json`):
   - Updated agent decision logic to detect fresh pipeline runs
   - Now calls `/tools/run_pipeline` once instead of duplicating steps

3. **Added Debug Logging**:
   - Console logs now show exactly what parameters are being sent
   - Helps identify any issues in the flow

## If Still Not Working:

Check the browser console logs and share them - they will show exactly what's being sent from the frontend.
