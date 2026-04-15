import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

function Documents() {
  const [groups, setGroups] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [downloadError, setDownloadError] = useState(null)
  const [downloadingPath, setDownloadingPath] = useState(null)

  useEffect(() => {
    fetchDocuments()
  }, [])

  const fetchDocuments = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get('/api/documents')
      setGroups(response.data.groups || [])
      setSummary(response.data.summary || null)
    } catch (err) {
      setError(err?.response?.data?.error || err.message || 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  const totalFiles = useMemo(() => {
    if (summary?.total_files != null) {
      return summary.total_files
    }
    return groups.reduce((acc, group) => {
      const dirCount = group.directories?.reduce((dirAcc, directory) => dirAcc + (directory.files?.length || 0), 0) || 0
      return acc + dirCount
    }, 0)
  }, [groups, summary])

  const handleDownloadPdf = async (file) => {
    if (!file?.pdf_available || !file?.path) return
    setDownloadError(null)
    setDownloadingPath(file.path)
    try {
      const response = await axios.get('/api/documents/pdf', {
        params: { path: file.path },
        responseType: 'blob'
      })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      const fileStem = file.name?.replace(/\.[^/.]+$/, '') || 'document'
      a.href = url
      a.download = `${fileStem}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setDownloadError(err?.response?.data?.error || err.message || 'Unable to generate PDF for this document.')
    } finally {
      setDownloadingPath(null)
    }
  }

  const formatDateTime = (isoString) => {
    if (!isoString) return 'Unknown'
    const date = new Date(isoString)
    if (Number.isNaN(date.getTime())) return 'Unknown'
    const datePart = date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
    const timePart = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
    return `${datePart} • ${timePart}`
  }

  const formatFileSize = (bytes) => {
    if (bytes == null) return '—'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  const formatExtension = (extension) => {
    if (!extension) return ''
    return extension.replace('.', '').toUpperCase()
  }

  const renderFileRow = (file) => {
    const isDownloading = downloadingPath === file.path
    return (
      <li key={file.path} className="flex items-center gap-3 p-3 rounded-xl bg-white/60 dark:bg-cas-gray-800/60 border border-cas-gray-200 dark:border-cas-gray-700">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-cas-teal-50 dark:bg-cas-teal-900/40 flex items-center justify-center">
          <svg className="w-5 h-5 text-cas-teal-600 dark:text-cas-teal-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 3h7l5 5v11a2 2 0 01-2 2H7a2 2 0 01-2-2V5a2 2 0 012-2z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-cas-gray-900 dark:text-gray-100 truncate" title={file.name}>
            {file.name}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-cas-gray-600 dark:text-gray-400">
            <span>{formatFileSize(file.size_bytes)}</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-cas-gray-100 dark:bg-cas-gray-700 text-cas-gray-700 dark:text-gray-200">
              {formatExtension(file.extension)}
            </span>
            <span>{formatDateTime(file.modified)}</span>
          </div>
        </div>
        <div className="flex flex-shrink-0 items-center">
          <button
            type="button"
            onClick={() => handleDownloadPdf(file)}
            disabled={!file.pdf_available || isDownloading}
            title={
              file.pdf_available
                ? 'Download a reader-friendly PDF version of this document'
                : 'PDF export is not available for this file type'
            }
            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
              file.pdf_available
                ? 'bg-cas-teal-600 hover:bg-cas-teal-500 text-white disabled:bg-cas-teal-300 dark:disabled:bg-cas-teal-800'
                : 'bg-cas-gray-200 dark:bg-cas-gray-700 text-cas-gray-500 dark:text-gray-400 cursor-not-allowed'
            }`}
          >
            {isDownloading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                </svg>
                Processing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 16l-4-4m4 4l4-4m-4 4V4m8 12a4 4 0 01-4 4H8a4 4 0 01-4-4" />
                </svg>
                PDF
              </>
            )}
          </button>
        </div>
      </li>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-cas-navy-900 dark:text-gray-100 tracking-tight">[Placeholder for future development] </h1>
        </div>
        <div className="flex items-center gap-2 self-start md:self-end">
          <button
            onClick={fetchDocuments}
            type="button"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white dark:bg-cas-gray-800 text-sm font-semibold text-cas-gray-700 dark:text-gray-200 border border-cas-gray-200 dark:border-cas-gray-700 hover:bg-cas-gray-100 dark:hover:bg-cas-gray-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <div className="px-4 py-2 rounded-lg bg-cas-teal-50 dark:bg-cas-teal-900/30 border border-cas-teal-100 dark:border-cas-teal-800 text-sm text-cas-teal-700 dark:text-cas-teal-300 font-semibold">
            {loading ? '—' : `${totalFiles} file${totalFiles === 1 ? '' : 's'}`}
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {downloadError && (
        <div className="rounded-xl border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20 px-4 py-3 text-sm text-yellow-800 dark:text-yellow-200">
          {downloadError}
        </div>
      )}

      {loading ? (
        <div className="rounded-2xl border border-cas-gray-200 dark:border-cas-gray-700 bg-white/60 dark:bg-cas-gray-800/60 p-12 text-center text-cas-gray-500 dark:text-gray-400">
          Loading documents...
        </div>
      ) : (
        <div className="space-y-10">
          {groups.map((group) => (
            <section key={group.id} className="space-y-4">
              <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div>
                  <h2 className="text-2xl font-semibold text-cas-navy-800 dark:text-gray-100">{group.label}</h2>
                  {group.description && (
                    <p className="text-sm text-cas-gray-600 dark:text-gray-400 mt-1">{group.description}</p>
                  )}
                  <p className="text-xs text-cas-gray-500 dark:text-gray-500 mt-2">
                    Base path: <span className="font-mono">{group.base_path}</span>
                  </p>
                </div>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cas-gray-100 dark:bg-cas-gray-700 text-xs font-semibold text-cas-gray-700 dark:text-gray-300">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7a2 2 0 012-2h3l2 3h6l2-3h1a2 2 0 012 2v11a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                  </svg>
                  {group.directories?.length || 0} collection{group.directories?.length === 1 ? '' : 's'}
                </div>
              </header>

              {group.directories?.length ? (
                <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
                  {group.directories.map((directory) => (
                    <article
                      key={directory.id}
                      className="flex flex-col rounded-2xl border border-cas-gray-200 dark:border-cas-gray-700 bg-white/80 dark:bg-cas-gray-800/80 shadow-sm backdrop-blur transition-all hover:shadow-md"
                    >
                      <div className="p-6 border-b border-cas-gray-200/70 dark:border-cas-gray-700/60">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h3 className="text-lg font-semibold text-cas-gray-900 dark:text-gray-100">{directory.label}</h3>
                            {directory.description && (
                              <p className="text-sm text-cas-gray-600 dark:text-gray-400 mt-1">{directory.description}</p>
                            )}
                            <p className="text-xs text-cas-gray-500 dark:text-gray-500 mt-2 font-mono">{directory.path}</p>
                          </div>
                          <span className="inline-flex items-center px-2 py-1 rounded-full bg-cas-blue-50 dark:bg-cas-blue-900/40 text-xs font-semibold text-cas-blue-700 dark:text-cas-blue-200">
                            {directory.file_count || 0} file{directory.file_count === 1 ? '' : 's'}
                          </span>
                        </div>
                      </div>

                      <div className="p-6 flex-1">
                        {directory.files?.length ? (
                          <ul className="space-y-3 max-h-72 overflow-y-auto pr-1">
                            {directory.files.map((file) => renderFileRow(file))}
                          </ul>
                        ) : (
                          <div className="h-full flex items-center justify-center text-sm text-cas-gray-500 dark:text-gray-400">
                            No files yet. Add files to <span className="ml-1 font-mono">{directory.path}</span>
                          </div>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-cas-gray-200 dark:border-cas-gray-700 bg-white/70 dark:bg-cas-gray-800/70 px-6 py-10 text-center text-cas-gray-500 dark:text-gray-400">
                  No documents found in this group.
                </div>
              )}
            </section>
          ))}

          {groups.length === 0 && !error && (
            <div className="rounded-2xl border border-cas-gray-200 dark:border-cas-gray-700 bg-white/70 dark:bg-cas-gray-800/70 px-6 py-16 text-center text-cas-gray-500 dark:text-gray-400">
              No document directories found. Add files to the input or output folders to see them listed here.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Documents
