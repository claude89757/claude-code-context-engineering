import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { fetchApi } from '../lib/api'

interface Scenario {
  key: string
  name: string
  group: string
  mode: string
  description: string
}

const groupColors: Record<string, string> = {
  '\u57fa\u7840': 'border-blue-500/40 bg-blue-500/10',
  '\u5de5\u5177': 'border-purple-500/40 bg-purple-500/10',
  '\u4ee3\u7406': 'border-cyan-500/40 bg-cyan-500/10',
  '\u4e0a\u4e0b\u6587\u7ba1\u7406': 'border-yellow-500/40 bg-yellow-500/10',
  '\u6a21\u578b': 'border-green-500/40 bg-green-500/10',
}

const groupBadgeColors: Record<string, string> = {
  '\u57fa\u7840': 'bg-blue-500/20 text-blue-300',
  '\u5de5\u5177': 'bg-purple-500/20 text-purple-300',
  '\u4ee3\u7406': 'bg-cyan-500/20 text-cyan-300',
  '\u4e0a\u4e0b\u6587\u7ba1\u7406': 'bg-yellow-500/20 text-yellow-300',
  '\u6a21\u578b': 'bg-green-500/20 text-green-300',
}

export default function ScenariosIndex() {
  const navigate = useNavigate()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchApi<Scenario[]>('/scenarios')
      .then(setScenarios)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  // Group scenarios by group
  const grouped = scenarios.reduce<Record<string, Scenario[]>>((acc, s) => {
    if (!acc[s.group]) acc[s.group] = []
    acc[s.group].push(s)
    return acc
  }, {})

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Test Scenarios</h1>

      {Object.entries(grouped).map(([group, items]) => (
        <section key={group} className="space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full ${groupBadgeColors[group] ?? 'bg-gray-700 text-gray-300'}`}>
              {group}
            </span>
            <span className="text-gray-400 text-sm font-normal">{items.length} scenarios</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {items.map((s) => (
              <button
                key={s.key}
                onClick={() => navigate(`/scenarios/${s.key}`)}
                className={`text-left p-4 rounded-xl border transition-colors hover:bg-gray-800/50 ${
                  groupColors[group] ?? 'border-gray-700 bg-gray-900'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono text-sm text-blue-400">{s.key}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded border border-gray-700 text-gray-400">
                    {s.mode}
                  </span>
                </div>
                <p className="text-sm font-medium text-gray-200">{s.name}</p>
                <p className="text-xs text-gray-500 mt-1">{s.description}</p>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
