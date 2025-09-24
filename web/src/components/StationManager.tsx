import React, { useEffect, useState } from 'react'
import { apiHelpers } from '../utils/api'

interface Track {
  id: number
  title: string
  artist: string
}

interface Station {
  id: number
  name: string
  slug: string
  stream_mount: string
  stream_name?: string
  stream_url?: string
  tracks: Track[]
}

const StationManager: React.FC = () => {
  const [tracks, setTracks] = useState<Track[]>([])
  const [stations, setStations] = useState<Station[]>([])
  const [name, setName] = useState('')
  const [selectedTracks, setSelectedTracks] = useState<number[]>([])
  const [slug, setSlug] = useState('')
  const [streamMount, setStreamMount] = useState('/raido.mp3')
  const [streamMountTouched, setStreamMountTouched] = useState(false)
  const [streamName, setStreamName] = useState('')

  const slugify = (value: string) =>
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')

  const autoMountForSlug = (value: string) => `/${(value || 'station').replace(/^\/+/, '')}.mp3`

  const handleNameInput = (value: string) => {
    const previousAuto = slugify(name)
    setName(value)
    if (!streamName) {
      setStreamName(value)
    }
    if (!slug || slug === previousAuto) {
      const nextSlug = slugify(value)
      setSlug(nextSlug)
      if (!streamMountTouched) {
        setStreamMount(autoMountForSlug(nextSlug))
      }
    }
  }

  const handleSlugInput = (value: string) => {
    const nextSlug = slugify(value)
    setSlug(nextSlug)
    if (!streamMountTouched) {
      setStreamMount(autoMountForSlug(nextSlug))
    }
  }

  const handleStreamMountInput = (value: string) => {
    const normalized = value.startsWith('/') ? value : `/${value}`
    setStreamMount(normalized)
    setStreamMountTouched(true)
  }

  useEffect(() => {
    apiHelpers.getTracks()
      .then(res => setTracks(res.data))
      .catch(() => setTracks([]))
    apiHelpers.getStations()
      .then(res => setStations(res.data))
      .catch(() => setStations([]))
  }, [])

  const handleCreate = async () => {
    if (!name) return
    const nextSlug = slug || slugify(name)
    if (!nextSlug) return
    try {
      const res = await apiHelpers.createStation({
        name,
        slug: nextSlug,
        stream_mount: streamMount || autoMountForSlug(nextSlug),
        stream_name: streamName || name,
        track_ids: selectedTracks,
      })
      setStations(prev => [...prev, res.data])
      setName('')
      setSlug('')
      setStreamName('')
      setStreamMount('/raido.mp3')
      setStreamMountTouched(false)
      setSelectedTracks([])
    } catch (err) {
      console.error('Failed to create station', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 p-4 rounded-lg">
        <h2 className="text-xl text-white mb-2">Create Station</h2>
        <input
          className="w-full p-2 mb-2 rounded bg-gray-700 text-white"
          placeholder="Name"
          value={name}
          onChange={e => handleNameInput(e.target.value)}
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-2">
          <div>
            <label className="block text-xs uppercase tracking-wide text-gray-400 mb-1">Slug</label>
            <input
              className="w-full p-2 rounded bg-gray-700 text-white"
              placeholder="main"
              value={slug}
              onChange={e => handleSlugInput(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-gray-400 mb-1">Stream Name</label>
            <input
              className="w-full p-2 rounded bg-gray-700 text-white"
              placeholder="Friendly name"
              value={streamName}
              onChange={e => setStreamName(e.target.value)}
            />
          </div>
        </div>
        <div className="mb-2">
          <label className="block text-xs uppercase tracking-wide text-gray-400 mb-1">Icecast Mount</label>
          <input
            className="w-full p-2 rounded bg-gray-700 text-white"
            placeholder="/raido-holiday.mp3"
            value={streamMount}
            onChange={e => handleStreamMountInput(e.target.value)}
          />
        </div>
        <label className="text-gray-300 text-sm">Tracks</label>
        <select
          multiple
          className="w-full p-2 mb-2 rounded bg-gray-700 text-white h-40"
          value={selectedTracks.map(String)}
          onChange={e =>
            setSelectedTracks(Array.from(e.target.selectedOptions).map(o => Number(o.value)))
          }
        >
          {tracks.map(t => (
            <option key={t.id} value={t.id}>
              {t.artist} - {t.title}
            </option>
          ))}
        </select>
        <button
          className="px-4 py-2 bg-pirate-500 rounded text-white"
          onClick={handleCreate}
        >
          Create
        </button>
      </div>
      <div className="bg-gray-800 p-4 rounded-lg">
        <h2 className="text-xl text-white mb-2">Stations</h2>
        <ul className="text-gray-300 space-y-1">
          {stations.map(s => (
            <li key={s.id}>
              <div>
                <span className="font-semibold text-white">{s.name}</span> ({s.tracks.length} tracks)
                <div className="text-xs text-gray-400">
                  Slug: {s.slug} · Mount: {s.stream_mount}
                </div>
              </div>
              {s.tracks.length > 0 && (
                <ul className="ml-4 list-disc">
                  {s.tracks.map(t => (
                    <li key={t.id}>{t.artist} - {t.title}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default StationManager
