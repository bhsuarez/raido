import React, { useState } from 'react'
import { MicIcon, SearchIcon, ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'
import { useCommentaries, CommentaryFilters } from '../hooks/useNowPlaying'
import { apiHelpers } from '../utils/api'

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = React.useState(value)
  React.useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatDuration(ms: number | null): string {
  if (!ms) return ''
  const s = Math.round(ms / 1000)
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}:${rem.toString().padStart(2, '0')}`
}

const PROVIDER_OPTIONS = [
  { label: 'All', value: '' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Ollama', value: 'ollama' },
]

export default function CommentaryBrowser() {
  const [provider, setProvider] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebounce(search, 300)

  const filters: CommentaryFilters = {
    provider: provider || undefined,
    status: 'ready',
    search: debouncedSearch || undefined,
    page,
    per_page: 20,
  }

  const { data, isLoading, isError } = useCommentaries(filters)

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0
  const progressPct =
    data && data.total_tracks > 0
      ? ((data.total / data.total_tracks) * 100).toFixed(1)
      : '0'

  function handleProviderChange(val: string) {
    setProvider(val)
    setPage(1)
  }

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSearch(e.target.value)
    setPage(1)
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-white">Transcripts</h1>
          {data && (
            <span className="text-xs bg-teal-900/50 text-teal-400 border border-teal-700/40 rounded-full px-2.5 py-0.5 font-medium">
              {data.total.toLocaleString()} / {data.total_tracks.toLocaleString()} tracks — {progressPct}%
            </span>
          )}
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Provider toggle */}
        <div className="flex rounded-lg overflow-hidden border border-gray-700 text-sm">
          {PROVIDER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleProviderChange(opt.value)}
              className={`px-3 py-1.5 font-medium transition-colors ${
                provider === opt.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={handleSearchChange}
            placeholder="Search title or artist…"
            className="w-full pl-9 pr-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-primary-500"
          />
        </div>
      </div>

      {/* States */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="flex gap-3">
                <div className="w-12 h-12 rounded bg-gray-800 flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-gray-800 rounded w-1/3" />
                  <div className="h-3 bg-gray-800 rounded w-1/4" />
                  <div className="h-3 bg-gray-800 rounded w-full mt-2" />
                  <div className="h-3 bg-gray-800 rounded w-4/5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {isError && (
        <div className="card p-6 text-red-400 text-sm">
          Failed to load commentaries.
        </div>
      )}

      {!isLoading && !isError && data?.items.length === 0 && (
        <div className="card p-10 text-center text-gray-500 text-sm">
          No commentaries found.
        </div>
      )}

      {/* Card list */}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((item) => {
            const artworkUrl = apiHelpers.resolveStaticUrl(item.track?.artwork_url ?? null)
            const audioUrl = apiHelpers.resolveStaticUrl(item.audio_url ?? null)
            const displayText = item.transcript || item.text

            return (
              <article key={item.id} className="card p-4 space-y-3">
                {/* Track info row */}
                <div className="flex gap-3 items-start">
                  {/* Artwork */}
                  {artworkUrl ? (
                    <img
                      src={artworkUrl}
                      alt=""
                      className="w-12 h-12 rounded object-cover flex-shrink-0 bg-gray-800"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded bg-gray-800 flex-shrink-0 flex items-center justify-center">
                      <MicIcon className="w-5 h-5 text-gray-600" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white truncate">
                      {item.track?.title ?? 'Unknown Track'}
                    </p>
                    <p className="text-xs text-gray-400 truncate">
                      {item.track?.artist ?? 'Unknown Artist'}
                      {item.track?.album ? ` · ${item.track.album}` : ''}
                    </p>

                    {/* Badges */}
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {item.model && (
                        <span className="text-[10px] font-mono bg-gray-800 text-gray-400 border border-gray-700 rounded px-1.5 py-0.5">
                          {item.model}
                        </span>
                      )}
                      <span className="text-[10px] text-gray-500">
                        {formatDate(item.created_at)}
                        {item.duration_ms ? ` · ${formatDuration(item.duration_ms)}` : ''}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Transcript */}
                {displayText && (
                  <p className="text-teal-300 text-sm leading-relaxed font-light tracking-wide">
                    {displayText}
                  </p>
                )}

                {/* Audio player */}
                {audioUrl && (
                  <audio
                    controls
                    preload="none"
                    className="w-full h-8"
                    src={audioUrl}
                  />
                )}
              </article>
            )
          })}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary flex items-center gap-1.5 text-sm py-2 px-3 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeftIcon className="h-4 w-4" />
            Prev
          </button>
          <span className="text-sm text-gray-500">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="btn-secondary flex items-center gap-1.5 text-sm py-2 px-3 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRightIcon className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
