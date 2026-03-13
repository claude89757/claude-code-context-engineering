import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { fetchApi } from '../lib/api'

interface Version {
  id: number
  version: string
  detected_at: string
  status: string
  summary?: string
  test_run_count?: number
}

const dotColor: Record<string, string> = {
  analyzed: 'bg-green-500',
  testing: 'bg-yellow-500',
  detected: 'bg-blue-500',
  error: 'bg-red-500',
}

const ringColor: Record<string, string> = {
  analyzed: 'ring-green-500/30',
  testing: 'ring-yellow-500/30',
  detected: 'ring-blue-500/30',
  error: 'ring-red-500/30',
}

export default function Timeline() {
  const navigate = useNavigate()
  const [versions, setVersions] = useState<Version[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchApi<Version[]>('/versions')
      .then(setVersions)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-8">Version Timeline</h1>

      {versions.length === 0 && (
        <p className="text-gray-400">No versions tracked yet.</p>
      )}

      <div className="relative">
        {/* Vertical line */}
        {versions.length > 0 && (
          <div className="absolute left-4 top-3 bottom-3 w-0.5 bg-gray-700" />
        )}

        <div className="space-y-6">
          {versions.map((v) => (
            <button
              key={v.id}
              onClick={() => navigate(`/versions/${v.id}`)}
              className="relative flex items-start gap-6 pl-0 w-full text-left group"
            >
              {/* Dot on the timeline */}
              <div className="relative z-10 flex-shrink-0 mt-1">
                <span
                  className={`block w-8 h-8 rounded-full ring-4 ${dotColor[v.status] ?? 'bg-gray-500'} ${ringColor[v.status] ?? 'ring-gray-500/30'}`}
                />
              </div>

              {/* Content card */}
              <div className="flex-1 bg-gray-900 rounded-xl border border-gray-800 p-5 group-hover:border-gray-600 transition-colors">
                <div className="flex items-center gap-3 mb-1">
                  <span className="font-mono text-sm font-semibold text-blue-400">
                    {v.version}
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(v.detected_at).toLocaleString()}
                  </span>
                </div>

                {v.summary && (
                  <p className="text-sm text-gray-400 mt-2 line-clamp-2">
                    {v.summary.slice(0, 100)}
                    {v.summary.length > 100 ? '...' : ''}
                  </p>
                )}

                <div className="flex items-center gap-3 mt-3 text-xs text-gray-500">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border border-gray-700`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${dotColor[v.status] ?? 'bg-gray-500'}`} />
                    {v.status}
                  </span>
                  {v.test_run_count !== undefined && (
                    <span>{v.test_run_count} test run{v.test_run_count !== 1 ? 's' : ''}</span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
