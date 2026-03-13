import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layers, Tag, Clock, AlertTriangle, Loader2 } from 'lucide-react'
import { fetchApi } from '../lib/api'
import TrendChart from '../components/TrendChart'

interface Version {
  id: number
  version: string
  detected_at: string
  status: string
  summary?: string
  test_run_count: number
  report_count: number
}

interface PatrolStatus {
  last_run?: string | null
  running?: boolean
  current_task?: string | null
  error?: string | null
}

interface TrendPoint {
  version: string
  value: number
}

interface TrendsResponse {
  metric: string
  scenario_key: string
  data: TrendPoint[]
}

const statusColor: Record<string, string> = {
  analyzed: 'bg-green-500',
  testing: 'bg-yellow-500',
  detected: 'bg-blue-500',
  error: 'bg-red-500',
}

const statusLabel: Record<string, string> = {
  analyzed: 'Analyzed',
  testing: 'Testing',
  detected: 'Detected',
  error: 'Error',
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [versions, setVersions] = useState<Version[]>([])
  const [latestVersion, setLatestVersion] = useState<string>('—')
  const [lastPatrol, setLastPatrol] = useState<string>('—')
  const [trendData, setTrendData] = useState<TrendPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [vList, latest, patrol, trends] = await Promise.allSettled([
          fetchApi<Version[]>('/versions'),
          fetchApi<{ version: string }>('/versions/latest'),
          fetchApi<PatrolStatus>('/patrol/status'),
          fetchApi<TrendsResponse>('/trends?metric=system_prompt_length'),
        ])

        if (vList.status === 'fulfilled') setVersions(vList.value)
        if (latest.status === 'fulfilled') setLatestVersion(latest.value.version)
        if (patrol.status === 'fulfilled' && patrol.value.last_run) {
          setLastPatrol(new Date(patrol.value.last_run).toLocaleString())
        }
        if (trends.status === 'fulfilled') setTrendData(trends.value.data ?? [])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const changesCount = versions.filter((v) => v.report_count > 0).length

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  const recentVersions = versions.slice(0, 10)

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Layers className="w-5 h-5 text-blue-400" />}
          title="Tracked Versions"
          value={String(versions.length)}
        />
        <StatCard
          icon={<Tag className="w-5 h-5 text-purple-400" />}
          title="Latest Version"
          value={latestVersion}
        />
        <StatCard
          icon={<Clock className="w-5 h-5 text-cyan-400" />}
          title="Last Patrol"
          value={lastPatrol}
        />
        <StatCard
          icon={<AlertTriangle className="w-5 h-5 text-yellow-400" />}
          title="Changes Found"
          value={String(changesCount)}
        />
      </div>

      {/* Recent Version Changes */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Recent Version Changes</h2>
        <div className="bg-gray-900 rounded-xl border border-gray-800 divide-y divide-gray-800">
          {recentVersions.length === 0 && (
            <p className="p-6 text-gray-400">No versions tracked yet.</p>
          )}
          {recentVersions.map((v) => (
            <button
              key={v.id}
              onClick={() => navigate(`/versions/${v.id}`)}
              className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-gray-800/50 transition-colors"
            >
              <span
                className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${statusColor[v.status] ?? 'bg-gray-500'}`}
              />
              <span className="font-mono text-sm text-blue-400 w-28 flex-shrink-0">
                {v.version}
              </span>
              <span className="text-xs text-gray-500 w-40 flex-shrink-0">
                {new Date(v.detected_at).toLocaleString()}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full border border-gray-700 text-gray-300">
                {statusLabel[v.status] ?? v.status}
              </span>
              {v.summary && (
                <span className="text-sm text-gray-400 truncate ml-2">
                  {v.summary}
                </span>
              )}
            </button>
          ))}
        </div>
      </section>

      {/* Trend Chart */}
      <section>
        <h2 className="text-xl font-semibold mb-4">System Prompt Length Trend</h2>
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          {trendData.length > 0 ? (
            <TrendChart data={trendData} label="System Prompt Length" />
          ) : (
            <p className="text-gray-400 text-center py-12">No trend data available yet.</p>
          )}
        </div>
      </section>
    </div>
  )
}

function StatCard({
  icon,
  title,
  value,
}: {
  icon: React.ReactNode
  title: string
  value: string
}) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <span className="text-sm text-gray-400">{title}</span>
      </div>
      <p className="text-2xl font-bold truncate">{value}</p>
    </div>
  )
}
