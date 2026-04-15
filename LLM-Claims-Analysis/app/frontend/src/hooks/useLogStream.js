import { useState, useEffect, useRef } from 'react'

/**
 * Custom hook for streaming job logs via Server-Sent Events
 * @param {string} jobId - The ID of the job to stream logs for
 * @param {boolean} isStreaming - Whether to enable streaming (typically job.status === 'running')
 * @returns {{logs: string, isConnected: boolean, error: string|null}}
 */
export function useLogStream(jobId, isStreaming) {
  const [logs, setLogs] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState(null)
  const eventSourceRef = useRef(null)

  useEffect(() => {
    // Don't start streaming if not enabled or no job ID
    if (!jobId || !isStreaming) {
      setIsConnected(false)
      return
    }

    console.log(`[useLogStream] Starting log stream for job ${jobId}`)

    // Create EventSource connection
    const eventSource = new EventSource(`/api/jobs/${jobId}/logs/stream`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      console.log(`[useLogStream] Connection opened for job ${jobId}`)
      setIsConnected(true)
      setError(null)
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.error) {
          console.error('[useLogStream] Stream error:', data.error)
          setError(data.error)
          eventSource.close()
          return
        }

        if (data.type === 'initial') {
          // Initial logs (sent when connection first opens)
          setLogs(data.log)
        } else if (data.type === 'line') {
          // New log line
          setLogs(prev => prev + data.log)
        } else if (data.type === 'complete') {
          // Job completed
          console.log('[useLogStream] Job completed, closing stream')
          eventSource.close()
          setIsConnected(false)
        }
      } catch (err) {
        console.error('[useLogStream] Failed to parse log data:', err, 'Raw data:', event.data)
      }
    }

    eventSource.onerror = (errorEvent) => {
      console.error('[useLogStream] EventSource error:', errorEvent)
      setError('Connection lost')
      setIsConnected(false)
      eventSource.close()
    }

    // Cleanup on unmount or when dependencies change
    return () => {
      if (eventSourceRef.current) {
        console.log(`[useLogStream] Cleaning up stream for job ${jobId}`)
        eventSourceRef.current.close()
        setIsConnected(false)
      }
    }
  }, [jobId, isStreaming])

  return { logs, isConnected, error }
}
