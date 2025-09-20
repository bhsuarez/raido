import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import api from '../utils/api'

interface VoiceReference {
  name: string
  filename: string
  size: number
  created: number
  modified: number
}

const VoiceCloning: React.FC = () => {
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [voiceName, setVoiceName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [testingVoice, setTestingVoice] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Query for voice references
  const { data: voiceRefs, isLoading, error } = useQuery<{voices: VoiceReference[]}>({
    queryKey: ['voice-references'],
    queryFn: () => api.get('/admin/voice-references').then(res => res.data),
    refetchInterval: 10000,
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async ({ file, name }: { file: File, name: string }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('voice_name', name)
      return api.post('/admin/upload-voice-reference', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    onSuccess: () => {
      toast.success('Voice reference uploaded successfully!')
      setUploadFile(null)
      setVoiceName('')
      queryClient.invalidateQueries({ queryKey: ['voice-references'] })
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Upload failed')
    }
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (voiceName: string) => api.delete(`/admin/voice-reference/${voiceName}`),
    onSuccess: () => {
      toast.success('Voice reference deleted!')
      queryClient.invalidateQueries({ queryKey: ['voice-references'] })
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Delete failed')
    }
  })

  // Test voice mutation
  const testVoiceMutation = useMutation({
    mutationFn: (voiceName: string) =>
      api.post('/admin/tts-test-chatterbox', {
        text: `Hello, this is a test of the ${voiceName} voice using Chatterbox TTS.`,
        voice: voiceName
      }),
    onSuccess: (response) => {
      if (response.data?.audio_url) {
        // Play the audio
        const audio = new Audio(response.data.audio_url)
        audio.play().catch(e => console.error('Failed to play audio:', e))
        toast.success('Voice test generated! Playing audio...')
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Voice test failed')
    },
    onSettled: () => {
      setTestingVoice(null)
    }
  })

  const handleUpload = () => {
    if (!uploadFile || !voiceName.trim()) {
      toast.error('Please select a file and enter a voice name')
      return
    }

    uploadMutation.mutate({ file: uploadFile, name: voiceName.trim() })
  }

  const handleDelete = (voiceName: string) => {
    if (window.confirm(`Are you sure you want to delete the '${voiceName}' voice reference?`)) {
      deleteMutation.mutate(voiceName)
    }
  }

  const handleTestVoice = (voiceName: string) => {
    setTestingVoice(voiceName)
    testVoiceMutation.mutate(voiceName)
  }

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 Bytes'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString()
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900 p-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <div className="animate-spin w-12 h-12 border-4 border-pirate-400 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-400">Loading voice references...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900 p-4">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-pirate-800/40 to-gray-800/40 rounded-2xl p-8 border border-pirate-600/20">
          <h1 className="text-4xl font-bold text-white mb-4 flex items-center gap-3">
            🎤 Voice Cloning Studio
          </h1>
          <p className="text-gray-300 text-lg">
            Upload audio samples to create custom voices for Chatterbox TTS using zero-shot voice cloning technology.
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            📁 Upload Voice Reference
          </h2>

          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="voiceName" className="block text-sm text-gray-300 mb-2">Voice Name</label>
                <input
                  id="voiceName"
                  type="text"
                  value={voiceName}
                  onChange={(e) => setVoiceName(e.target.value)}
                  placeholder="e.g., female, male, narrator, morgan_freeman"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  disabled={uploading}
                />
              </div>

              <div>
                <label htmlFor="voiceFile" className="block text-sm text-gray-300 mb-2">Audio File</label>
                <input
                  id="voiceFile"
                  type="file"
                  accept=".wav"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white file:bg-pirate-600 file:border-none file:rounded file:px-3 file:py-1 file:text-white file:mr-3"
                  disabled={uploading}
                />
              </div>
            </div>

            <div className="bg-blue-900/20 border border-blue-600/20 rounded-lg p-4">
              <h3 className="text-blue-300 font-semibold mb-2">💡 Voice Reference Guidelines</h3>
              <ul className="text-blue-200 text-sm space-y-1">
                <li>• <strong>5-15 seconds</strong> of clear speech (longer clips work too)</li>
                <li>• <strong>Single speaker</strong> only, no background music or noise</li>
                <li>• <strong>High quality</strong> recording for best results</li>
                <li>• <strong>WAV format only</strong> is supported currently</li>
                <li>• <strong>Match the target language</strong> for accent authenticity</li>
              </ul>
            </div>

            <button
              onClick={handleUpload}
              disabled={!uploadFile || !voiceName.trim() || uploading || uploadMutation.isPending}
              className="px-6 py-3 bg-pirate-600 text-white rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-pirate-700 transition-colors flex items-center gap-2"
            >
              {uploadMutation.isPending ? (
                <>
                  <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                  Uploading...
                </>
              ) : (
                <>
                  📤 Upload Voice Reference
                </>
              )}
            </button>
          </div>
        </div>

        {/* Voice References List */}
        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            🎵 Your Voice References
          </h2>

          {voiceRefs?.voices && voiceRefs.voices.length > 0 ? (
            <div className="space-y-4">
              {voiceRefs.voices.map((voice) => (
                <div
                  key={voice.name}
                  className="flex items-center justify-between p-4 bg-gray-800/30 rounded-lg border border-gray-700/20 hover:bg-gray-800/50 transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-8 h-8 rounded-full bg-pirate-600 flex items-center justify-center">
                        <span className="text-white text-sm font-bold">
                          {voice.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white">{voice.name}</h3>
                        <p className="text-sm text-gray-400">
                          {voice.filename} • {formatFileSize(voice.size)} • Uploaded {formatDate(voice.created)}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleTestVoice(voice.name)}
                      disabled={testingVoice === voice.name}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                    >
                      {testingVoice === voice.name ? (
                        <>
                          <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                          Testing...
                        </>
                      ) : (
                        <>
                          🔊 Test Voice
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => handleDelete(voice.name)}
                      disabled={deleteMutation.isPending}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      🗑️ Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="w-24 h-24 mx-auto mb-4 opacity-30">
                🎤
              </div>
              <h3 className="text-xl font-semibold text-gray-400 mb-2">No Voice References</h3>
              <p className="text-gray-500 mb-4">
                Upload your first voice reference to start using zero-shot voice cloning
              </p>
            </div>
          )}
        </div>

        {/* Usage Instructions */}
        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            📖 How to Use Your Custom Voices
          </h2>

          <div className="space-y-4 text-gray-300">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-pirate-600 flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-white text-sm font-bold">1</span>
              </div>
              <div>
                <h3 className="font-semibold text-white mb-1">Upload Voice References</h3>
                <p className="text-sm">Upload clear audio samples of the voices you want to clone above.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-pirate-600 flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-white text-sm font-bold">2</span>
              </div>
              <div>
                <h3 className="font-semibold text-white mb-1">Test Your Voices</h3>
                <p className="text-sm">Use the "Test Voice" button to preview how your uploaded voice sounds.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-pirate-600 flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-white text-sm font-bold">3</span>
              </div>
              <div>
                <h3 className="font-semibold text-white mb-1">Configure DJ Settings</h3>
                <p className="text-sm">Go to DJ Admin → Voice & TTS Settings, set Voice Provider to "Chatterbox", and select your custom voice.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-pirate-600 flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-white text-sm font-bold">4</span>
              </div>
              <div>
                <h3 className="font-semibold text-white mb-1">Enjoy Your Custom Voice</h3>
                <p className="text-sm">Your radio commentary will now use your custom voice through zero-shot cloning!</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default VoiceCloning
