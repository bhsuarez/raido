import React from 'react'
import { MicIcon } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'

const CommentaryTranscript: React.FC = () => {
  const commentaryText = useRadioStore((s) => s.commentaryText)
  const isGenerating = useRadioStore((s) => s.isGeneratingCommentary)

  if (!commentaryText && !isGenerating) return null

  return (
    <section
      className={`card p-5 border transition-colors duration-500 ${
        isGenerating
          ? 'border-teal-700/60 bg-teal-950/20'
          : 'border-gray-700/50'
      }`}
      aria-label="DJ Commentary"
      aria-live="polite"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div
          className={`flex items-center justify-center w-7 h-7 rounded-full ${
            isGenerating ? 'bg-teal-700/40' : 'bg-gray-800'
          }`}
        >
          <MicIcon className={`w-3.5 h-3.5 ${isGenerating ? 'text-teal-400' : 'text-gray-400'}`} />
        </div>
        <span className="text-xs font-semibold uppercase tracking-widest text-teal-500/80">
          DJ Commentary
        </span>
        {isGenerating && (
          <span className="flex items-center gap-1 ml-auto text-xs text-teal-600">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
            generating
          </span>
        )}
      </div>

      {/* Transcript text */}
      <p className="text-teal-300 leading-relaxed text-sm sm:text-base font-light tracking-wide">
        {commentaryText}
        {isGenerating && (
          <span className="inline-block w-0.5 h-4 bg-teal-400 ml-0.5 align-middle animate-[blink_1s_step-end_infinite]" />
        )}
      </p>
    </section>
  )
}

export default CommentaryTranscript
