import { useEffect, useState, useCallback, useRef } from 'react'
import { Loader2 } from 'lucide-react'
import { fetchApi, postApi } from '../lib/api'

interface PatrolStatusData {
  running: boolean
  last_run?: string
  current_task?: string
  error?: string
}

export default function PatrolStatus() {
  const [status, setStatus] = useState<PatrolStatusData | null>(null)
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadStatus = useCallback(async () => {
    try {
      const data = await fetchApi<PatrolStatusData>('/patrol/status')
      setStatus(data)
      return data
    } catch {
      // keep existing status on error
      return null
    }
  }, [])

  useEffect(() => {
    loadStatus().finally(() => setLoading(false))
  }, [loadStatus])

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      const data = await loadStatus()
      if (data && !data.running) {
        if (pollRef.current) clearInterval(pollRef.current)
        pollRef.current = null
      }
    }, 3000)
  }, [loadStatus])

  const handleTrigger = async () => {
    setTriggering(true)
    try {
      await postApi('/patrol/trigger')
      await loadStatus()
      startPolling()
    } catch {
      // reload status to reflect any changes
      await loadStatus()
    } finally {
      setTriggering(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  const isRunning = status?.running ?? false

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Patrol Status</h1>

      {/* Status Card */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-5">
        {/* Running State */}
        <div className="flex items-center gap-3">
          <span className="relative flex h-3 w-3">
            {isRunning ? (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-yellow-500" />
              </>
            ) : (
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500" />
            )}
          </span>
          <span className="text-lg font-semibold">
            {isRunning ? 'Running' : 'Idle'}
          </span>
        </div>

        {/* Current Task */}
        {isRunning && status?.current_task && (
          <div>
            <span className="text-sm text-gray-400">Current Task</span>
            <p className="text-gray-200 mt-1 font-mono text-sm">{status.current_task}</p>
          </div>
        )}

        {/* Last Run */}
        <div>
          <span className="text-sm text-gray-400">Last Run</span>
          <p className="text-gray-200 mt-1">
            {status?.last_run
              ? new Date(status.last_run).toLocaleString()
              : 'Never'}
          </p>
        </div>

        {/* Error */}
        {status?.error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
            <span className="text-sm font-medium text-red-400">Error</span>
            <p className="text-red-300 mt-1 text-sm">{status.error}</p>
          </div>
        )}
      </div>

      {/* Trigger Button */}
      <button
        onClick={handleTrigger}
        disabled={isRunning || triggering}
        className={`w-full py-3 rounded-xl text-sm font-semibold transition-colors ${
          isRunning || triggering
            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-500 text-white'
        }`}
      >
        {triggering ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Triggering...
          </span>
        ) : isRunning ? (
          'Patrol is Running...'
        ) : (
          'Trigger Patrol'
        )}
      </button>
    </div>
  )
}
