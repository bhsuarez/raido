import React from 'react'
import { useRadioStore } from '../store/radioStore'

const CommentaryTranscript: React.FC = () => {
  const commentaryText = useRadioStore((s) => s.commentaryText)
  const isGenerating = useRadioStore((s) => s.isGeneratingCommentary)

  if (!commentaryText && !isGenerating) return null

  return (
    <section
      className="relative overflow-hidden rounded-2xl"
      aria-label="DJ Commentary"
      aria-live="polite"
      style={{
        background: isGenerating
          ? 'rgba(26, 5, 32, 0.7)'
          : 'rgba(13, 13, 26, 0.96)',
        border: `1px solid ${isGenerating ? 'rgba(232,121,249,0.25)' : '#1a1a32'}`,
        transition: 'background 0.6s ease, border-color 0.6s ease',
      }}
    >
      {/* Left accent bar */}
      <div
        className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-2xl"
        style={{
          background: isGenerating
            ? 'linear-gradient(to bottom, transparent, #d946ef, transparent)'
            : 'linear-gradient(to bottom, transparent, #252545, transparent)',
          transition: 'background 0.6s ease',
        }}
      />

      {/* Subtle glow when generating */}
      {isGenerating && (
        <div
          className="absolute inset-0 pointer-events-none rounded-2xl"
          style={{ boxShadow: 'inset 0 0 40px rgba(217, 70, 239, 0.05)' }}
        />
      )}

      <div className="px-5 py-4">
        {/* Header row */}
        <div className="flex items-center gap-2.5 mb-3">
          {/* Mic indicator */}
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
            style={{
              background: isGenerating ? 'rgba(217,70,239,0.15)' : 'rgba(37,37,69,0.5)',
              border: `1px solid ${isGenerating ? 'rgba(217,70,239,0.3)' : '#252545'}`,
            }}
          >
            {/* Waveform mic icon — 3 tiny bars */}
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <rect x="1"  y="4" width="1.5" height="4" rx="0.75"
                fill={isGenerating ? '#e879f9' : '#383858'} opacity="0.7" />
              <rect x="4.25" y="1" width="1.5" height="7" rx="0.75"
                fill={isGenerating ? '#e879f9' : '#383858'} />
              <rect x="7.5" y="3" width="1.5" height="5" rx="0.75"
                fill={isGenerating ? '#e879f9' : '#383858'} opacity="0.7" />
            </svg>
          </div>

          <span
            className="font-display font-bold uppercase"
            style={{
              fontSize: '0.6rem',
              letterSpacing: '0.16em',
              color: isGenerating ? '#d946ef' : '#383858',
              transition: 'color 0.5s ease',
            }}
          >
            AI Commentary
          </span>

          {isGenerating && (
            <div className="flex items-center gap-1 ml-auto">
              <span
                className="w-1.5 h-1.5 rounded-full animate-pulse"
                style={{ background: '#d946ef', boxShadow: '0 0 6px rgba(217,70,239,0.7)' }}
              />
              <span
                className="font-mono uppercase"
                style={{ fontSize: '0.55rem', color: '#a020c0', letterSpacing: '0.1em' }}
              >
                live
              </span>
            </div>
          )}
        </div>

        {/* Commentary text */}
        <p
          className="leading-relaxed"
          style={{
            color: isGenerating ? '#e8a0f8' : '#9090b8',
            fontSize: '0.95rem',
            fontWeight: 400,
            fontStyle: 'normal',
            lineHeight: '1.65',
            letterSpacing: '0.01em',
          }}
        >
          {commentaryText}
          {isGenerating && (
            <span
              className="inline-block w-0.5 h-4 ml-0.5 align-middle rounded-sm"
              style={{
                background: '#d946ef',
                boxShadow: '0 0 6px rgba(217,70,239,0.8)',
                animation: 'blink 1s step-end infinite',
              }}
            />
          )}
        </p>
      </div>
    </section>
  )
}

export default CommentaryTranscript
