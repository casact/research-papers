import { useState, useEffect } from 'react'
import axios from 'axios'

function JsonPreviewModal({ isOpen, onClose, filename, configFile }) {
  const [content, setContent] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [truncated, setTruncated] = useState(false)

  useEffect(() => {
    if (isOpen && filename) {
      fetchFileContent()
    }
  }, [isOpen, filename])

  const fetchFileContent = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get(`/api/preview-file?config=${configFile}&filename=${filename}`)
      setContent(response.data.content)
      setTruncated(response.data.truncated)
      setLoading(false)
    } catch (err) {
      setError('Failed to load file: ' + err.message)
      setLoading(false)
    }
  }

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
        <div className="flex justify-between items-center p-6 border-b border-cas-gray-200 dark:border-cas-gray-700 bg-gradient-to-r from-cas-navy-50 dark:from-cas-navy-900/50 to-cas-teal-50 dark:to-cas-teal-900/20">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-cas-navy-900 dark:text-gray-100">File Preview</h2>
            {filename && (
              <div className="flex items-center gap-2 mt-2">
                <svg className="w-4 h-4 text-cas-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <p className="text-sm text-cas-gray-700 dark:text-gray-300 font-medium truncate">{filename}</p>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-cas-gray-500 dark:text-gray-400 hover:text-cas-gray-700 dark:hover:text-gray-200 transition-colors p-1 rounded-lg hover:bg-white/50 dark:hover:bg-cas-gray-700/50"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 min-h-0 flex flex-col p-6 bg-cas-gray-50 dark:bg-cas-gray-900/50">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-3">
                <svg className="animate-spin h-8 w-8 text-cas-teal-600 dark:text-cas-teal-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <div className="text-cas-gray-600 dark:text-gray-400 font-medium">Loading file...</div>
              </div>
            </div>
          ) : error ? (
            <div className="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 dark:border-red-400 text-red-700 dark:text-red-300 px-4 py-3 rounded flex items-start gap-3">
              <svg className="w-5 h-5 text-red-500 dark:text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="font-semibold">Error Loading File</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          ) : content ? (
            <div className="flex-1 min-h-0 flex flex-col">
              {truncated && (
                <div className="bg-yellow-50 dark:bg-yellow-900/30 border-l-4 border-yellow-400 text-yellow-800 dark:text-yellow-300 px-4 py-3 rounded mb-4 flex items-start gap-3">
                  <svg className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <div>
                    <p className="font-semibold text-sm">Preview Truncated</p>
                    <p className="text-sm mt-1">
                      File is large and has been truncated for preview. The full file will be used during processing.
                    </p>
                  </div>
                </div>
              )}
              <div className="flex-1 min-h-0 overflow-auto bg-cas-navy-900 dark:bg-black rounded-lg border border-cas-gray-300 dark:border-cas-gray-700 shadow-inner">
                <pre className="p-5 text-sm text-green-400 dark:text-green-300 font-mono whitespace-pre-wrap leading-relaxed">
                  {JSON.stringify(content, null, 2)}
                </pre>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-cas-gray-200 dark:border-cas-gray-700 bg-white dark:bg-cas-gray-800 flex items-center justify-between">
          <div className="text-sm text-cas-gray-600 dark:text-gray-400">
            {content && (
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                JSON Format
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-cas-teal-600 text-white rounded-lg hover:bg-cas-teal-700 transition-colors font-medium shadow-sm hover:shadow-md"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default JsonPreviewModal
