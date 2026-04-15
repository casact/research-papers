import { useState } from 'react'

function ScriptArgumentsForm({ onChange }) {
  const [args, setArgs] = useState({
    outputDir: '',
    limit: '',
    verbose: false,
    dryRun: false,
    skipValidation: false
  })

  const handleChange = (field, value) => {
    const newArgs = { ...args, [field]: value }
    setArgs(newArgs)
    onChange(newArgs)
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-cas-gray-900 dark:text-gray-100 mb-4">Script Arguments</h3>

      {/* Output Directory */}
      <div>
        <label className="block text-sm font-medium text-cas-gray-700 dark:text-gray-300 mb-1">
          Output Directory
        </label>
        <input
          type="text"
          value={args.outputDir}
          onChange={(e) => handleChange('outputDir', e.target.value)}
          placeholder="./output/1_data-process_fhir_bundle"
          className="w-full px-3 py-2 border border-cas-gray-300 dark:border-cas-gray-600 dark:bg-cas-gray-700 dark:text-gray-200 rounded-md shadow-sm focus:outline-none focus:ring-cas-blue-500 focus:border-cas-blue-500 text-sm"
        />
        <p className="text-xs text-cas-gray-500 dark:text-gray-400 mt-1">
          Leave empty to use default from config
        </p>
      </div>

      {/* Limit Encounters */}
      <div>
        <label className="block text-sm font-medium text-cas-gray-700 dark:text-gray-300 mb-1">
          Limit Encounters
        </label>
        <input
          type="number"
          value={args.limit}
          onChange={(e) => handleChange('limit', e.target.value)}
          placeholder="No limit"
          min="1"
          className="w-full px-3 py-2 border border-cas-gray-300 dark:border-cas-gray-600 dark:bg-cas-gray-700 dark:text-gray-200 rounded-md shadow-sm focus:outline-none focus:ring-cas-blue-500 focus:border-cas-blue-500 text-sm"
        />
        <p className="text-xs text-cas-gray-500 dark:text-gray-400 mt-1">
          Limit number of encounters per file (useful for testing)
        </p>
      </div>

      {/* Checkboxes */}
      <div className="space-y-3 pt-2">
        {/* Verbose Logging */}
        <div className="flex items-start">
          <div className="flex items-center h-5">
            <input
              id="verbose"
              type="checkbox"
              checked={args.verbose}
              onChange={(e) => handleChange('verbose', e.target.checked)}
              className="h-4 w-4 text-cas-blue-600 focus:ring-cas-blue-500 border-cas-gray-300 dark:border-cas-gray-600 dark:bg-cas-gray-700 rounded"
            />
          </div>
          <div className="ml-3">
            <label htmlFor="verbose" className="text-sm font-medium text-cas-gray-700 dark:text-gray-300 cursor-pointer">
              Verbose Logging
            </label>
            <p className="text-xs text-cas-gray-500 dark:text-gray-400">
              Enable detailed debug output
            </p>
          </div>
        </div>

        {/* Dry Run */}
        <div className="flex items-start">
          <div className="flex items-center h-5">
            <input
              id="dryRun"
              type="checkbox"
              checked={args.dryRun}
              onChange={(e) => handleChange('dryRun', e.target.checked)}
              className="h-4 w-4 text-cas-blue-600 focus:ring-cas-blue-500 border-cas-gray-300 dark:border-cas-gray-600 dark:bg-cas-gray-700 rounded"
            />
          </div>
          <div className="ml-3">
            <label htmlFor="dryRun" className="text-sm font-medium text-cas-gray-700 dark:text-gray-300 cursor-pointer">
              Dry Run
            </label>
            <p className="text-xs text-cas-gray-500 dark:text-gray-400">
              Validate inputs without processing
            </p>
          </div>
        </div>

        {/* Skip Validation */}
        <div className="flex items-start">
          <div className="flex items-center h-5">
            <input
              id="skipValidation"
              type="checkbox"
              checked={args.skipValidation}
              onChange={(e) => handleChange('skipValidation', e.target.checked)}
              className="h-4 w-4 text-cas-blue-600 focus:ring-cas-blue-500 border-cas-gray-300 dark:border-cas-gray-600 dark:bg-cas-gray-700 rounded"
            />
          </div>
          <div className="ml-3">
            <label htmlFor="skipValidation" className="text-sm font-medium text-cas-gray-700 dark:text-gray-300 cursor-pointer">
              Skip Validation
            </label>
            <p className="text-xs text-cas-gray-500 dark:text-gray-400">
              Skip input validation (not recommended)
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ScriptArgumentsForm
