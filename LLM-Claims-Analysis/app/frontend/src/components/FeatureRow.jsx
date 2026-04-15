function FeatureRow({ title, description, onStart, stepNumber, icon }) {
  const getIcon = () => {
    switch (icon) {
      case 'process':
        return (
          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        )
      case 'add':
        return (
          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        )
      case 'combine':
        return (
          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
        )
      default:
        return (
          <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        )
    }
  }

  return (
    <div className="card-feature group cursor-pointer" onClick={onStart}>
      <div className="flex items-start gap-6">
        {/* Icon and Step Number */}
        <div className="flex-shrink-0">
          <div className="icon-container-lg relative">
            {getIcon()}
            {/* Step badge */}
            <div className="absolute -top-2 -right-2 w-7 h-7 bg-cas-navy-900 dark:bg-cas-navy-700 text-white rounded-full flex items-center justify-center text-xs font-bold shadow-md ring-2 ring-white dark:ring-cas-gray-800">
              {stepNumber}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4 mb-3">
            <h3 className="text-xl font-bold text-cas-navy-900 dark:text-gray-100 group-hover:text-cas-teal-700 dark:group-hover:text-cas-teal-400 transition-colors">
              {title}
            </h3>
            <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <svg className="w-6 h-6 text-cas-teal-600 dark:text-cas-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </div>
          </div>

          <p className="text-cas-gray-600 dark:text-gray-400 leading-relaxed mb-4">
            {description}
          </p>

          {/* Action indicator */}
          <div className="flex items-center gap-2 text-sm font-medium text-cas-teal-600 dark:text-cas-teal-400 group-hover:text-cas-teal-700 dark:group-hover:text-cas-teal-300">
            <span>Start Processing</span>
            <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FeatureRow
