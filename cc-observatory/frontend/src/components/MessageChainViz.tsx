import { MessageSquare, Bot, Wrench, Brain } from 'lucide-react'

interface ContentBlock {
  type: string
  text?: string
  name?: string
  id?: string
  input?: unknown
  content?: string | ContentBlock[]
  tool_use_id?: string
  thinking?: string
}

interface Message {
  role: string
  content: string | ContentBlock[]
}

interface ApiCallTurn {
  turn?: number
  messages: Message[]
}

interface MessageChainVizProps {
  chain: ApiCallTurn[]
}

const roleBadge: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  user: {
    bg: 'bg-blue-500/20 border-blue-500/30',
    text: 'text-blue-300',
    icon: <MessageSquare className="w-3.5 h-3.5" />,
  },
  assistant: {
    bg: 'bg-green-500/20 border-green-500/30',
    text: 'text-green-300',
    icon: <Bot className="w-3.5 h-3.5" />,
  },
  tool_result: {
    bg: 'bg-yellow-500/20 border-yellow-500/30',
    text: 'text-yellow-300',
    icon: <Wrench className="w-3.5 h-3.5" />,
  },
}

function getContentBlocks(content: string | ContentBlock[]): ContentBlock[] {
  if (typeof content === 'string') {
    return [{ type: 'text', text: content }]
  }
  return content
}

function ContentBlockView({ block }: { block: ContentBlock }) {
  if (block.type === 'text' && block.text) {
    return (
      <div className="text-sm text-gray-300 whitespace-pre-wrap break-words">
        {block.text.length > 500 ? block.text.slice(0, 500) + '...' : block.text}
      </div>
    )
  }
  if (block.type === 'tool_use') {
    return (
      <div className="bg-gray-800/50 rounded p-3 space-y-1">
        <div className="flex items-center gap-2">
          <Wrench className="w-3.5 h-3.5 text-orange-400" />
          <span className="text-sm font-mono text-orange-300">{block.name}</span>
          <span className="text-xs text-gray-500">tool_use</span>
        </div>
        {block.input != null && (
          <pre className="text-xs text-gray-400 overflow-x-auto max-h-32 overflow-y-auto">
            {String(JSON.stringify(block.input, null, 2)).slice(0, 300)}
          </pre>
        )}
      </div>
    )
  }
  if (block.type === 'tool_result') {
    return (
      <div className="bg-gray-800/50 rounded p-3 space-y-1">
        <div className="flex items-center gap-2">
          <Wrench className="w-3.5 h-3.5 text-yellow-400" />
          <span className="text-xs text-gray-500">tool_result</span>
          {block.tool_use_id && (
            <span className="text-xs text-gray-600 font-mono">{block.tool_use_id.slice(0, 12)}</span>
          )}
        </div>
        {block.content && typeof block.content === 'string' && (
          <div className="text-xs text-gray-400 whitespace-pre-wrap max-h-32 overflow-y-auto">
            {block.content.slice(0, 300)}
          </div>
        )}
      </div>
    )
  }
  if (block.type === 'thinking') {
    return (
      <div className="bg-gray-800/50 rounded p-3 space-y-1">
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-xs text-purple-400">thinking</span>
        </div>
        <div className="text-xs text-gray-400 italic max-h-32 overflow-y-auto">
          {(block.thinking || block.text || '').slice(0, 300)}
        </div>
      </div>
    )
  }
  return (
    <div className="text-xs text-gray-500">
      [{block.type}]
    </div>
  )
}

export default function MessageChainViz({ chain }: MessageChainVizProps) {
  if (chain.length === 0) {
    return <p className="text-gray-400">No message chain data available.</p>
  }

  return (
    <div className="space-y-6">
      {chain.map((turn, ti) => (
        <div key={ti} className="relative">
          <div className="text-xs text-gray-500 mb-2 font-medium">
            API Call Turn {turn.turn ?? ti + 1}
          </div>
          <div className="space-y-3 ml-4 border-l-2 border-gray-800 pl-4">
            {turn.messages.map((msg, mi) => {
              const badge = roleBadge[msg.role] ?? roleBadge.user
              const blocks = getContentBlocks(msg.content)
              return (
                <div key={mi} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border ${badge.bg} ${badge.text}`}
                    >
                      {badge.icon}
                      {msg.role}
                    </span>
                    <span className="text-xs text-gray-600">
                      {blocks.length} block{blocks.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="space-y-2 pl-2">
                    {blocks.map((block, bi) => (
                      <ContentBlockView key={bi} block={block} />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
