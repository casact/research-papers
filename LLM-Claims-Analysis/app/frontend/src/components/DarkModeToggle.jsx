import { useDarkMode } from '../contexts/DarkModeContext'

function DarkModeToggle() {
  const { darkMode, toggleDarkMode } = useDarkMode()

  return (
    <button
      onClick={toggleDarkMode}
      className="p-2 rounded-lg transition-all duration-200
        text-cas-gray-600 hover:text-cas-navy-900 hover:bg-cas-gray-100
        dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-cas-gray-800
        focus:outline-none focus:ring-2 focus:ring-cas-teal-500 focus:ring-offset-2 dark:focus:ring-offset-cas-gray-900"
      aria-label="Toggle dark mode"
      title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {darkMode ? (
        // Sun icon for light mode
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      ) : (
        // Moon icon for dark mode
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        </svg>
      )}
    </button>
  )
}

export default DarkModeToggle
