import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ReadmeModal from '../components/ReadmeModal'
import FeatureRow from '../components/FeatureRow'

function Home({ apiInfo }) {
  const [isReadmeOpen, setIsReadmeOpen] = useState(false)
  const navigate = useNavigate()

  const features = [
    {
      title: 'Process Bundle',
      description: 'Convert FHIR bundles to structured claims data with AI-powered medical summarization',
      route: '/process-bundle',
      icon: 'process',
      stepNumber: 1
    },
    {
      title: 'Add Docs',
      description: 'Generate synthetic claim documents for comprehensive analysis',
      route: '/add-docs',
      icon: 'add',
      stepNumber: 2
    },
    {
      title: 'Process Text',
      description: 'Consolidate text documents into unified claim files',
      route: '/process-text',
      icon: 'combine',
      stepNumber: 3
    }
  ]

  return (
    <>
      {/* Hero Section */}
      <div className="text-center mb-20">
        {/* Title with gradient */}
        <div className="mb-6">
          <h1 className="text-6xl font-extrabold mb-6 leading-tight text-cas-navy-900 dark:text-gray-100">
            LLM Claims Analysis
          </h1>
          <p className="text-xl text-cas-gray-600 dark:text-gray-400 max-w-3xl mx-auto leading-relaxed mb-10">
            Transform unstructured claims data into actionable insights with advanced AI-powered feature engineering tailored for actuarial professionals.
          </p>
        </div>

        {/* Key Features Grid */}
        {/* <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto mb-10">
          <div className="flex flex-col items-center p-6 bg-white/50 backdrop-blur-sm rounded-xl border border-cas-gray-200">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-cas-teal-400 to-cas-teal-600 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="font-bold text-cas-navy-900 mb-1">AI-Powered</h3>
            <p className="text-sm text-cas-gray-600 text-center">Advanced LLM processing</p>
          </div>

          <div className="flex flex-col items-center p-6 bg-white/50 backdrop-blur-sm rounded-xl border border-cas-gray-200">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-cas-navy-400 to-cas-navy-600 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            </div>
            <h3 className="font-bold text-cas-navy-900 mb-1">FHIR Compatible</h3>
            <p className="text-sm text-cas-gray-600 text-center">Standards-based processing</p>
          </div>

          <div className="flex flex-col items-center p-6 bg-white/50 backdrop-blur-sm rounded-xl border border-cas-gray-200">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-cas-blue-400 to-cas-blue-600 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="font-bold text-cas-navy-900 mb-1">Actuarial Ready</h3>
            <p className="text-sm text-cas-gray-600 text-center">Structured for analysis</p>
          </div>
        </div> */}

        {/* CTA Buttons */}
        <div className="flex justify-center gap-4">
          <button
            onClick={() => setIsReadmeOpen(true)}
            className="btn-secondary"
          >
            <svg className="w-5 h-5 inline-block mr-2 -mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Learn More
          </button>
        </div>
      </div>

      {/* Features Section */}
      <div className="mb-20">
        <div className="space-y-6">
          {features.map((feature) => (
            <FeatureRow
              key={feature.route}
              title={feature.title}
              description={feature.description}
              onStart={() => navigate(feature.route)}
              stepNumber={feature.stepNumber}
              icon={feature.icon}
            />
          ))}
        </div>
      </div>

      {/* System Info */}
      {apiInfo && (
        <div className="relative overflow-hidden">
          <div className="card bg-gradient-to-br from-cas-navy-50 via-white to-cas-teal-50 dark:from-cas-navy-900/50 dark:via-cas-gray-800 dark:to-cas-teal-900/20 border-cas-navy-200 dark:border-cas-gray-700">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cas-navy-600 to-cas-navy-800 dark:from-cas-navy-500 dark:to-cas-navy-700 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-cas-navy-900 dark:text-gray-100">System Information</h3>
                  <p className="text-sm text-cas-gray-600 dark:text-gray-400">Platform status and version</p>
                </div>
              </div>
              <div className="badge-secondary font-mono text-sm">
                v{apiInfo.version}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6 pt-6 border-t border-cas-gray-200 dark:border-cas-gray-700">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-cas-teal-100 dark:bg-cas-teal-900/30 flex items-center justify-center">
                  <svg className="w-4 h-4 text-cas-teal-700 dark:text-cas-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <div className="text-xs text-cas-gray-500 dark:text-gray-400 uppercase tracking-wide">Status</div>
                  <div className="text-sm font-semibold text-cas-navy-900 dark:text-gray-100">Operational</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-cas-blue-100 dark:bg-cas-blue-900/30 flex items-center justify-center">
                  <svg className="w-4 h-4 text-cas-blue-700 dark:text-cas-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <div className="text-xs text-cas-gray-500 dark:text-gray-400 uppercase tracking-wide">Environment</div>
                  <div className="text-sm font-semibold text-cas-navy-900 dark:text-gray-100">Development</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-cas-navy-100 dark:bg-cas-navy-800 flex items-center justify-center">
                  <svg className="w-4 h-4 text-cas-navy-700 dark:text-cas-navy-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                  </svg>
                </div>
                <div>
                  <div className="text-xs text-cas-gray-500 dark:text-gray-400 uppercase tracking-wide">Pipeline</div>
                  <div className="text-sm font-semibold text-cas-navy-900 dark:text-gray-100">Ready</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* README Modal */}
      <ReadmeModal isOpen={isReadmeOpen} onClose={() => setIsReadmeOpen(false)} />
    </>
  )
}

export default Home
