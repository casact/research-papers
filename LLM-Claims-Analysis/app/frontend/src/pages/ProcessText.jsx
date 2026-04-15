import { useState } from 'react'
import ConfigModal from '../components/ConfigModal'

function ProcessText() {
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false)

  return (
    <div className="text-center py-16">
      <p className="text-lg text-cas-gray-600 mb-6">[Placeholder for future development]</p>

      <button
        onClick={() => setIsConfigModalOpen(true)}
        className="px-6 py-3 bg-cas-blue-600 text-white rounded-lg hover:bg-cas-blue-700 transition-colors font-medium"
      >
        Configure Settings
      </button>

      <ConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        configPath="3_process-combine_text_to_json.yaml"
        title="Process & Combine Text Configuration"
      />
    </div>
  )
}

export default ProcessText
