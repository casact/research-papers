import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import DarkModeToggle from './DarkModeToggle'

function Navbar({ apiStatus }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const location = useLocation()

  const navLinks = [
    { to: '/', label: 'Home', title: 'LLM Claims Analysis', description: 'Transform unstructured claims data into actionable insights' },
    { to: '/process-bundle', label: 'Process Bundle', title: '1: Process FHIR Bundle', description: 'Convert a FHIR bundle into a json with summarization' },
    { to: '/add-docs', label: 'Add Docs', title: '2: Add Documents', description: 'Add additional documents to the FHIR bundle' },
    { to: '/process-text', label: 'Process Text', title: '3: Process Text', description: 'Process text documents for claims analysis' },
    // { to: '/documents', label: 'Documents', title: 'Documents Library', description: 'Browse pipeline inputs and generated outputs' }
  ]

  // Find current page info
  const currentPage = navLinks.find(link => link.to === location.pathname)

  return (
    <>
      <nav className="fixed top-4 left-1/2 z-50 w-[calc(100%-2rem)] sm:w-[calc(100%-4rem)] max-w-5xl -translate-x-1/2 rounded-2xl border border-white/50 dark:border-cas-gray-700/50 bg-white/85 dark:bg-cas-gray-800/85 backdrop-blur supports-[backdrop-filter]:bg-white/65 dark:supports-[backdrop-filter]:bg-cas-gray-800/65 shadow-xl shadow-cas-navy-900/15 dark:shadow-black/30 transition-all px-4 sm:px-6 lg:px-8">
        <div className="relative">
          <div className="flex justify-between items-center h-16">
            {/* Left Side: Hamburger + Logo */}
            <div className="flex items-center space-x-3">
              {/* Hamburger Button */}
              <div className="relative">
                <button
                  onClick={() => setIsMenuOpen(!isMenuOpen)}
                  className="p-2 rounded-md text-cas-gray-600 dark:text-gray-400 hover:text-cas-gray-900 dark:hover:text-gray-100 hover:bg-white dark:hover:bg-cas-gray-700 transition-colors shadow-sm shadow-transparent hover:shadow-cas-navy-900/5 dark:hover:shadow-black/20 border border-transparent hover:border-cas-gray-200/60 dark:hover:border-cas-gray-600"
                  aria-label="Menu"
                  aria-expanded={isMenuOpen}
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    {isMenuOpen ? (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    ) : (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    )}
                  </svg>
                </button>

                <div
                  className={`absolute left-0 top-full mt-2 w-[min(20rem,calc(100vw-4rem))] origin-top ${
                    isMenuOpen
                      ? 'scale-100 opacity-100 pointer-events-auto'
                      : 'scale-95 opacity-0 pointer-events-none'
                  } transition-all duration-200 ease-out`}
                >
                  <div className="rounded-2xl border border-white/40 dark:border-cas-gray-600/40 bg-white/95 dark:bg-cas-gray-800/95 shadow-xl shadow-cas-navy-900/10 dark:shadow-black/30 backdrop-blur-md ring-1 ring-cas-gray-200/40 dark:ring-cas-gray-700/40 overflow-hidden">
                    <div className="divide-y divide-cas-gray-100 dark:divide-cas-gray-700">
                      {navLinks.map((link) => (
                        <Link
                          key={link.to}
                          to={link.to}
                          onClick={() => setIsMenuOpen(false)}
                          className="block px-4 py-3 text-sm font-medium text-cas-navy-800 dark:text-gray-200 hover:text-cas-teal-600 dark:hover:text-cas-teal-400 hover:bg-cas-teal-50/60 dark:hover:bg-cas-teal-900/20 transition-colors"
                        >
                          <div className="font-semibold">{link.label}</div>
                          <p className="mt-0.5 text-xs text-cas-gray-600 dark:text-gray-400">{link.description}</p>
                        </Link>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <Link to="/" className="flex items-center space-x-3 group">
                <div className="w-10 h-10 bg-gradient-to-br from-cas-teal-500 to-cas-teal-600 rounded-lg flex items-center justify-center shadow-lg shadow-cas-teal-500/30 group-hover:shadow-cas-teal-500/50 transition-shadow">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-cas-navy-900 dark:text-gray-100 tracking-tight">
                    {currentPage ? currentPage.title : 'LLM Claims Analysis'}
                  </h1>
                  {currentPage && currentPage.description && (
                    <p className="text-xs text-cas-gray-600 dark:text-gray-400 hidden sm:block">{currentPage.description}</p>
                  )}
                </div>
              </Link>
            </div>

            {/* Right Side: Dark Mode Toggle + Status */}
            <div className="flex items-center gap-3">
              {/* Dark Mode Toggle */}
              <DarkModeToggle />
              
              {/* Status Indicator */}
              <div className={`px-3 py-1 rounded-full text-xs font-medium flex items-center space-x-1.5 ${
                apiStatus === 'healthy' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                apiStatus === 'error' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300' :
                'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
              }`}>
                <div className={`w-1.5 h-1.5 rounded-full ${
                  apiStatus === 'healthy' ? 'bg-green-600 dark:bg-green-400' :
                  apiStatus === 'error' ? 'bg-red-600 dark:bg-red-400' :
                  'bg-yellow-600 dark:bg-yellow-400'
                }`}></div>
                <span>{apiStatus === 'healthy' ? 'Live' : apiStatus === 'error' ? 'Error' : 'Connecting...'}</span>
              </div>
            </div>
          </div>

        </div>
      </nav>
      <div className="h-24" aria-hidden="true" />
    </>
  )
}

export default Navbar
