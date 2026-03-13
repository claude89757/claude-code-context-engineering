import { useState } from 'react'
import { ChevronDown, ChevronRight, Shield } from 'lucide-react'

interface SystemBlock {
  index?: number
  text: string
  length?: number
  cache_control?: { type: string } | null
}

interface SystemPromptViewerProps {
  blocks: SystemBlock[]
}

export default function SystemPromptViewer({ blocks }: SystemPromptViewerProps) {
  const [collapsed, setCollapsed] = useState<Record<number, boolean>>(() => {
    const init: Record<number, boolean> = {}
    blocks.forEach((_, i) => {
      // Default: first two blocks collapsed, rest expanded
      init[i] = i < 2
    })
    return init
  })

  const toggle = (index: number) => {
    setCollapsed((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  if (blocks.length === 0) {
    return <p className="text-gray-400">No system prompt blocks available.</p>
  }

  return (
    <div className="space-y-3">
      {blocks.map((block, i) => {
        const isCollapsed = collapsed[i] ?? false
        return (
          <div
            key={i}
            className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden"
          >
            <button
              onClick={() => toggle(i)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-800/50 transition-colors"
            >
              {isCollapsed ? (
                <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
              )}
              <Shield className="w-4 h-4 text-blue-400 flex-shrink-0" />
              <span className="font-medium text-sm">Block {i + 1}</span>
              <span className="text-xs text-gray-500 ml-2">
                {block.text.length.toLocaleString()} chars
              </span>
              {block.cache_control && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 ml-auto">
                  cache: {block.cache_control.type}
                </span>
              )}
            </button>
            {!isCollapsed && (
              <div className="border-t border-gray-800">
                <pre className="bg-gray-900 rounded-b-lg p-4 font-mono text-sm text-gray-300 overflow-x-auto max-h-96 overflow-y-auto whitespace-pre-wrap">
                  {block.text}
                </pre>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
