import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchApi } from '../lib/api'

interface Scenario {
  key: string
  name: string
  group?: string
  description?: string
}

interface HistoryEntry {
  test_run_id: string
  version_id: string
  started_at: string
  system_prompt_length: number
  tool_count: number
  model_used: string
  token_usage?: { input_tokens?: number; output_tokens?: number }
}

type Metric = 'system_prompt_length' | 'tool_count'

export default function ScenarioHistory() {
  const { key } = useParams<{ key: string }>()
  const navigate = useNavigate()
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [metric, setMetric] = useState<Metric>('system_prompt_length')

  useEffect(() => {
    if (!key) return
    setLoading(true)

    Promise.allSettled([
      fetchApi<Scenario[]>('/scenarios'),
      fetchApi<HistoryEntry[]>(`/scenarios/${key}/history`),
    ])
      .then(([scenariosResult, historyResult]) => {
        if (scenariosResult.status === 'fulfilled') {
          const match = scenariosResult.value.find((s) => s.key === key)
          setScenario(match ?? null)
        }
        if (historyResult.status === 'fulfilled') {
          setHistory(historyResult.value)
        } else {
          setError('Failed to load scenario history')
        }
      })
      .finally(() => setLoading(false))
  }, [key])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-16 text-red-400">{error}</div>
    )
  }

  const chartData = history.map((entry) => ({
    version: entry.version_id,
    value: entry[metric],
  }))

  const metricLabel = metric === 'system_prompt_length' ? 'System Prompt Length' : 'Tool Count'

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">{scenario?.name ?? key}</h1>
        <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
          {scenario?.group && (
            <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300">
              {scenario.group}
            </span>
          )}
          {scenario?.description && (
            <span className="text-gray-400">{scenario.description}</span>
          )}
        </div>
      </div>

      {/* Metric Selector + Chart */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Metric Trend</h2>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as Metric)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="system_prompt_length">System Prompt Length</option>
            <option value="tool_count">Tool Count</option>
          </select>
        </div>
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="version"
                  stroke="#9ca3af"
                  tick={{ fill: '#9ca3af', fontSize: 12 }}
                />
                <YAxis
                  stroke="#9ca3af"
                  tick={{ fill: '#9ca3af', fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: '1px solid #374151',
                    borderRadius: '0.5rem',
                    color: '#f3f4f6',
                  }}
                  labelStyle={{ color: '#9ca3af' }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  name={metricLabel}
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-center py-12">No history data available.</p>
          )}
        </div>
      </section>

      {/* History Table */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Version History</h2>
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          {history.length === 0 ? (
            <p className="p-6 text-gray-400">No history entries yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 text-left">
                    <th className="px-6 py-3 font-medium">Version</th>
                    <th className="px-6 py-3 font-medium">Date</th>
                    <th className="px-6 py-3 font-medium">Prompt Length</th>
                    <th className="px-6 py-3 font-medium">Tools</th>
                    <th className="px-6 py-3 font-medium">Model</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {history.map((entry) => (
                    <tr
                      key={entry.test_run_id}
                      onClick={() => navigate(`/test-runs/${entry.test_run_id}`)}
                      className="hover:bg-gray-800/50 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-4 font-mono text-blue-400">
                        {entry.version_id}
                      </td>
                      <td className="px-6 py-4 text-gray-400">
                        {new Date(entry.started_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-gray-300">
                        {entry.system_prompt_length.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-gray-300">
                        {entry.tool_count}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-gray-400">
                        {entry.model_used}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
