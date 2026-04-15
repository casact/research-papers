import Navbar from './Navbar'
import { DarkModeProvider } from '../contexts/DarkModeContext'

function Layout({ children, apiStatus }) {
  return (
    <DarkModeProvider>
      <div className="min-h-screen flex flex-col">
        <Navbar apiStatus={apiStatus} />

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {children}
        </main>

        {/* Footer */}
        <footer className="pb-8 text-center border-t border-cas-gray-200 dark:border-cas-gray-700 pt-8 mt-12">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cas-teal-500 to-cas-teal-600 flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <span className="font-semibold text-cas-navy-900 dark:text-gray-100">LLM Claims Analysis</span>
            </div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cas-gold-50 dark:bg-cas-gold-900/30 border border-cas-gold-200 dark:border-cas-gold-700 mb-3">
              <svg className="w-4 h-4 text-cas-gold-600 dark:text-cas-gold-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span className="text-xs font-semibold text-cas-gold-800 dark:text-cas-gold-300 uppercase tracking-wide">Prototype</span>
            </div>
            <p className="text-sm text-cas-gray-600 dark:text-cas-gray-400 mb-1">
              Under development for the Casualty Actuarial Society
            </p>
            <p className="text-xs text-cas-gray-500 dark:text-cas-gray-500">
              Not for production use
            </p>
          </div>
        </footer>
      </div>
    </DarkModeProvider>
  )
}

export default Layout
