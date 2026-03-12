import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchApi } from '../lib/api'
import ReactMarkdown from 'react-markdown'
import {
  ArrowLeft,
  Calendar,
  GitCommit,
  AlertTriangle,
  CheckCircle,
  Loader2,
} from 'lucide-react'

interface TestRun {
  id: string
  scenario_key: string
  scenario_name: string
  scenario_group: string
  status: string
}

interface Report {
  id: string
  report_type: string
  content: string
}

interface VersionDetail {
  id: string
  version_number: string
  detected_at: string
  status: string
  test_runs: TestRun[]
  reports: Report[]
}

interface Diff {
  id: string
  scenario_key: string
  diff_type: string
  significance: string
  change_summary: string
}

interface ReportListItem {
  id: string
  report_type: string
}

function significanceBadge(significance: string) {
  const styles: Record<string, string> = {
    major: 'bg-red-900/50 text-red-400',
    minor: 'bg-yellow-900/50 text-yellow-400',
    none: 'bg-green-900/50 text-green-400',
  }
  const cls = styles[significance] ?? 'bg-gray-800 text-gray-400'
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${cls}`}>
      {significance}
    </span>
  )
}

function statusBadge(status: string) {
  const isComplete = status === 'completed' || status === 'complete'
  const isPending = status === 'pending' || status === 'running'
  const cls = isComplete
    ? 'bg-green-900/50 text-green-400'
    : isPending
      ? 'bg-yellow-900/50 text-yellow-400'
      : 'bg-gray-800 text-gray-400'
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${cls}`}>
      {status}
    </span>
  )
}

export default function VersionDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [version, setVersion] = useState<VersionDetail | null>(null)
  const [diffs, setDiffs] = useState<Diff[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [versionData, diffsData, reportsList] = await Promise.all([
          fetchApi<VersionDetail>(`/versions/${id}`),
          fetchApi<Diff[]>(`/versions/${id}/diff`),
          fetchApi<ReportListItem[]>(`/reports?version_id=${id}`),
        ])

        setVersion(versionData)
        setDiffs(diffsData)

        // Find the version_summary report and fetch full content
        const summaryRef = reportsList.find(
          (r) => r.report_type === 'version_summary'
        )
        if (summaryRef) {
          const fullReport = await fetchApi<Report>(
            `/reports/${summaryRef.id}`
          )
          setReport(fullReport)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load version')
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        <span className="ml-2 text-gray-400">Loading version...</span>
      </div>
    )
  }

  if (error || !version) {
    return (
      <div className="flex items-center justify-center py-20">
        <AlertTriangle className="w-6 h-6 text-red-400" />
        <span className="ml-2 text-red-400">{error ?? 'Version not found'}</span>
      </div>
    )
  }

  // Group test runs by scenario_group
  const grouped = version.test_runs.reduce<Record<string, TestRun[]>>(
    (acc, run) => {
      const group = run.scenario_group || 'Other'
      if (!acc[group]) acc[group] = []
      acc[group].push(run)
      return acc
    },
    {}
  )

  // Group diffs by diff_type
  const diffsByType = diffs.reduce<Record<string, Diff[]>>((acc, diff) => {
    const type = diff.diff_type || 'other'
    if (!acc[type]) acc[type] = []
    acc[type].push(diff)
    return acc
  }, {})

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <div className="flex items-center gap-4 flex-wrap">
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <GitCommit className="w-7 h-7 text-blue-400" />
            Version {version.version_number}
          </h1>
          {statusBadge(version.status)}
        </div>

        <div className="flex items-center gap-2 mt-2 text-sm text-gray-400">
          <Calendar className="w-4 h-4" />
          <span>
            Detected{' '}
            {new Date(version.detected_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      </div>

      {/* LLM Analysis Report */}
      <section>
        <h2 className="text-xl font-semibold mb-3">LLM Analysis Report</h2>
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          {report ? (
            <div className="prose prose-invert max-w-none prose-headings:text-gray-100 prose-p:text-gray-300 prose-li:text-gray-300 prose-strong:text-gray-200">
              <ReactMarkdown>{report.content}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-gray-500">No analysis report available</p>
          )}
        </div>
      </section>

      {/* Diff Summary */}
      <section>
        <h2 className="text-xl font-semibold mb-3">Diff Summary</h2>
        {diffs.length === 0 ? (
          <p className="text-gray-500">No diffs available for this version.</p>
        ) : (
          <div className="space-y-4">
            {Object.entries(diffsByType).map(([type, typeDiffs]) => (
              <div key={type}>
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-2">
                  {type}
                </h3>
                <div className="space-y-2">
                  {typeDiffs.map((diff) => (
                    <div
                      key={diff.id}
                      className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 flex items-center justify-between gap-4"
                    >
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium text-gray-200">
                          {diff.scenario_key}
                        </span>
                        <p className="text-sm text-gray-400 mt-0.5 truncate">
                          {diff.change_summary}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {significanceBadge(diff.significance)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Scenario Test Results Grid */}
      <section>
        <h2 className="text-xl font-semibold mb-3">Scenario Test Results</h2>
        {version.test_runs.length === 0 ? (
          <p className="text-gray-500">No test runs available.</p>
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([group, runs]) => (
              <div key={group}>
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
                  {group}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {runs.map((run) => {
                    const isPass =
                      run.status === 'passed' || run.status === 'completed'
                    const isFail =
                      run.status === 'failed' || run.status === 'error'
                    return (
                      <div
                        key={run.id}
                        onClick={() => navigate(`/test-runs/${run.id}`)}
                        className="bg-gray-900 rounded-lg border border-gray-800 p-4 hover:border-gray-700 cursor-pointer transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-gray-100 truncate">
                              {run.scenario_name}
                            </p>
                            <span className="inline-flex mt-1 px-2 py-0.5 rounded-full text-xs bg-gray-800 text-gray-400">
                              {run.scenario_group}
                            </span>
                          </div>
                          <div className="shrink-0 mt-0.5">
                            {isPass && (
                              <CheckCircle className="w-5 h-5 text-green-400" />
                            )}
                            {isFail && (
                              <AlertTriangle className="w-5 h-5 text-red-400" />
                            )}
                            {!isPass && !isFail && (
                              <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-gray-800 text-gray-400">
                                {run.status}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="mt-2 text-xs text-gray-500">
                          {run.scenario_key}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
