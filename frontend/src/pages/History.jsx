import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import '../styles/History.css'

function History() {
  const [pipelineRuns, setPipelineRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [historyRecords, setHistoryRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterChannel, setFilterChannel] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  // Fetch pipeline runs on mount
  useEffect(() => {
    fetchPipelineRuns()
  }, [])

  const fetchPipelineRuns = async () => {
    try {
      setLoading(true)
      const data = await api.getPipelineRuns({ limit: 50 })
      setPipelineRuns(data.runs || [])
      setError(null)
    } catch (err) {
      setError('Failed to load pipeline runs')
      console.error('Error fetching pipeline runs:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchRunDetails = async (runId) => {
    try {
      setDetailsLoading(true)
      const data = await api.getHistory({ pipeline_run_id: runId, limit: 1000 })
      setHistoryRecords(data.records || [])
      setSelectedRun(runId)
      setError(null)
    } catch (err) {
      setError('Failed to load run details')
      console.error('Error fetching run details:', err)
    } finally {
      setDetailsLoading(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusBadge = (status) => {
    const statusColors = {
      'SENT': 'success',
      'APPROVED': 'info',
      'PENDING': 'warning',
      'FAILED': 'danger',
      'DELIVERED': 'success'
    }
    return statusColors[status] || 'default'
  }

  const getChannelIcon = (channel) => {
    return channel === 'email' ? '📧' : channel === 'linkedin' ? '💼' : '📱'
  }

  // Filter history records
  const filteredRecords = historyRecords.filter(record => {
    const matchesSearch = 
      record.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      record.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      record.company_name?.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesChannel = filterChannel === 'all' || record.channel === filterChannel
    const matchesStatus = filterStatus === 'all' || record.message_status === filterStatus

    return matchesSearch && matchesChannel && matchesStatus
  })

  // Calculate run statistics
  const getRunStats = (runId) => {
    const records = historyRecords.filter(r => r.pipeline_run_id === runId)
    const totalMessages = records.length
    const sentMessages = records.filter(r => r.message_status === 'SENT').length
    const approvedMessages = records.filter(r => r.message_status === 'APPROVED').length
    const emailMessages = records.filter(r => r.channel === 'email').length
    const linkedinMessages = records.filter(r => r.channel === 'linkedin').length

    return {
      totalMessages,
      sentMessages,
      approvedMessages,
      emailMessages,
      linkedinMessages,
      successRate: totalMessages > 0 ? ((sentMessages / totalMessages) * 100).toFixed(1) : 0
    }
  }

  if (loading) {
    return (
      <div className="history-page">
        <div className="loading">
          <div className="loading-spinner"></div>
          Loading history...
        </div>
      </div>
    )
  }

  return (
    <div className="history-page">
      <header className="history-header">
        <h1>📜 Pipeline History</h1>
        <p>View past pipeline runs and their results</p>
      </header>

      {error && <div className="error">{error}</div>}

      {/* Pipeline Runs List */}
      <section className="runs-section">
        <h2>Pipeline Runs</h2>
        {pipelineRuns.length === 0 ? (
          <div className="empty-state">
            <p>No pipeline runs found</p>
            <p className="empty-state-hint">Run your first pipeline to see history here</p>
          </div>
        ) : (
          <div className="runs-grid">
            {pipelineRuns.map((run) => {
              const stats = selectedRun === run.pipeline_run_id ? getRunStats(run.pipeline_run_id) : null
              return (
                <div
                  key={run.pipeline_run_id}
                  className={`run-card ${selectedRun === run.pipeline_run_id ? 'active' : ''}`}
                  onClick={() => fetchRunDetails(run.pipeline_run_id)}
                >
                  <div className="run-header">
                    <span className="run-id">Run #{run.pipeline_run_id.slice(0, 8)}</span>
                    <span className={`run-mode ${run.dry_run ? 'dry-run' : 'live'}`}>
                      {run.dry_run ? '🧪 Dry Run' : '🚀 Live'}
                    </span>
                  </div>
                  <div className="run-date">{formatDate(run.created_at)}</div>
                  <div className="run-metrics">
                    <div className="run-metric">
                      <span className="metric-label">Total</span>
                      <span className="metric-value">{run.total_records}</span>
                    </div>
                    <div className="run-metric">
                      <span className="metric-label">Leads</span>
                      <span className="metric-value">{run.unique_leads}</span>
                    </div>
                    <div className="run-metric">
                      <span className="metric-label">Messages</span>
                      <span className="metric-value">{run.unique_messages}</span>
                    </div>
                  </div>
                  {stats && (
                    <div className="run-success-rate">
                      Success Rate: {stats.successRate}%
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Run Details */}
      {selectedRun && (
        <section className="details-section">
          <div className="details-header">
            <h2>Run Details</h2>
            <div className="filters">
              <input
                type="text"
                placeholder="🔍 Search by name, email, or company..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-input"
              />
              <select
                value={filterChannel}
                onChange={(e) => setFilterChannel(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Channels</option>
                <option value="email">📧 Email</option>
                <option value="linkedin">💼 LinkedIn</option>
              </select>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Statuses</option>
                <option value="SENT">Sent</option>
                <option value="APPROVED">Approved</option>
                <option value="PENDING">Pending</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>
          </div>

          {detailsLoading ? (
            <div className="loading">
              <div className="loading-spinner"></div>
              Loading details...
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className="empty-state">
              <p>No records found</p>
            </div>
          ) : (
            <>
              <div className="results-count">
                Showing {filteredRecords.length} of {historyRecords.length} records
              </div>
              <div className="history-table-container">
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Lead</th>
                      <th>Company</th>
                      <th>Role</th>
                      <th>Channel</th>
                      <th>Variant</th>
                      <th>Status</th>
                      <th>Confidence</th>
                      <th>Sent At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRecords.map((record, index) => (
                      <tr key={`${record.id}-${index}`}>
                        <td>
                          <div className="lead-info">
                            <div className="lead-name">{record.full_name}</div>
                            <div className="lead-email">{record.email || 'N/A'}</div>
                          </div>
                        </td>
                        <td>
                          <div className="company-info">
                            <div className="company-name">{record.company_name}</div>
                            <div className="company-industry">{record.industry}</div>
                          </div>
                        </td>
                        <td>{record.role}</td>
                        <td>
                          <span className="channel-badge">
                            {getChannelIcon(record.channel)} {record.channel}
                          </span>
                        </td>
                        <td>
                          <span className="variant-badge">{record.variant || 'N/A'}</span>
                        </td>
                        <td>
                          <span className={`status-badge ${getStatusBadge(record.message_status)}`}>
                            {record.message_status}
                          </span>
                        </td>
                        <td>
                          <span className="confidence-score">
                            {record.confidence_score ? `${record.confidence_score}%` : 'N/A'}
                          </span>
                        </td>
                        <td>{formatDate(record.sent_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  )
}

export default History
