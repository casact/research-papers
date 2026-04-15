import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { useLogStream } from '../hooks/useLogStream'

function LogsModal({ isOpen, onClose, job, onRefresh }) {
  const [jobDetails, setJobDetails] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const logsRef = useRef(null)

  // Use streaming for running jobs
  const isStreaming = job?.status === 'running'
  const { logs: streamedLogs, isConnected, error: streamError } = useLogStream(job?.id, isStreaming && isOpen)

  useEffect(() => {
    if (isOpen && job) {
      fetchJobDetails()
    }
  }, [isOpen, job])

  const fetchJobDetails = async () => {
    if (!job) return
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get(`/api/jobs/${job.id}`)
      setJobDetails(response.data)
      setLoading(false)
    } catch (err) {
      setError('Failed to load job details: ' + err.message)
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    fetchJobDetails()
    if (onRefresh) onRefresh()
  }

  const formatCost = (cost) => {
    if (cost === 0) return '$0.00'
    if (cost < 0.01) return '<$0.01'
    return `$${cost.toFixed(4)}`
  }

  const downloadLogs = () => {
    if (!jobDetails) return

    const costInfo = jobDetails.cost_info || {}
    const logContent = `Job: ${jobDetails.input_file}
Status: ${jobDetails.status}
Start Time: ${jobDetails.start_time}
End Time: ${jobDetails.end_time || 'Running'}
Exit Code: ${jobDetails.exit_code !== null ? jobDetails.exit_code : 'N/A'}
Total Cost: ${formatCost(costInfo.total_cost || 0)}
Tokens Used: ${costInfo.total_tokens || 0}
API Calls: ${costInfo.api_calls || 0}
Encounters Processed: ${costInfo.encounters_processed || 0}

=== LOGS ===
${jobDetails.logs || '(no output yet)'}`

    const blob = new Blob([logContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${jobDetails.input_file.replace('.json', '')}_logs.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Display either streamed logs (for running) or final logs (for completed/failed)
  const displayLogs = isStreaming ? streamedLogs : (jobDetails?.logs || '')
  const displayError = error || streamError

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-cas-gray-800 rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-cas-gray-200 dark:border-cas-gray-700">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-cas-gray-900 dark:text-gray-100">Job Logs</h2>
              {/* Live Streaming Indicator */}
              {isStreaming && (
                <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700">
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></div>
                  <span className="text-xs font-medium text-green-700 dark:text-green-300">
                    {isConnected ? 'Live' : 'Connecting...'}
                  </span>
                </div>
              )}
            </div>
            {jobDetails && (
              <>
                <div className="flex items-center gap-4 mt-2 text-sm text-cas-gray-600 dark:text-gray-400">
                  <span><strong>File:</strong> {jobDetails.input_file}</span>
                  <span><strong>Status:</strong> {jobDetails.status}</span>
                  {jobDetails.exit_code !== null && (
                    <span><strong>Exit Code:</strong> {jobDetails.exit_code}</span>
                  )}
                </div>
                {jobDetails.cost_info && (
                  <div className="flex items-center gap-4 mt-1 text-xs text-cas-gray-500 dark:text-gray-400">
                    <span><strong>Cost:</strong> {formatCost(jobDetails.cost_info.total_cost)}</span>
                    {jobDetails.cost_info.total_tokens > 0 && (
                      <span><strong>Tokens:</strong> {jobDetails.cost_info.total_tokens.toLocaleString()}</span>
                    )}
                    {jobDetails.cost_info.api_calls > 0 && (
                      <span><strong>API Calls:</strong> {jobDetails.cost_info.api_calls}</span>
                    )}
                    {jobDetails.cost_info.encounters_processed > 0 && (
                      <span><strong>Encounters:</strong> {jobDetails.cost_info.encounters_processed}</span>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-cas-gray-500 dark:text-gray-400 hover:text-cas-gray-700 dark:hover:text-gray-200 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Actions Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cas-gray-200 dark:border-cas-gray-700 bg-cas-gray-50 dark:bg-cas-gray-700/50">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-cas-gray-700 dark:text-gray-300">
              {isStreaming ? 'Live Logs' : 'Combined Logs'}
            </h3>
            {streamError && (
              <span className="text-xs text-red-600 dark:text-red-400">
                ({streamError})
              </span>
            )}
          </div>
          <div className="flex gap-2">
            {jobDetails && jobDetails.status === 'running' && !isStreaming && (
              <button
                onClick={handleRefresh}
                className="px-3 py-1 text-sm bg-cas-gray-100 dark:bg-cas-gray-700 text-cas-gray-700 dark:text-gray-300 rounded hover:bg-cas-gray-200 dark:hover:bg-cas-gray-600 transition-colors flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            )}
            <button
              onClick={downloadLogs}
              disabled={!jobDetails}
              className="px-3 py-1 text-sm bg-cas-gray-100 dark:bg-cas-gray-700 text-cas-gray-700 dark:text-gray-300 rounded hover:bg-cas-gray-200 dark:hover:bg-cas-gray-600 transition-colors flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-h-0 flex flex-col p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-cas-gray-500 dark:text-gray-400">Loading logs...</div>
            </div>
          ) : displayError ? (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded">
              {displayError}
            </div>
          ) : (
            <div
              ref={logsRef}
              className="flex-1 min-h-0 overflow-y-auto bg-cas-gray-900 dark:bg-black rounded-lg p-4"
            >
              <pre className="text-xs text-green-400 dark:text-green-300 font-mono whitespace-pre-wrap">
                {displayLogs || '(no output yet)'}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-cas-gray-200 dark:border-cas-gray-700 bg-cas-gray-50 dark:bg-cas-gray-700/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-cas-blue-600 dark:bg-cas-blue-500 text-white rounded-md hover:bg-cas-blue-700 dark:hover:bg-cas-blue-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default LogsModal
