import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pipelineRunning, setPipelineRunning] = useState(false)
  const [lastPipelineRunId, setLastPipelineRunId] = useState(null)
  const [workflowSteps, setWorkflowSteps] = useState([])
  const [numLeads, setNumLeads] = useState('')
  const [seedValue, setSeedValue] = useState('')
  const [enrichmentMode, setEnrichmentMode] = useState('offline')
  const [dryRun, setDryRun] = useState(true)

  // Fetch stats - from history when idle, from working tables when running
  const fetchStats = async () => {
    try {
      setLoading(true)
      
      if (pipelineRunning) {
        // During pipeline execution, show working table stats
        const data = await api.getStats()
        setStats(data)
      } else {
        // When idle, show stats from last pipeline run in history
        const pipelineRuns = await api.getPipelineRuns({ limit: 1 })
        
        if (pipelineRuns.runs && pipelineRuns.runs.length > 0) {
          const lastRun = pipelineRuns.runs[0]
          const historyData = await api.getHistory({ 
            pipeline_run_id: lastRun.pipeline_run_id, 
            limit: 1000 
          })
          
          // Convert history data to stats format
          const records = historyData.records || []
          const leads = new Set(records.map(r => r.lead_id))
          const sentMessages = records.filter(r => r.message_status === 'SENT')
          const approvedMessages = records.filter(r => r.message_status === 'APPROVED')
          // Total approved = APPROVED + SENT (since SENT messages were previously approved)
          const totalApproved = approvedMessages.length + sentMessages.length
          
          // Get unique leads with confidence scores from records
          const leadsWithScores = new Map()
          records.forEach(r => {
            if (r.lead_id && r.confidence_score !== null && r.confidence_score !== undefined) {
              leadsWithScores.set(r.lead_id, r.confidence_score)
            }
          })
          const leadsAboveThreshold = Array.from(leadsWithScores.values()).filter(score => score >= 60).length
          
          setStats({
            summary: {
              total_leads: leads.size,
              leads_enriched: leads.size,
              leads_above_threshold: leadsAboveThreshold,
              total_messages: records.length,
              messages_sent: sentMessages.length,
              messages_failed: 0,
              messages_pending: approvedMessages.length
            },
            leads: { ENRICHED: leads.size },
            messages: { 
              SENT: sentMessages.length,
              APPROVED: totalApproved
            },
            timestamp: new Date().toISOString(),
            from_history: true,
            pipeline_run_id: lastRun.pipeline_run_id
          })
          setLastPipelineRunId(lastRun.pipeline_run_id)
        } else {
          // No history, show empty stats
          setStats({
            summary: {
              total_leads: 0,
              leads_enriched: 0,
              leads_above_threshold: 0,
              total_messages: 0,
              messages_sent: 0,
              messages_failed: 0,
              messages_pending: 0
            },
            leads: {},
            messages: {},
            timestamp: new Date().toISOString()
          })
        }
      }
      
      setError(null)
      setLoading(false)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to connect to backend'
      setError(`Backend Error: ${errorMsg}`)
      console.error('Error fetching stats:', err)
      setLoading(false)
      setStats({
        summary: {
          total_leads: 0,
          leads_enriched: 0,
          total_messages: 0,
          messages_sent: 0,
          messages_failed: 0,
          messages_pending: 0
        },
        leads: {},
        messages: {},
        timestamp: new Date().toISOString()
      })
    }
  }

  // Initial fetch and refresh based on pipeline state
  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 3000) // Refresh every 3 seconds
    return () => clearInterval(interval)
  }, [pipelineRunning]) // Re-fetch when pipeline state changes

  // Calculate metrics
  const getMetrics = () => {
    if (!stats) return null

    // Lead metrics
    const totalLeads = stats.summary.total_leads || 0
    const leadsEnriched = stats.summary.leads_enriched || 0
    const leadsAboveThreshold = stats.summary.leads_above_threshold || 0
    
    // Message metrics - use actual counts from database
    const totalMessages = stats.summary.total_messages || 0
    const messagesApproved = stats.messages?.APPROVED || 0
    const messagesSent = stats.messages?.SENT || 0

    return {
      totalLeads,
      leadsEnriched,
      leadsAboveThreshold,
      totalMessages,
      messagesApproved,
      messagesSent
    }
  }

  // Prepare pie chart data
  const getPieChartData = () => {
    const metrics = getMetrics()
    if (!metrics) return []

    const { totalLeads, leadsEnriched, totalMessages, messagesApproved, messagesSent } = metrics
    
    return [
      { name: 'Leads Generated', value: totalLeads, color: '#646cff' },
      { name: 'Leads Enriched', value: leadsEnriched, color: '#8b5cf6' },
      { name: 'Messages Generated', value: totalMessages, color: '#3b82f6' },
      { name: 'Messages Approved', value: messagesApproved, color: '#10b981' },
      { name: 'Messages Sent', value: messagesSent, color: '#f59e0b' }
    ].filter(item => item.value > 0)
  }

  // Calculate percentages for pie chart
  const calculatePercentages = () => {
    const data = getPieChartData()
    const total = data.reduce((sum, item) => sum + item.value, 0)
    return data.map(item => ({
      ...item,
      percentage: ((item.value / total) * 100).toFixed(1)
    }))
  }

  // Run pipeline using n8n agent orchestration
  const handleRunPipeline = async () => {
    // Validate number of leads
    if (!numLeads || numLeads < 1 || numLeads > 250) {
      setError('Number of leads must be between 1 and 250')
      return
    }

    // Generate random seed if not provided
    const seed = seedValue ? parseInt(seedValue) : Math.floor(Math.random() * 250) + 1
    
    // Generate unique pipeline run ID for this execution
    const pipelineRunId = `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    setPipelineRunning(true)
    setLastPipelineRunId(pipelineRunId)
    setError(null)
    setWorkflowSteps([
      { id: 1, name: 'n8n Agent Orchestration', status: 'completed', icon: '🤖' },
      { id: 2, name: 'Generate Leads', status: 'active', icon: '👥' },
      { id: 3, name: 'Enrich Leads', status: 'pending', icon: '✨' },
      { id: 4, name: 'Generate Messages', status: 'pending', icon: '✉️' },
      { id: 5, name: 'Review & Send', status: 'pending', icon: '🚀' },
      { id: 6, name: 'Archive to History', status: 'pending', icon: '💾' }
    ])

    // Setup progress polling to update workflow steps
    const progressInterval = setInterval(async () => {
      try {
        const currentStats = await api.getStats()
        const totalLeads = currentStats.summary?.total_leads || 0
        const leadsEnriched = currentStats.summary?.leads_enriched || 0
        const totalMessages = currentStats.summary?.total_messages || 0
        const messagesApproved = currentStats.messages?.APPROVED || 0
        const messagesSent = currentStats.messages?.SENT || 0

        setWorkflowSteps(prev => {
          const updated = [...prev]
          
          // Step 1: n8n Orchestration - always completed when we start
          updated[0].status = 'completed'
          
          // Step 2: Generate Leads
          if (totalLeads > 0) {
            updated[1].status = 'completed'
            updated[2].status = 'active'
          }
          
          // Step 3: Enrich Leads
          if (leadsEnriched > 0) {
            updated[2].status = 'completed'
            updated[3].status = 'active'
          }
          
          // Step 4: Generate Messages
          if (totalMessages > 0) {
            updated[3].status = 'completed'
            updated[4].status = 'active'
          }
          
          // Step 5: Review & Send
          if (messagesApproved > 0 || messagesSent > 0) {
            updated[4].status = 'completed'
            updated[5].status = 'active'
          }
          
          return updated
        })
      } catch (err) {
        console.error('Error polling progress:', err)
      }
    }, 1000) // Poll every second

    try {
      console.log('🤖 Triggering n8n agent workflow orchestration...')
      console.log(`Config: ${numLeads} leads, seed: ${seed}, mode: ${enrichmentMode}, dryRun: ${dryRun}`)
      
      // Call n8n workflow orchestration (with fallback to direct MCP)
      const result = await api.runPipeline({
        leadCount: numLeads,
        seed: seed,
        enrichmentMode: enrichmentMode,
        dryRun: dryRun,
        pipelineRunId: pipelineRunId
      })
      
      console.log('✅ n8n agent workflow completed:', result)
      
      // Stop polling
      clearInterval(progressInterval)
      
      // Mark all steps as completed
      setWorkflowSteps(prev => prev.map((step) => ({ ...step, status: 'completed' })))
      
      // Fetch final stats
      await fetchStats()
      
      console.log('Pipeline completed and archived successfully!')
      
    } catch (err) {
      console.error('Pipeline error:', err)
      
      // Stop polling on error
      clearInterval(progressInterval)
      
      const errorMsg = err.response?.data?.detail || err.message || 'Unknown error'
      
      // Check if it's an n8n connection error
      if (err.message?.includes('ERR_CONNECTION_REFUSED') || err.code === 'ECONNREFUSED') {
        setError(`n8n Error: n8n server not running at http://localhost:5678. Please start n8n with './scripts/start_n8n.ps1'`)
      } else {
        setError(`Pipeline Error: ${errorMsg}`)
      }
      
      // Mark current step as failed
      setWorkflowSteps(prev => prev.map(step => 
        step.status === 'active' ? { ...step, status: 'failed' } : step
      ))
    } finally {
      setPipelineRunning(false)
      setTimeout(() => setWorkflowSteps([]), 5000)
    }
  }

  const metrics = getMetrics()
  const pieData = calculatePercentages()

  if (loading && !stats) {
    return (
      <div className="loading">
        <div className="loading-spinner"></div>
        Loading dashboard...
      </div>
    )
  }

  return (
    <>
      {error && <div className="error">{error}</div>}

      {/* Metrics Cards */}
      {metrics && (
        <div className="metrics-grid">
          <div className="metric-card primary">
            <div className="metric-label">Leads Generated</div>
            <div className="metric-value">{metrics.totalLeads}</div>
          </div>
          
          <div className="metric-card info">
            <div className="metric-label">Leads Enriched</div>
            <div className="metric-value">{metrics.leadsEnriched}</div>
          </div>
          
          <div className="metric-card success">
            <div className="metric-label">Above Confidence Threshold</div>
            <div className="metric-value">{metrics.leadsAboveThreshold}</div>
          </div>
          
          <div className="metric-card info">
            <div className="metric-label">Messages Generated</div>
            <div className="metric-value">{metrics.totalMessages}</div>
          </div>
          
          <div className="metric-card success">
            <div className="metric-label">Messages Approved</div>
            <div className="metric-value">{metrics.messagesApproved}</div>
          </div>
        </div>
      )}

      {/* Pipeline Control */}
      <div className="pipeline-section">
        <h2>Pipeline Control</h2>
        
        <div className="pipeline-inputs">
          <div className="input-group">
            <label htmlFor="numLeads">
              Number of Leads <span className="required">*</span>
            </label>
            <input
              id="numLeads"
              type="number"
              min="1"
              max="250"
              value={numLeads}
              onChange={(e) => {
                const value = e.target.value
                if (value === '') {
                  setNumLeads('')
                } else {
                  const num = parseInt(value)
                  // Allow typing but validate on blur
                  setNumLeads(num)
                }
              }}
              onBlur={(e) => {
                const value = e.target.value
                if (value !== '') {
                  const num = parseInt(value)
                  // Clamp value between 1 and 250
                  if (num < 1) {
                    setNumLeads(1)
                  } else if (num > 250) {
                    setNumLeads(250)
                  }
                }
              }}
              placeholder="Enter 1-250"
              disabled={pipelineRunning}
              className={numLeads !== '' && (numLeads < 1 || numLeads > 250) ? 'input-error' : ''}
            />
            <span className="input-hint">Required: 1-250 leads</span>
            {numLeads !== '' && numLeads < 1 && (
              <span className="input-error-message">Value must be at least 1</span>
            )}
            {numLeads !== '' && numLeads > 250 && (
              <span className="input-error-message">Value must not exceed 250</span>
            )}
          </div>

          <div className="input-group">
            <label htmlFor="seedValue">
              Seed Value <span className="optional">(Optional)</span>
            </label>
            <input
              id="seedValue"
              type="number"
              value={seedValue}
              onChange={(e) => setSeedValue(e.target.value)}
              placeholder="Leave empty for random"
              disabled={pipelineRunning}
            />
            <span className="input-hint">Optional: for reproducible results</span>
          </div>

          <div className="input-group">
            <label htmlFor="enrichmentMode">
              Enrichment Mode <span className="required">*</span>
            </label>
            <div className="toggle-switch">
              <input
                id="enrichmentMode"
                type="checkbox"
                checked={enrichmentMode === 'ai'}
                onChange={(e) => setEnrichmentMode(e.target.checked ? 'ai' : 'offline')}
                disabled={pipelineRunning}
              />
              <label htmlFor="enrichmentMode" className="toggle-label">
                <span className="toggle-slider"></span>
                <span className="toggle-text">
                  {enrichmentMode === 'offline' ? '⚡ Offline (Fast)' : '🤖 AI (Accurate)'}
                </span>
              </label>
            </div>
            <span className="input-hint">
              {enrichmentMode === 'offline' 
                ? 'Fast mode - uses predefined data' 
                : 'Slow mode - uses AI for enrichment (more accurate)'}
            </span>
          </div>

          <div className="input-group">
            <label htmlFor="runMode">
              Run Mode <span className="required">*</span>
            </label>
            <div className="toggle-switch">
              <input
                id="runMode"
                type="checkbox"
                checked={!dryRun}
                onChange={(e) => setDryRun(!e.target.checked)}
                disabled={pipelineRunning}
              />
              <label htmlFor="runMode" className="toggle-label">
                <span className="toggle-slider"></span>
                <span className="toggle-text">
                  {dryRun ? '🧪 Dry Run' : '🚀 Live'}
                </span>
              </label>
            </div>
            <span className="input-hint">
              {dryRun ? 'Testing mode - no emails sent' : '⚠️ LIVE - will send actual emails'}
            </span>
          </div>
        </div>

        <button 
          className="pipeline-button"
          onClick={handleRunPipeline}
          disabled={pipelineRunning || !numLeads || numLeads < 1 || numLeads > 250}
        >
          {pipelineRunning ? '⏳ Running Pipeline...' : '🚀 Run Pipeline'}
        </button>

        {/* Workflow Animation */}
        {workflowSteps.length > 0 && (
          <div className="pipeline-animation">
            <div className="workflow-steps">
              {workflowSteps.map((step) => (
                <div 
                  key={step.id} 
                  className={`workflow-step ${step.status}`}
                >
                  <div className="step-icon">{step.icon}</div>
                  <div className="step-name">{step.name}</div>
                  <div className="step-status">
                    {step.status === 'completed' ? '✓ Complete' : 
                     step.status === 'active' ? '⏳ Processing...' : 
                     'Pending'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Live Metrics */}
      {metrics && (
        <div className="live-metrics">
          <h2>
            <span className="live-indicator"></span>
            {dryRun ? 'Dry Run Metrics' : 'Live Metrics'}
          </h2>
          
          {dryRun ? (
            /* Dry Run Mode - Show messages stored with loading bar */
            <div className="dry-run-metrics">
              <div className="metric-card primary">
                <div className="metric-label">Messages Stored</div>
                <div className="metric-value">{metrics.messagesSent}</div>
                <div className="metric-sublabel">Saved to storage</div>
              </div>
              
              {/* Only show progress bar if not at 100% */}
              {metrics.messagesApproved > 0 && metrics.messagesSent < metrics.messagesApproved && (
                <div className="progress-section">
                  <div className="progress-info">
                    <span>Storing Messages</span>
                    <span className="progress-percentage">
                      {Math.round((metrics.messagesSent / metrics.messagesApproved) * 100)}%
                    </span>
                  </div>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{
                        width: `${(metrics.messagesSent / metrics.messagesApproved) * 100}%`
                      }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Live Mode - Show full metrics */
            <div className="metrics-grid">
              <div className="metric-card warning">
                <div className="metric-label">Messages Sent</div>
                <div className="metric-value">{metrics.messagesSent}</div>
                <div className="metric-sublabel">Delivered successfully</div>
              </div>
              
              <div className="metric-card info">
                <div className="metric-label">Messages Pending</div>
                <div className="metric-value">{stats?.summary?.messages_pending || 0}</div>
                <div className="metric-sublabel">Awaiting delivery</div>
              </div>
              
              <div className="metric-card" style={{borderColor: 'rgba(239, 68, 68, 0.3)'}}>
                <div className="metric-label">Messages Failed</div>
                <div className="metric-value" style={{color: '#ef4444'}}>
                  {stats?.summary?.messages_failed || 0}
                </div>
                <div className="metric-sublabel">Delivery failed</div>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  )
}

export default Dashboard
