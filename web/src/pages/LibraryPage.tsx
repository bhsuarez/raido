// web/src/pages/LibraryPage.tsx
import { useSearchParams } from 'react-router-dom'
import MediaLibrary from '../components/MediaLibrary'
import MBEnrich from '../components/MBEnrich'

type Tab = 'browse' | 'enrich'

export default function LibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = (searchParams.get('tab') as Tab) || 'browse'

  function setTab(t: Tab) {
    setSearchParams({ tab: t }, { replace: true })
  }

  return (
    <div className="space-y-4">
      {/* Tab switcher */}
      <div
        className="flex gap-1 p-1 rounded-xl w-fit"
        style={{ background: 'rgba(13,13,26,0.8)', border: '1px solid #1a1a32' }}
      >
        {(['browse', 'enrich'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-4 py-1.5 rounded-lg text-xs font-display font-bold uppercase transition-all"
            style={{
              letterSpacing: '0.12em',
              background: tab === t ? 'rgba(56,189,248,0.12)' : 'transparent',
              color: tab === t ? '#38bdf8' : '#404060',
              border: tab === t ? '1px solid rgba(56,189,248,0.2)' : '1px solid transparent',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'browse' && <MediaLibrary />}
      {tab === 'enrich' && <MBEnrich />}
    </div>
  )
}
