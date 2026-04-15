import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

function ReadmeModal({ isOpen, onClose }) {
  const [markdown, setMarkdown] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isOpen) {
      fetch('/README.md')
        .then(response => response.text())
        .then(text => {
          setMarkdown(text)
          setLoading(false)
        })
        .catch(error => {
          console.error('Failed to load README:', error)
          setMarkdown('# Error\n\nFailed to load documentation.')
          setLoading(false)
        })
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-cas-gray-800 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-cas-gray-200 dark:border-cas-gray-700">
          <h2 className="text-2xl font-bold text-cas-gray-900 dark:text-gray-100">Documentation</h2>
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

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-cas-gray-500 dark:text-gray-400">Loading documentation...</div>
            </div>
          ) : (
            <div className="prose prose-cas max-w-none">
              <ReactMarkdown
                components={{
                  h1: ({ node, ...props }) => (
                    <h1 className="text-3xl font-bold text-cas-gray-900 dark:text-gray-100 mb-4 mt-6" {...props} />
                  ),
                  h2: ({ node, ...props }) => (
                    <h2 className="text-2xl font-bold text-cas-gray-900 dark:text-gray-100 mb-3 mt-5 border-b border-cas-gray-200 dark:border-cas-gray-700 pb-2" {...props} />
                  ),
                  h3: ({ node, ...props }) => (
                    <h3 className="text-xl font-semibold text-cas-gray-900 dark:text-gray-100 mb-2 mt-4" {...props} />
                  ),
                  h4: ({ node, ...props }) => (
                    <h4 className="text-lg font-semibold text-cas-gray-900 dark:text-gray-100 mb-2 mt-3" {...props} />
                  ),
                  p: ({ node, ...props }) => <p className="text-cas-gray-700 dark:text-gray-300 mb-4 leading-relaxed" {...props} />,
                  ul: ({ node, ordered, ...props }) => (
                    <ul className="list-disc pl-6 mb-4 text-cas-gray-700 dark:text-gray-300 space-y-2" {...props} />
                  ),
                  ol: ({ node, ordered, ...props }) => (
                    <ol className="list-decimal pl-6 mb-4 text-cas-gray-700 dark:text-gray-300 space-y-2" {...props} />
                  ),
                  li: ({ node, ...props }) => (
                    <li className="leading-relaxed marker:text-cas-blue-600 dark:marker:text-cas-blue-400" {...props} />
                  ),
                  code: ({ node, inline, className, children, ...props }) => {
                    const match = /language-(\w+)/.exec(className || '')
                    const language = match ? match[1] : null

                    return inline ? (
                      <code
                        className="bg-cas-gray-100 dark:bg-cas-gray-700 text-cas-blue-600 dark:text-cas-blue-400 px-1.5 py-0.5 rounded text-sm font-mono"
                        {...props}
                      >
                        {children}
                      </code>
                    ) : (
                      <code
                        className="block bg-cas-gray-900 dark:bg-black text-white p-4 rounded-lg overflow-x-auto font-mono text-sm whitespace-pre"
                        {...props}
                      >
                        {children}
                      </code>
                    )
                  },
                  pre: ({ node, children, ...props }) => (
                    <pre className="mb-5 rounded-lg overflow-hidden shadow-sm border border-cas-gray-800/40 dark:border-cas-gray-700" {...props}>
                      {children}
                    </pre>
                  ),
                  a: ({ node, ...props }) => (
                    <a className="text-cas-blue-600 dark:text-cas-blue-400 hover:text-cas-blue-700 dark:hover:text-cas-blue-300 underline" {...props} />
                  ),
                  blockquote: ({ node, ...props }) => (
                    <blockquote className="border-l-4 border-cas-blue-500 dark:border-cas-blue-400 pl-4 italic text-cas-gray-600 dark:text-gray-400 mb-4" {...props} />
                  ),
                  hr: ({ node, ...props }) => <hr className="my-6 border-cas-gray-200 dark:border-cas-gray-700" {...props} />,
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto rounded-lg border border-cas-gray-200 dark:border-cas-gray-700 shadow-sm">
                      <table className="min-w-full divide-y divide-cas-gray-200 dark:divide-cas-gray-700 text-sm" {...props} />
                    </div>
                  ),
                  thead: ({ node, ...props }) => (
                    <thead className="bg-cas-gray-50 dark:bg-cas-gray-700 text-cas-gray-700 dark:text-gray-300 font-semibold uppercase tracking-wide" {...props} />
                  ),
                  tbody: ({ node, ...props }) => <tbody className="bg-white dark:bg-cas-gray-800 divide-y divide-cas-gray-100 dark:divide-cas-gray-700" {...props} />,
                  tr: ({ node, isHeader, ...props }) => (
                    <tr className="hover:bg-cas-gray-50 dark:hover:bg-cas-gray-700/50 transition-colors" {...props} />
                  ),
                  th: ({ node, ...props }) => (
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-cas-gray-600 dark:text-gray-300" {...props} />
                  ),
                  td: ({ node, ...props }) => <td className="px-4 py-3 text-cas-gray-700 dark:text-gray-300 align-top" {...props} />,
                  strong: ({ node, ...props }) => <strong className="text-cas-gray-900 dark:text-gray-100 font-semibold" {...props} />,
                  em: ({ node, ...props }) => <em className="text-cas-gray-600 dark:text-gray-400" {...props} />,
                }}
              >
                {markdown}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-cas-gray-200 dark:border-cas-gray-700 bg-cas-gray-50 dark:bg-cas-gray-700/50">
          <button
            onClick={onClose}
            className="btn-secondary w-full sm:w-auto"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default ReadmeModal
