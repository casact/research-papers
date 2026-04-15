import { useState, useEffect } from 'react'
import axios from 'axios'

function ConfigModal({ isOpen, onClose, configPath, title = 'Configuration' }) {
  const [configText, setConfigText] = useState('')
  const [originalText, setOriginalText] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (isOpen && configPath) {
      fetchConfig()
    }
  }, [isOpen, configPath])

  const fetchConfig = async () => {
    setLoading(true)
    setError(null)
    setSaveSuccess(false)

    try {
      const response = await axios.get(`/api/config/${configPath}`)
      const text = response.data
      setConfigText(text)
      setOriginalText(text)
      setLoading(false)
    } catch (err) {
      setError('Failed to load configuration: ' + err.message)
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSaveSuccess(false)

    try {
      await axios.post(`/api/config/${configPath}`, { content: configText })
      setOriginalText(configText)
      setSaving(false)
      setSaveSuccess(true)

      setTimeout(() => {
        setSaveSuccess(false)
        onClose()
      }, 800)
    } catch (err) {
      setError('Failed to save configuration: ' + err.message)
      setSaving(false)
      setSaveSuccess(false)
    }
  }

  const handleCancel = () => {
    setConfigText(originalText)
    setError(null)
    setSaveSuccess(false)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50 p-4"
      onClick={handleCancel}
    >
      <div
        className="bg-white dark:bg-cas-gray-800 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center p-6 border-b border-cas-gray-200 dark:border-cas-gray-700">
          <h2 className="text-2xl font-bold text-cas-gray-900 dark:text-gray-100">{title}</h2>
          <button
            onClick={handleCancel}
            className="text-cas-gray-500 dark:text-gray-400 hover:text-cas-gray-700 dark:hover:text-gray-200 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-cas-gray-500 dark:text-gray-400">Loading configuration...</div>
            </div>
          ) : error ? (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded">{error}</div>
          ) : (
            <div className="space-y-4">
              <textarea
                value={configText}
                onChange={(e) => setConfigText(e.target.value)}
                className="w-full h-[50vh] min-h-[300px] font-mono text-sm px-3 py-2 border border-cas-gray-300 dark:border-cas-gray-600 dark:bg-cas-gray-900 dark:text-gray-200 rounded-md shadow-sm focus:outline-none focus:ring-cas-blue-500 focus:border-cas-blue-500 resize-y whitespace-pre"
                spellCheck={false}
              />
              <p className="text-xs text-cas-gray-500 dark:text-gray-400">
                Edit the configuration directly. Ensure YAML syntax stays valid before saving.
              </p>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-cas-gray-200 dark:border-cas-gray-700 bg-cas-gray-50 dark:bg-cas-gray-700/50 flex gap-3 justify-end">
          <button
            onClick={handleCancel}
            className="px-4 py-2 border border-cas-gray-300 dark:border-cas-gray-600 text-cas-gray-700 dark:text-gray-300 rounded-md hover:bg-cas-gray-100 dark:hover:bg-cas-gray-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || saveSuccess}
            className="px-4 py-2 bg-cas-blue-600 dark:bg-cas-blue-500 text-white rounded-md hover:bg-cas-blue-700 dark:hover:bg-cas-blue-600 transition-colors disabled:bg-cas-blue-600 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saving ? (
              <>
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                <span>Saving...</span>
              </>
            ) : saveSuccess ? (
              <>
                <svg
                  className="h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>Saved!</span>
              </>
            ) : (
              'Save Configuration'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfigModal
