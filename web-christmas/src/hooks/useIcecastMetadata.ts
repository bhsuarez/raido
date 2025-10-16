import { useEffect, useState } from 'react'

interface IcecastMetadata {
  artist: string
  title: string
  album?: string
  artwork_url?: string
}

export function useIcecastMetadata() {
  const [metadata, setMetadata] = useState<IcecastMetadata | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const response = await fetch('/stream/status-json.xsl')
        const data = await response.json()

        // Find the Christmas stream
        const sources = Array.isArray(data.icestats.source)
          ? data.icestats.source
          : [data.icestats.source]

        const christmasSource = sources.find((s: any) =>
          s.listenurl && s.listenurl.toLowerCase().includes('christmas')
        )

        if (christmasSource) {
          const fullTitle = christmasSource.title || 'Unknown Track'
          // Parse "Artist - Title" format
          const parts = fullTitle.split(' - ')

          let artist = 'Unknown Artist'
          let title = fullTitle

          if (parts.length >= 2) {
            artist = parts[0].trim()
            title = parts.slice(1).join(' - ').trim()
          }

          // Fetch artwork from API
          try {
            const searchParams = new URLSearchParams({
              artist: artist,
              title: title,
            })
            const artworkResponse = await fetch(`/api/v1/metadata/search?${searchParams}`)

            if (artworkResponse.ok) {
              const tracks = await artworkResponse.json()
              const artwork_url = tracks.length > 0 ? tracks[0].artwork_url : undefined

              setMetadata({
                artist,
                title,
                artwork_url,
              })
            } else {
              setMetadata({ artist, title })
            }
          } catch (artworkError) {
            // If artwork fetch fails, still show basic metadata
            setMetadata({ artist, title })
          }
        } else {
          console.warn('Christmas stream not found in Icecast sources')
        }
        setIsLoading(false)
      } catch (error) {
        console.error('Failed to fetch Icecast metadata:', error)
        setIsLoading(false)
      }
    }

    // Initial fetch
    fetchMetadata()

    // Poll every 10 seconds
    const interval = setInterval(fetchMetadata, 10000)

    return () => clearInterval(interval)
  }, [])

  return { metadata, isLoading }
}
