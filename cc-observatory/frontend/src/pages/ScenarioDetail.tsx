import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Loader2,
  FileText,
  MessageSquare,
  Wrench,
  GitCompare,
  Code,
  LayoutDashboard,
  ArrowRight,
  Copy,
  Check,
} from 'lucide-react'
import { fetchApi } from '../lib/api'
import SystemPromptViewer from '../components/SystemPromptViewer'
import MessageChainViz from '../components/MessageChainViz'
import ToolsViewer from '../components/ToolsViewer'
import DiffViewer from '../components/DiffViewer'

interface Extracted {
  system_blocks?: { type: string; text: string; cache_control?: { type: string } }[]
  messages_chain?: { turn?: number; messages: { role: string; content: string | unknown[] }[] }[]
  tool_names?: string[]
  deferred_tools?: string[]
  tools?: { name: string; description?: string; input_schema?: unknown }[]
  api_calls?: { method: string; url: string }[]
  token_usage?: { input_tokens?: number; output_tokens?: number; cache_read?: number; cache_creation?: number }
  diff?: { original?: string; modified?: string }
  model_used?: string
}

interface TestRunDetail {
  id: number
  scenario_key?: string
  scenario_name?: string
  scenario_group?: string
  status?: string
  version_id?: number
  started_at?: string
  finished_at?: string
  error_message?: string
  extracted_data?: Extracted
  diff_data?: {
    original?: string
    modified?: string
    prev_version_id?: number
  }
}

type TabKey = 'overview' | 'system' | 'messages' | 'tools' | 'diff' | 'raw'

const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
  { key: 'system', label: 'System Prompt', icon: <FileText className="w-4 h-4" /> },
  { key: 'messages', label: 'Message Chain', icon: <MessageSquare className="w-4 h-4" /> },
  { key: 'tools', label: 'Tools', icon: <Wrench className="w-4 h-4" /> },
  { key: 'diff', label: 'Diff', icon: <GitCompare className="w-4 h-4" /> },
  { key: 'raw', label: 'Raw', icon: <Code className="w-4 h-4" /> },
]

export default function ScenarioDetail() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<TestRunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [rawData, setRawData] = useState<string | null>(null)
  const [rawLoading, setRawLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchApi<TestRunDetail>(`/test-runs/${id}`)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (activeTab === 'raw' && rawData === null && id) {
      setRawLoading(true)
      fetch(`/api/test-runs/${id}/raw`)
        .then((r) => r.json())
        .then((j) => setRawData(j.raw_jsonl ?? 'No raw data.'))
        .catch(() => setRawData('Failed to load raw data.'))
        .finally(() => setRawLoading(false))
    }
  }, [activeTab, rawData, id])

  const handleCopy = async () => {
    if (!rawData) return
    await navigator.clipboard.writeText(rawData)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-16 text-red-400">
        {error || 'Test run not found'}
      </div>
    )
  }

  const ext = data.extracted_data ?? {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">{data.scenario_name || data.scenario_key || 'Test Run'}</h1>
        <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
          {data.scenario_group && <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300">{data.scenario_group}</span>}
          {data.status && (
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${
                data.status === 'success'
                  ? 'bg-green-500/20 text-green-300'
                  : data.status === 'error'
                    ? 'bg-red-500/20 text-red-300'
                    : 'bg-yellow-500/20 text-yellow-300'
              }`}
            >
              {data.status}
            </span>
          )}
          {ext.model_used && <span className="font-mono text-xs">{ext.model_used}</span>}
          {data.started_at && <span className="text-xs text-gray-500">{new Date(data.started_at).toLocaleString()}</span>}
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 border-b border-gray-800">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors -mb-px ${
              activeTab === tab.key
                ? 'border-b-2 border-blue-400 text-blue-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && <OverviewTab data={data} ext={ext} />}
        {activeTab === 'system' && (
          <SystemPromptViewer blocks={ext.system_blocks ?? []} />
        )}
        {activeTab === 'messages' && (
          <MessageChainViz chain={(ext.messages_chain ?? []) as { turn?: number; messages: { role: string; content: string | { type: string; text?: string; name?: string; id?: string; input?: unknown; content?: string; tool_use_id?: string; thinking?: string }[] }[] }[]} />
        )}
        {activeTab === 'tools' && (
          <ToolsViewer
            toolNames={ext.tool_names ?? []}
            deferredTools={ext.deferred_tools ?? []}
            toolDefinitions={ext.tools}
          />
        )}
        {activeTab === 'diff' && (
          <DiffViewer
            original={data.diff_data?.original}
            modified={data.diff_data?.modified}
            language="markdown"
          />
        )}
        {activeTab === 'raw' && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <button
                onClick={handleCopy}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              >
                {copied ? (
                  <><Check className="w-4 h-4 text-green-400" /> Copied</>
                ) : (
                  <><Copy className="w-4 h-4" /> Copy</>
                )}
              </button>
            </div>
            {rawLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
              </div>
            ) : (
              <pre className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-300 overflow-x-auto max-h-[600px] overflow-y-scroll border border-gray-800">
                {rawData || 'No raw data available.'}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function OverviewTab({ data, ext }: { data: TestRunDetail; ext: Extracted }) {
  const systemLen = (ext.system_blocks ?? []).reduce((acc, b) => acc + (b.text?.length ?? 0), 0)
  const toolCount = (ext.tool_names ?? []).length + (ext.deferred_tools ?? []).length
  const messageTurns = (ext.messages_chain ?? []).length
  const tokens = ext.token_usage

  return (
    <div className="space-y-8">
      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="System Prompt" value={systemLen > 0 ? `${systemLen.toLocaleString()} chars` : '--'} />
        <MetricCard label="Tools" value={String(toolCount)} />
        <MetricCard label="Message Turns" value={String(messageTurns)} />
        <MetricCard
          label="Token Usage"
          value={
            tokens && (tokens.input_tokens || tokens.output_tokens)
              ? `${((tokens.input_tokens ?? 0) + (tokens.output_tokens ?? 0)).toLocaleString()}`
              : 'N/A'
          }
          sub={
            tokens && (tokens.input_tokens || tokens.output_tokens)
              ? `In: ${(tokens.input_tokens ?? 0).toLocaleString()} / Out: ${(tokens.output_tokens ?? 0).toLocaleString()}`
              : 'claude-trace 未捕获响应体'
          }
        />
      </div>

      {/* API Call Flow */}
      {ext.api_calls && ext.api_calls.length > 0 && (
        <section>
          <h3 className="text-lg font-semibold mb-3">API Call Flow</h3>
          <div className="bg-gray-900 rounded-lg border border-gray-800 divide-y divide-gray-800">
            {ext.api_calls.map((call, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3">
                <span className="text-xs text-gray-500 w-6">{i + 1}</span>
                <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-blue-500/20 text-blue-300">
                  {call.method}
                </span>
                <span className="font-mono text-sm text-gray-300 truncate">{call.url}</span>
                {i < (ext.api_calls?.length ?? 0) - 1 && (
                  <ArrowRight className="w-3.5 h-3.5 text-gray-600 ml-auto flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Scenario Info */}
      <section>
        <h3 className="text-lg font-semibold mb-3">Scenario Info</h3>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-2 text-sm">
          <InfoRow label="ID" value={data.id} mono />
          {data.scenario_key && <InfoRow label="Key" value={data.scenario_key} />}
          {data.scenario_group && <InfoRow label="Group" value={data.scenario_group} />}
          {ext.model_used && <InfoRow label="Model" value={ext.model_used} mono />}
          {data.version_id && <InfoRow label="Version" value={String(data.version_id)} mono />}
        </div>
      </section>
    </div>
  )
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="text-sm text-gray-400 mb-1">{label}</div>
      <div className="text-xl font-bold">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  )
}

function InfoRow({ label, value, mono }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <div className="flex gap-3">
      <span className="text-gray-500 w-24 flex-shrink-0">{label}</span>
      <span className={mono ? 'font-mono text-gray-300' : 'text-gray-300'}>{value}</span>
    </div>
  )
}
