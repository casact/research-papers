function JobCard({ job, onViewLogs, onDelete }) {
  const getStatusBadge = () => {
    const statusConfig = {
      running: {
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        text: 'text-blue-800 dark:text-blue-300',
        label: 'Running',
        icon: (
          <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        )
      },
      completed: {
        bg: 'bg-green-100 dark:bg-green-900/30',
        text: 'text-green-800 dark:text-green-300',
        label: 'Completed',
        icon: (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )
      },
      failed: {
        bg: 'bg-red-100 dark:bg-red-900/30',
        text: 'text-red-800 dark:text-red-300',
        label: 'Failed',
        icon: (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )
      }
    }

    const config = statusConfig[job.status] || statusConfig.running
    return (
      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.icon}
        {config.label}
      </span>
    )
  }

  const formatTime = (isoDate) => {
    if (!isoDate) return 'N/A'
    const date = new Date(isoDate)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const getElapsedTime = () => {
    const start = new Date(job.start_time)
    const end = job.end_time ? new Date(job.end_time) : new Date()
    const elapsed = Math.floor((end - start) / 1000) // seconds

    if (elapsed < 60) return `${elapsed}s`
    if (elapsed < 3600) return `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    return `${Math.floor(elapsed / 3600)}h ${Math.floor((elapsed % 3600) / 60)}m`
  }

  const formatCost = (cost) => {
    if (cost === 0) return '$0.00'
    if (cost < 0.01) return '<$0.01'
    return `$${cost.toFixed(4)}`
  }

  const formatNumber = (num) => {
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'k'
    }
    return num.toString()
  }

  return (
    <div className="bg-white dark:bg-cas-gray-800 border border-cas-gray-200 dark:border-cas-gray-700 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-cas-gray-900 dark:text-gray-100 truncate" title={job.input_file}>
            {job.input_file}
          </h4>
          <p className="text-xs text-cas-gray-500 dark:text-gray-400 mt-1">
            Started: {formatTime(job.start_time)}
          </p>
        </div>
        <div className="ml-3">
          {getStatusBadge()}
        </div>
      </div>

      {/* Timing and Cost */}
      <div className="space-y-1 mb-3">
        <div className="text-xs text-cas-gray-600 dark:text-gray-400">
          <span className="font-medium">Duration:</span> {getElapsedTime()}
        </div>
        {job.cost_info && (
          <>
            <div className="text-xs text-cas-gray-600 dark:text-gray-400">
              <span className="font-medium">Cost:</span> {formatCost(job.cost_info.total_cost)}
              {job.cost_info.total_cost === 0 && job.status === 'completed' && (
                <span className="ml-1 text-cas-blue-600 dark:text-cas-blue-400">(dry run)</span>
              )}
            </div>
            {job.cost_info.encounters_processed > 0 && (
              <div className="text-xs text-cas-gray-600 dark:text-gray-400">
                <span className="font-medium">Encounters:</span> {job.cost_info.encounters_processed}
              </div>
            )}
            {job.cost_info.total_tokens > 0 && (
              <div className="text-xs text-cas-gray-600 dark:text-gray-400">
                <span className="font-medium">Tokens:</span> {formatNumber(job.cost_info.total_tokens)}
              </div>
            )}
          </>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onViewLogs(job)}
          className="flex-1 px-3 py-2 bg-cas-blue-50 dark:bg-cas-blue-900/30 text-cas-blue-700 dark:text-cas-blue-300 rounded-md hover:bg-cas-blue-100 dark:hover:bg-cas-blue-900/50 transition-colors text-sm font-medium flex items-center justify-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          View Logs
        </button>

        {(job.status === 'completed' || job.status === 'failed') && (
          <button
            onClick={() => onDelete(job.id)}
            className="px-3 py-2 bg-red-50 text-red-700 rounded-md hover:bg-red-100 transition-colors text-sm font-medium"
            title="Delete job"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}

export default JobCard
