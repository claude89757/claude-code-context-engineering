import { useState } from 'react'
import { Wrench, ChevronDown, ChevronRight, Package } from 'lucide-react'

interface ToolDefinition {
  name: string
  description?: string
  input_schema?: unknown
}

interface ToolsViewerProps {
  toolNames: string[]
  deferredTools: string[]
  toolDefinitions?: ToolDefinition[]
}

export default function ToolsViewer({
  toolNames,
  deferredTools,
  toolDefinitions = [],
}: ToolsViewerProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const toggle = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }))
  }

  const defMap = new Map(toolDefinitions.map((t) => [t.name, t]))

  function ToolCard({ name, isDeferred }: { name: string; isDeferred: boolean }) {
    const def = defMap.get(name)
    const isExpanded = expanded[name] ?? false

    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
        <button
          onClick={() => def && toggle(name)}
          className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-800/50 transition-colors"
        >
          {def ? (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
            )
          ) : (
            <div className="w-4" />
          )}
          {isDeferred ? (
            <Package className="w-4 h-4 text-yellow-400 flex-shrink-0" />
          ) : (
            <Wrench className="w-4 h-4 text-blue-400 flex-shrink-0" />
          )}
          <span className="font-mono text-sm">{name}</span>
          {def?.description && (
            <span className="text-xs text-gray-500 ml-2 truncate">
              {def.description.slice(0, 100)}
              {def.description.length > 100 ? '...' : ''}
            </span>
          )}
        </button>
        {isExpanded && def && (
          <div className="border-t border-gray-800 p-4">
            {def.description && (
              <p className="text-sm text-gray-300 mb-3">{def.description}</p>
            )}
            {def.input_schema != null && (
              <pre className="bg-gray-950 rounded p-3 font-mono text-xs text-gray-400 overflow-x-auto max-h-64 overflow-y-auto">
                {String(JSON.stringify(def.input_schema, null, 2))}
              </pre>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Wrench className="w-5 h-5 text-blue-400" />
          Core Tools
          <span className="text-sm text-gray-500 font-normal">({toolNames.length})</span>
        </h3>
        {toolNames.length === 0 ? (
          <p className="text-gray-400 text-sm">No core tools found.</p>
        ) : (
          <div className="space-y-2">
            {toolNames.map((name) => (
              <ToolCard key={name} name={name} isDeferred={false} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Package className="w-5 h-5 text-yellow-400" />
          Deferred Tools
          <span className="text-sm text-gray-500 font-normal">({deferredTools.length})</span>
        </h3>
        {deferredTools.length === 0 ? (
          <p className="text-gray-400 text-sm">No deferred tools found.</p>
        ) : (
          <div className="space-y-2">
            {deferredTools.map((name) => (
              <ToolCard key={name} name={name} isDeferred={true} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
