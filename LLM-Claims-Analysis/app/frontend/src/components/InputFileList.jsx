import { useState, useEffect } from 'react'
import axios from 'axios'

function InputFileList({ configFile, onSelectFile, selectedFile, refreshTrigger }) {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [inputFolder, setInputFolder] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetchFiles()
  }, [configFile, refreshTrigger])

  const fetchFiles = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get(`/api/input-files?config=${configFile}`)
      setFiles(response.data.files)
      setInputFolder(response.data.input_folder)
      setLoading(false)
    } catch (err) {
      setError('Failed to load input files: ' + err.message)
      setLoading(false)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDate = (isoDate) => {
    const date = new Date(isoDate)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const filteredFiles = files.filter(file => 
    file.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-cas-gray-900 dark:text-gray-100">Input Files</h3>
        <button
          onClick={fetchFiles}
          className="p-2 text-cas-gray-600 dark:text-gray-400 hover:text-cas-teal-600 dark:hover:text-cas-teal-400 transition-colors rounded-lg hover:bg-cas-teal-50 dark:hover:bg-cas-teal-900/30"
          title="Refresh file list"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Search Box */}
      {files.length > 0 && (
        <div className="mb-3">
          <div className="relative">
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 pl-9 text-sm border border-cas-gray-300 dark:border-cas-gray-600 dark:bg-cas-gray-700 dark:text-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cas-teal-500 focus:border-cas-teal-500"
            />
            <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-cas-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>
      )}

      {inputFolder && (
        <div className="text-xs text-cas-gray-500 dark:text-gray-400 mb-3 bg-cas-gray-50 dark:bg-cas-gray-700/50 px-3 py-2 rounded">
          <span className="font-medium">Folder:</span> {inputFolder}
        </div>
      )}

      <div className="overflow-y-auto border border-cas-gray-200 dark:border-cas-gray-700 rounded-lg max-h-80">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-cas-gray-500 dark:text-gray-400">Loading files...</div>
          </div>
        ) : error ? (
          <div className="p-4">
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded text-sm">
              {error}
            </div>
          </div>
        ) : files.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center text-cas-gray-500 dark:text-gray-400">
              <svg className="w-12 h-12 mx-auto mb-3 text-cas-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-sm">No JSON files found</p>
              <p className="text-xs mt-1">Add files to {inputFolder}</p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-cas-gray-200 dark:divide-cas-gray-700">
            {filteredFiles.map((file) => (
              <button
                key={file.name}
                onClick={() => onSelectFile(file.name)}
                className={`w-full px-4 py-3 text-left hover:bg-cas-teal-50 dark:hover:bg-cas-teal-900/20 transition-colors group ${
                  selectedFile === file.name ? 'bg-cas-teal-100 dark:bg-cas-teal-900/40 border-l-4 border-cas-teal-600' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* JSON Icon */}
                  <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
                    selectedFile === file.name ? 'bg-cas-teal-600' : 'bg-cas-gray-200 dark:bg-cas-gray-700 group-hover:bg-cas-teal-500'
                  } transition-colors`}>
                    <svg className={`w-4 h-4 ${selectedFile === file.name ? 'text-white' : 'text-cas-gray-600 dark:text-gray-400 group-hover:text-white'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm text-cas-gray-900 dark:text-gray-100 truncate" title={file.name}>
                      {file.name}
                    </div>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-cas-gray-100 dark:bg-cas-gray-700 text-cas-gray-700 dark:text-gray-300">
                        {formatFileSize(file.size)}
                      </span>
                      <span className="text-xs text-cas-gray-500 dark:text-gray-400">
                        {formatDate(file.modified)}
                      </span>
                    </div>
                  </div>

                  {/* Selected Checkmark */}
                  {selectedFile === file.name && (
                    <div className="flex-shrink-0">
                      <svg className="w-5 h-5 text-cas-teal-600 dark:text-cas-teal-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {files.length > 0 && (
        <div className="mt-1 px-3 py-1 bg-cas-gray-50 dark:bg-cas-gray-700/50 rounded text-xs text-cas-gray-600 dark:text-gray-400 text-center border border-cas-gray-200 dark:border-cas-gray-700">
          {filteredFiles.length} of {files.length} file{files.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}

export default InputFileList
