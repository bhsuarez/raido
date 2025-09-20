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
  tracks: Track[]
}

const StationManager: React.FC = () => {
  const [tracks, setTracks] = useState<Track[]>([])
  const [stations, setStations] = useState<Station[]>([])
  const [name, setName] = useState('')
  const [selectedTracks, setSelectedTracks] = useState<number[]>([])

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
    try {
      const res = await apiHelpers.createStation({ name, track_ids: selectedTracks })
      setStations(prev => [...prev, res.data])
      setName('')
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
          onChange={e => setName(e.target.value)}
        />
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
                {s.name} ({s.tracks.length} tracks)
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
