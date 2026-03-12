import { DiffEditor } from '@monaco-editor/react'
import { GitCompare } from 'lucide-react'

interface DiffViewerProps {
  original?: string
  modified?: string
  language?: string
}

export default function DiffViewer({ original, modified, language = 'plaintext' }: DiffViewerProps) {
  if (!original || !modified) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400 space-y-3">
        <GitCompare className="w-10 h-10 text-gray-600" />
        <p>Select two versions to compare</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg overflow-hidden border border-gray-800">
      <DiffEditor
        height="600px"
        original={original}
        modified={modified}
        language={language}
        theme="vs-dark"
        options={{
          readOnly: true,
          renderSideBySide: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          fontSize: 13,
        }}
      />
    </div>
  )
}
