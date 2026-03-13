import { useEffect, useState, useCallback, useRef } from 'react'
import { Loader2, Check } from 'lucide-react'
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

  // Available versions
  const [availableVersions, setAvailableVersions] = useState<string[]>([])
  const [selectedVersions, setSelectedVersions] = useState<Set<string>>(new Set())
  const [loadingVersions, setLoadingVersions] = useState(false)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadStatus = useCallback(async () => {
    try {
      const data = await fetchApi<PatrolStatusData>('/patrol/status')
      setStatus(data)
      return data
    } catch {
      return null
    }
  }, [])

  const loadAvailableVersions = useCallback(async () => {
    setLoadingVersions(true)
    try {
      const data = await fetchApi<{ versions: string[] }>('/patrol/available-versions')
      setAvailableVersions(data.versions)
    } catch {
      // ignore
    } finally {
      setLoadingVersions(false)
    }
  }, [])

  useEffect(() => {
    Promise.all([loadStatus(), loadAvailableVersions()]).finally(() => setLoading(false))
  }, [loadStatus, loadAvailableVersions])

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
        loadAvailableVersions()
      }
    }, 3000)
  }, [loadStatus, loadAvailableVersions])

  const handleTriggerLatest = async () => {
    setTriggering(true)
    try {
      await postApi('/patrol/trigger')
      await loadStatus()
      startPolling()
    } catch {
      await loadStatus()
    } finally {
      setTriggering(false)
    }
  }

  const handleTriggerBatch = async () => {
    if (selectedVersions.size === 0) return
    setTriggering(true)
    try {
      const versions = Array.from(selectedVersions).sort()
      await postApi('/patrol/trigger-batch', { versions })
      setSelectedVersions(new Set())
      await loadStatus()
      startPolling()
    } catch {
      await loadStatus()
    } finally {
      setTriggering(false)
    }
  }

  const toggleVersion = (version: string) => {
    setSelectedVersions((prev) => {
      const next = new Set(prev)
      if (next.has(version)) {
        next.delete(version)
      } else {
        next.add(version)
      }
      return next
    })
  }

  const selectLatestN = (n: number) => {
    const latest = availableVersions.slice(-n)
    setSelectedVersions(new Set(latest))
  }

  const clearSelection = () => setSelectedVersions(new Set())

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  const isRunning = status?.running ?? false
  // Show latest versions first (reversed)
  const displayVersions = [...availableVersions].reverse()

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Patrol Status</h1>

      {/* Status Card */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-5">
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

        {isRunning && status?.current_task && (
          <div>
            <span className="text-sm text-gray-400">Current Task</span>
            <p className="text-gray-200 mt-1 font-mono text-sm">{status.current_task}</p>
          </div>
        )}

        <div>
          <span className="text-sm text-gray-400">Last Run</span>
          <p className="text-gray-200 mt-1">
            {status?.last_run
              ? new Date(status.last_run).toLocaleString()
              : 'Never'}
          </p>
        </div>

        {status?.error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
            <span className="text-sm font-medium text-red-400">Error</span>
            <p className="text-red-300 mt-1 text-sm">{status.error}</p>
          </div>
        )}
      </div>

      {/* Trigger Latest Button */}
      <button
        onClick={handleTriggerLatest}
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
          'Trigger Patrol (Latest Version)'
        )}
      </button>

      {/* Multi-Version Selection */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Multi-Version Analysis</h2>
          {loadingVersions && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
        </div>

        {displayVersions.length === 0 ? (
          <p className="text-gray-400 text-sm">All published versions have been analyzed.</p>
        ) : (
          <>
            {/* Quick Select Buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-gray-400">Quick select:</span>
              {[5, 10, 20].map((n) => (
                <button
                  key={n}
                  onClick={() => selectLatestN(n)}
                  disabled={isRunning}
                  className="px-3 py-1 text-xs rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white transition-colors disabled:opacity-50"
                >
                  Latest {n}
                </button>
              ))}
              {selectedVersions.size > 0 && (
                <button
                  onClick={clearSelection}
                  className="px-3 py-1 text-xs rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
                >
                  Clear ({selectedVersions.size})
                </button>
              )}
            </div>

            {/* Version Grid */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 max-h-72 overflow-y-auto">
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                {displayVersions.map((v) => {
                  const selected = selectedVersions.has(v)
                  return (
                    <button
                      key={v}
                      onClick={() => toggleVersion(v)}
                      disabled={isRunning}
                      className={`px-3 py-2 text-xs font-mono rounded-lg border transition-colors flex items-center gap-1.5 ${
                        selected
                          ? 'border-blue-500 bg-blue-500/20 text-blue-300'
                          : 'border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                      } disabled:opacity-50`}
                    >
                      {selected ? (
                        <Check className="w-3 h-3 flex-shrink-0" />
                      ) : (
                        <span className="w-3 h-3 flex-shrink-0" />
                      )}
                      {v}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Batch Trigger Button */}
            <button
              onClick={handleTriggerBatch}
              disabled={isRunning || triggering || selectedVersions.size === 0}
              className={`w-full py-3 rounded-xl text-sm font-semibold transition-colors ${
                isRunning || triggering || selectedVersions.size === 0
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  : 'bg-purple-600 hover:bg-purple-500 text-white'
              }`}
            >
              {selectedVersions.size === 0
                ? 'Select versions to analyze'
                : `Analyze ${selectedVersions.size} Version${selectedVersions.size > 1 ? 's' : ''}`}
            </button>
          </>
        )}
      </section>
    </div>
  )
}
