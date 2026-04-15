import { useState, useEffect } from 'react'
import axios from 'axios'
import ConfigModal from '../components/ConfigModal'
import InputFileList from '../components/InputFileList'
import ScriptArgumentsForm from '../components/ScriptArgumentsForm'
import JsonPreviewModal from '../components/JsonPreviewModal'
import JobCard from '../components/JobCard'
import LogsModal from '../components/LogsModal'
import ReadmeModal from '../components/ReadmeModal'
import Toast from '../components/Toast'

function ProcessBundle() {
  const configFile = '1_data-process_fhir_bundle.yaml'

  // State management
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false)
  const [isReadmeModalOpen, setIsReadmeModalOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [scriptArgs, setScriptArgs] = useState({})
  const [jobs, setJobs] = useState([])
  const [showPreview, setShowPreview] = useState(false)
  const [showLogs, setShowLogs] = useState(false)
  const [selectedJob, setSelectedJob] = useState(null)
  const [configChanged, setConfigChanged] = useState(0)
  const [executing, setExecuting] = useState(false)
  const [jobsFilter, setJobsFilter] = useState('all') // all, running, completed, failed
  const [toast, setToast] = useState(null)

  const fetchJobs = async () => {
    try {
      const response = await axios.get('/api/jobs')
      const newJobs = response.data.jobs
      
      // Check for newly completed jobs
      jobs.forEach(oldJob => {
        const newJob = newJobs.find(j => j.id === oldJob.id)
        if (oldJob.status === 'running' && newJob && newJob.status === 'completed') {
          setToast({ message: `Job "${oldJob.input_file}" completed successfully!`, type: 'success' })
        } else if (oldJob.status === 'running' && newJob && newJob.status === 'failed') {
          setToast({ message: `Job "${oldJob.input_file}" failed!`, type: 'error' })
        }
      })
      
      setJobs(newJobs)
    } catch (err) {
      console.error('Failed to fetch jobs:', err)
    }
  }

  // Poll for job updates
  useEffect(() => {
    fetchJobs()

    const interval = setInterval(() => {
      fetchJobs()
    }, 1000) // Poll every second

    return () => clearInterval(interval)
  }, []) // Empty dependency array - only run once on mount

  const handleConfigClose = () => {
    setIsConfigModalOpen(false)
    setConfigChanged(prev => prev + 1) // Trigger file list refresh
  }

  const handleExecute = async () => {
    if (!selectedFile) {
      setToast({ message: 'Please select an input file', type: 'error' })
      return
    }

    setExecuting(true)
    try {
      const response = await axios.post('/api/execute-script', {
        scriptType: 'process_bundle',
        inputFile: selectedFile,
        args: scriptArgs,
        config: configFile
      })

      // Add new job to list
      await fetchJobs()

      // Show success message
      setToast({ message: `Job started successfully for ${selectedFile}`, type: 'success' })
    } catch (err) {
      setToast({ message: 'Failed to start job: ' + err.message, type: 'error' })
    } finally {
      setExecuting(false)
    }
  }

  const handleViewLogs = (job) => {
    setSelectedJob(job)
    setShowLogs(true)
  }

  const handleDeleteJob = async (jobId) => {
    if (!confirm('Are you sure you want to delete this job?')) return

    try {
      await axios.delete(`/api/jobs/${jobId}`)
      await fetchJobs()
      setToast({ message: 'Job deleted successfully', type: 'info' })
    } catch (err) {
      setToast({ message: 'Failed to delete job: ' + err.message, type: 'error' })
    }
  }

  const runningJobsCount = jobs.filter(j => j.status === 'running').length

  // Determine current step
  const getCurrentStep = () => {
    if (!selectedFile) return 1
    if (Object.keys(scriptArgs).length === 0) return 2
    return 3
  }

  const currentStep = getCurrentStep()

  // Filter jobs based on selected filter
  const getFilteredJobs = () => {
    switch (jobsFilter) {
      case 'running':
        return jobs.filter(j => j.status === 'running')
      case 'completed':
        return jobs.filter(j => j.status === 'completed')
      case 'failed':
        return jobs.filter(j => j.status === 'failed')
      default:
        return jobs
    }
  }

  const filteredJobs = getFilteredJobs()
  const completedCount = jobs.filter(j => j.status === 'completed').length
  const failedCount = jobs.filter(j => j.status === 'failed').length

  const handleDeleteAll = async (status) => {
    const jobsToDelete = jobs.filter(j => j.status === status)
    if (jobsToDelete.length === 0) return
    
    if (!confirm(`Are you sure you want to delete all ${status} jobs? (${jobsToDelete.length} jobs)`)) return

    try {
      await Promise.all(jobsToDelete.map(job => axios.delete(`/api/jobs/${job.id}`)))
      await fetchJobs()
      setToast({ message: `Deleted ${jobsToDelete.length} ${status} job(s)`, type: 'info' })
    } catch (err) {
      setToast({ message: 'Failed to delete jobs: ' + err.message, type: 'error' })
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e) => {
      // Enter to start processing (when not in input/textarea)
      if (e.key === 'Enter' && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        if (selectedFile && !executing) {
          handleExecute()
        }
      }
      // Escape to close modals
      if (e.key === 'Escape') {
        if (isConfigModalOpen) setIsConfigModalOpen(false)
        if (isReadmeModalOpen) setIsReadmeModalOpen(false)
        if (showPreview) setShowPreview(false)
        if (showLogs) setShowLogs(false)
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [selectedFile, executing, isConfigModalOpen, isReadmeModalOpen, showPreview, showLogs])

  return (
    <div className="container mx-auto px-4 pt-4 pb-8 max-w-7xl">
      {/* Workflow Progress Indicator */}
      <div className="mb-8 bg-white dark:bg-cas-gray-800 rounded-lg p-6 shadow-sm border border-cas-gray-200 dark:border-cas-gray-700">
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          {/* Step 1 */}
          <div className="flex flex-col items-center flex-1">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm mb-2 transition-all ${
              currentStep >= 1 
                ? 'bg-cas-teal-600 text-white ring-4 ring-cas-teal-100 dark:ring-cas-teal-900/50' 
                : 'bg-cas-gray-200 dark:bg-cas-gray-700 text-cas-gray-500 dark:text-gray-400'
            }`}>
              {selectedFile ? '✓' : '1'}
            </div>
            <span className={`text-sm font-medium ${currentStep >= 1 ? 'text-cas-teal-700 dark:text-cas-teal-400' : 'text-cas-gray-500 dark:text-gray-400'}`}>
              Select File
            </span>
          </div>

          {/* Connector */}
          <div className={`h-1 flex-1 mx-4 rounded transition-all ${
            currentStep >= 2 ? 'bg-cas-teal-600' : 'bg-cas-gray-200 dark:bg-cas-gray-700'
          }`}></div>

          {/* Step 2 */}
          <div className="flex flex-col items-center flex-1">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm mb-2 transition-all ${
              currentStep >= 2 
                ? 'bg-cas-teal-600 text-white ring-4 ring-cas-teal-100 dark:ring-cas-teal-900/50' 
                : 'bg-cas-gray-200 dark:bg-cas-gray-700 text-cas-gray-500 dark:text-gray-400'
            }`}>
              2
            </div>
            <span className={`text-sm font-medium ${currentStep >= 2 ? 'text-cas-teal-700 dark:text-cas-teal-400' : 'text-cas-gray-500 dark:text-gray-400'}`}>
              Set Arguments
            </span>
          </div>

          {/* Connector */}
          <div className={`h-1 flex-1 mx-4 rounded transition-all ${
            currentStep >= 3 ? 'bg-cas-teal-600' : 'bg-cas-gray-200 dark:bg-cas-gray-700'
          }`}></div>

          {/* Step 3 */}
          <div className="flex flex-col items-center flex-1">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm mb-2 transition-all ${
              currentStep >= 3 
                ? 'bg-cas-teal-600 text-white ring-4 ring-cas-teal-100 dark:ring-cas-teal-900/50' 
                : 'bg-cas-gray-200 dark:bg-cas-gray-700 text-cas-gray-500 dark:text-gray-400'
            }`}>
              3
            </div>
            <span className={`text-sm font-medium ${currentStep >= 3 ? 'text-cas-teal-700 dark:text-cas-teal-400' : 'text-cas-gray-500 dark:text-gray-400'}`}>
              Start Processing
            </span>
          </div>
        </div>
      </div>

      {/* Configure Button */}
      <div className="flex justify-center mb-6 gap-3">
        <button
          onClick={() => setIsConfigModalOpen(true)}
          className="px-12 py-3 bg-gradient-to-r from-cas-teal-600 to-cas-teal-700 dark:from-cas-teal-500 dark:to-cas-teal-600 text-white rounded-lg hover:from-cas-teal-700 hover:to-cas-teal-800 dark:hover:from-cas-teal-600 dark:hover:to-cas-teal-700 transition-all font-medium text-lg flex-1 max-w-md shadow-md hover:shadow-lg"
        >
          Configure Settings
        </button>
        <button
          onClick={() => setIsReadmeModalOpen(true)}
          className="px-4 py-3 bg-white dark:bg-cas-gray-800 text-cas-navy-700 dark:text-gray-300 rounded-lg hover:bg-cas-teal-50 dark:hover:bg-cas-teal-900/30 hover:text-cas-teal-700 dark:hover:text-cas-teal-400 hover:border-cas-teal-500 transition-all font-medium border-2 border-cas-navy-200 dark:border-cas-gray-600 shadow-sm"
          title="View Documentation"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Left Column - File List */}
        <div className="lg:col-span-1 bg-white dark:bg-cas-gray-800 rounded-lg p-6 shadow-sm">
          {!selectedFile && (
            <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg flex items-start gap-2">
              <svg className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-green-800 dark:text-green-300">
                <strong>Please select a file</strong> to continue
              </p>
            </div>
          )}
          <InputFileList
            configFile={configFile}
            onSelectFile={setSelectedFile}
            selectedFile={selectedFile}
            refreshTrigger={configChanged}
          />
        </div>

        {/* Right Column - Arguments and Actions */}
        <div className="lg:col-span-2 bg-white dark:bg-cas-gray-800 border border-cas-gray-200 dark:border-cas-gray-700 rounded-lg p-6 shadow-sm">
          <ScriptArgumentsForm onChange={setScriptArgs} />

          {/* Action Buttons */}
          <div className="flex gap-3 mt-6 pt-6 border-t border-cas-gray-200 dark:border-cas-gray-700">
            <button
              onClick={() => setShowPreview(true)}
              disabled={!selectedFile}
              className="flex-1 px-4 py-3 bg-cas-gray-100 dark:bg-cas-gray-700 text-cas-gray-700 dark:text-gray-300 rounded-lg hover:bg-cas-gray-200 dark:hover:bg-cas-gray-600 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Preview Input
            </button>

            <button
              onClick={handleExecute}
              disabled={!selectedFile || executing}
              className="flex-1 px-4 py-3 bg-gradient-to-r from-cas-teal-600 to-cas-teal-700 dark:from-cas-teal-500 dark:to-cas-teal-600 text-white rounded-lg hover:from-cas-teal-700 hover:to-cas-teal-800 dark:hover:from-cas-teal-600 dark:hover:to-cas-teal-700 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-md hover:shadow-lg disabled:shadow-sm"
            >
              {executing ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Starting...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Start Processing
                </>
              )}
            </button>
          </div>

          {selectedFile && (
            <div className="mt-4 p-3 bg-cas-teal-50 dark:bg-cas-teal-900/30 border border-cas-teal-200 dark:border-cas-teal-700 rounded-lg">
              <p className="text-sm text-cas-teal-800 dark:text-cas-teal-300">
                <strong>Selected file:</strong> {selectedFile}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Jobs Section */}
      <div className="bg-white dark:bg-cas-gray-800 border border-cas-gray-200 dark:border-cas-gray-700 rounded-lg shadow-sm overflow-hidden">
        {/* Jobs Header with Tabs */}
        <div className="border-b border-cas-gray-200 dark:border-cas-gray-700 bg-gradient-to-r from-cas-gray-50 dark:from-cas-gray-800 to-white dark:to-cas-gray-800">
          <div className="flex items-center justify-between p-6 pb-0">
            <h2 className="text-2xl font-bold text-cas-gray-900 dark:text-gray-100">Jobs</h2>
            <div className="flex items-center gap-2">
              {completedCount > 0 && (
                <button
                  onClick={() => handleDeleteAll('completed')}
                  className="px-3 py-1.5 text-xs bg-cas-gray-100 dark:bg-cas-gray-700 text-cas-gray-700 dark:text-gray-300 rounded hover:bg-cas-gray-200 dark:hover:bg-cas-gray-600 transition-colors"
                  title="Delete all completed jobs"
                >
                  Clear Completed
                </button>
              )}
              <button
                onClick={fetchJobs}
                className="p-2 text-cas-gray-600 hover:text-cas-teal-600 transition-colors rounded-lg hover:bg-cas-teal-50"
                title="Refresh jobs"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex gap-2 px-6 pt-4">
            <button
              onClick={() => setJobsFilter('all')}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-all ${
                jobsFilter === 'all'
                  ? 'bg-white text-cas-teal-700 border-t-2 border-x border-cas-teal-500'
                  : 'text-cas-gray-600 hover:text-cas-gray-900 hover:bg-cas-gray-100'
              }`}
            >
              All ({jobs.length})
            </button>
            <button
              onClick={() => setJobsFilter('running')}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-all ${
                jobsFilter === 'running'
                  ? 'bg-white text-cas-teal-700 border-t-2 border-x border-cas-teal-500'
                  : 'text-cas-gray-600 hover:text-cas-gray-900 hover:bg-cas-gray-100'
              }`}
            >
              Running ({runningJobsCount})
            </button>
            <button
              onClick={() => setJobsFilter('completed')}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-all ${
                jobsFilter === 'completed'
                  ? 'bg-white text-cas-teal-700 border-t-2 border-x border-cas-teal-500'
                  : 'text-cas-gray-600 hover:text-cas-gray-900 hover:bg-cas-gray-100'
              }`}
            >
              Completed ({completedCount})
            </button>
            <button
              onClick={() => setJobsFilter('failed')}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-all ${
                jobsFilter === 'failed'
                  ? 'bg-white text-cas-teal-700 border-t-2 border-x border-cas-teal-500'
                  : 'text-cas-gray-600 hover:text-cas-gray-900 hover:bg-cas-gray-100'
              }`}
            >
              Failed ({failedCount})
            </button>
          </div>
        </div>

        {/* Jobs Content */}
        <div className="p-6">
          {filteredJobs.length === 0 ? (
            <div className="text-center py-12 text-cas-gray-500">
              <svg className="w-16 h-16 mx-auto mb-4 text-cas-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="font-medium">
                {jobsFilter === 'all' 
                  ? 'No jobs yet' 
                  : `No ${jobsFilter} jobs`}
              </p>
              <p className="text-sm mt-1">
                {jobsFilter === 'all' 
                  ? 'Select a file and click "Start Processing" to begin' 
                  : `Switch to "All" to see other jobs`}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredJobs.map(job => (
                <JobCard
                  key={job.id}
                  job={job}
                  onViewLogs={handleViewLogs}
                  onDelete={handleDeleteJob}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <ConfigModal
        isOpen={isConfigModalOpen}
        onClose={handleConfigClose}
        configPath={configFile}
        title="Process FHIR Bundle Configuration"
      />

      <JsonPreviewModal
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        filename={selectedFile}
        configFile={configFile}
      />

      <LogsModal
        isOpen={showLogs}
        onClose={() => setShowLogs(false)}
        job={selectedJob}
        onRefresh={fetchJobs}
      />

      <ReadmeModal
        isOpen={isReadmeModalOpen}
        onClose={() => setIsReadmeModalOpen(false)}
      />

      {/* Toast Notification */}
      {toast && (
        <Toast
          key={toast.message + toast.type}
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Keyboard Shortcuts Hint */}
      <div className="fixed bottom-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg border border-cas-gray-200 px-4 py-2 text-xs text-cas-gray-600 hidden lg:block">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <kbd className="px-2 py-1 bg-cas-gray-100 border border-cas-gray-300 rounded text-xs font-mono">Enter</kbd>
            <span>Start</span>
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-2 py-1 bg-cas-gray-100 border border-cas-gray-300 rounded text-xs font-mono">Esc</kbd>
            <span>Close</span>
          </span>
        </div>
      </div>
    </div>
  )
}

export default ProcessBundle
