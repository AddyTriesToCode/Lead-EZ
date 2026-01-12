import axios from 'axios'
const BASE_URL = 'http://localhost:8001'

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const api = {
  // Get pipeline statistics
  async getStats() {
    const { data } = await apiClient.get('/tools/get_stats')
    return data
  },

  // Get leads with pagination
  async getLeads({ status = null, limit = 100, offset = 0 } = {}) {
    const params = { limit, offset }
    if (status) params.status = status
    const { data } = await apiClient.get('/leads', { params })
    return data
  },

  // Generate leads
  async generateLeads({ count, save_to_db = true, seed = null } = {}) {
    const { data } = await apiClient.post('/tools/generate_leads', {
      count,
      save_to_db,
      seed
    })
    return data
  },

  // Enrich leads
  async enrichLeads({ lead_ids = null, limit = null, mode = 'offline' } = {}) {
    const { data } = await apiClient.post('/tools/enrich_leads', {
      lead_ids,
      limit,
      mode
    })
    return data
  },

  // Generate messages
  async generateMessages({ lead_ids = null, limit = null, min_confidence_score = 60 } = {}) {
    const { data } = await apiClient.post('/tools/generate_messages', {
      lead_ids,
      limit,
      min_confidence_score
    })
    return data
  },

  // Review messages
  async reviewMessages({ message_ids = null } = {}) {
    const { data } = await apiClient.post('/tools/review_messages', {
      message_ids
    })
    return data
  },

  // Send messages
  async sendMessages({ message_ids = null, use_queue = true, batch_size = 50, dry_run = true } = {}) {
    const { data } = await apiClient.post('/tools/send_messages', {
      message_ids,
      use_queue,
      batch_size,
      dry_run
    })
    return data
  },

  // Run entire pipeline (orchestrated via n8n workflow)
  async runPipeline(params = {}) {
    console.log('🔍 api.runPipeline called with params:', params)
    
    const config = {
      leadCount: params.leadCount !== undefined ? params.leadCount : 200,
      seed: params.seed !== undefined ? params.seed : null,
      enrichmentMode: params.enrichmentMode || 'offline',
      dryRun: params.dryRun !== undefined ? params.dryRun : true,
      pipelineRunId: params.pipelineRunId || `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    }
    
    console.log('🔍 Final config being sent:', config)

    try {
      // Call n8n webhook to trigger the agent workflow
      console.log('🔍 Calling n8n webhook at http://localhost:5678/webhook/run-pipeline')
      const { data } = await axios.post('http://localhost:5678/webhook/run-pipeline', {
        trigger: 'frontend',
        timestamp: new Date().toISOString(),
        config
      })
      console.log('✅ n8n webhook responded:', data)
      return data
    } catch (err) {
      // Fallback to direct MCP endpoint if n8n is not running
      console.warn('n8n webhook failed, falling back to MCP endpoint:', err.message)
      const { data } = await apiClient.post('/tools/run_pipeline', config)
      return data
    }
  },

  // Archive pipeline data to history
  async archivePipeline({ pipeline_run_id, dry_run = true } = {}) {
    const { data } = await apiClient.post('/tools/archive_pipeline', {
      pipeline_run_id,
      dry_run
    })
    return data
  },

  // Get history records
  async getHistory({ pipeline_run_id = null, limit = 100 } = {}) {
    const params = { limit }
    if (pipeline_run_id) params.pipeline_run_id = pipeline_run_id
    const { data } = await apiClient.get('/tools/get_history', { params })
    return data
  },

  // Get pipeline runs list
  async getPipelineRuns({ limit = 50 } = {}) {
    const { data } = await apiClient.get('/tools/get_pipeline_runs', { params: { limit } })
    return data
  },

  // Get dry run messages
  async getDryRunMessages() {
    const { data } = await apiClient.get('/tools/get_dry_run_messages')
    return data
  },

  // Clear dry run messages
  async clearDryRunMessages() {
    const { data } = await apiClient.post('/tools/clear_dry_run_messages')
    return data
  },

  // Clear working tables (leads and messages)
  async clearWorkingTables() {
    const { data } = await apiClient.post('/tools/clear_working_tables')
    return data
  }
}
