import React, { useState, useEffect } from 'react'
import api from '../utils/api'
import LoadingSpinner from './LoadingSpinner'

interface Voice {
  id: string
  name: string
  provider: 'kokoro' | 'xtts' | 'openai_tts' | 'chatterbox'
}

const VoiceTester: React.FC = () => {
  const [testingVoice, setTestingVoice] = useState<string | null>(null)
  const [audioUrls, setAudioUrls] = useState<Record<string, string>>({})
  const [testText, setTestText] = useState("Welcome to Raido FM! This is a voice test sample.")
  const [kokoroVoices, setKokoroVoices] = useState<string[]>([])
  const [xttsVoices, setXttsVoices] = useState<string[]>([])
  const [chatterboxVoices, setChatterboxVoices] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  // Popular Kokoro voices (fallback if API fails)
  const fallbackKokoroVoices = [
    'af_bella', 'af_sarah', 'af_sky', 'af_nicole', 'af_aria',
    'am_onyx', 'am_michael', 'am_ryan', 'am_alex', 'am_eric',
    'bf_emma', 'bf_alice', 'bf_lily', 'bm_george', 'bm_lewis'
  ]

  // OpenAI TTS voices
  const openaiVoices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']

  // Chatterbox fallback voices
  const fallbackChatterboxVoices = ['default', 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']

  // Fetch available voices on component mount
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        setLoading(true)
        
        // Fetch Kokoro voices
        try {
          const kokoroRes = await api.get('/admin/voices')
          const voices = kokoroRes.data?.voices || []
          setKokoroVoices(voices.slice(0, 20)) // Limit to 20 for performance
        } catch (e) {
          console.warn('Failed to fetch Kokoro voices, using fallback:', e)
          setKokoroVoices(fallbackKokoroVoices)
        }

        // Fetch XTTS voices
        try {
          const xttsRes = await api.get('/admin/voices-xtts')
          const voices = xttsRes.data?.voices || []
          // Filter to only working XTTS voices (Coqui-TTS confirmed working)
          const workingVoices = voices.filter((v: string) => 
            v.includes('coqui-tts:')
          ) // Only Coqui voices - most reliable and highest quality
          setXttsVoices(workingVoices)
        } catch (e) {
          console.warn('Failed to fetch XTTS voices:', e)
          setXttsVoices([])
        }

        // Fetch Chatterbox voices
        try {
          const chatterboxRes = await api.get('/admin/voices-chatterbox')
          const voices = chatterboxRes.data?.voices || []
          setChatterboxVoices(voices)
        } catch (e) {
          console.warn('Failed to fetch Chatterbox voices, using fallback:', e)
          setChatterboxVoices(fallbackChatterboxVoices)
        }
      } finally {
        setLoading(false)
      }
    }

    fetchVoices()
  }, [])

  const testVoice = async (voiceId: string, provider: 'kokoro' | 'xtts' | 'openai_tts' | 'chatterbox' = 'kokoro') => {
    setTestingVoice(voiceId)
    
    try {
      let payload: any = {
        text: testText,
        voice: voiceId,
        speed: 1.0,
        volume: 1.0
      }

      // Use different endpoints for different providers
      let endpoint = '/admin/tts-test' // Default for Kokoro
      if (provider === 'xtts') {
        endpoint = '/admin/tts-test-xtts'
      } else if (provider === 'chatterbox') {
        endpoint = '/admin/tts-test-chatterbox'
        // Create Chatterbox-specific payload
        payload = {
          text: testText,
          voice: voiceId,
          exaggeration: 1.0,
          cfg_weight: 0.5
        }
      }
      // Use longer timeout for TTS requests (especially Chatterbox)
      const timeout = provider === 'chatterbox' ? 300000 : 60000 // 5 min for Chatterbox, 1 min for others
      const res = await api.post(endpoint, payload, { timeout })
      if (res.data?.audio_url) {
        setAudioUrls(prev => ({
          ...prev,
          [voiceId]: res.data.audio_url
        }))
      }
    } catch (error) {
      console.error(`Failed to test voice ${voiceId}:`, error)
      alert(`Failed to test voice ${voiceId}. Please try again.`)
    } finally {
      setTestingVoice(null)
    }
  }

  const testAllKokoroVoices = async () => {
    // Test only first 5 voices to avoid overwhelming the server
    const topVoices = kokoroVoices.slice(0, 5)
    for (const voice of topVoices) {
      await testVoice(voice, 'kokoro')
      // Add delay between requests
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
  }

  const testAllXTTSVoices = async () => {
    // Test only first 3 XTTS voices
    const topVoices = xttsVoices.slice(0, 3)
    for (const voice of topVoices) {
      await testVoice(voice, 'xtts')
      // Add longer delay for XTTS
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-purple-900 p-6 flex items-center justify-center">
        <LoadingSpinner message="Loading available voices..." />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-purple-900 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl border border-gray-700 p-6 mb-6">
          <h1 className="text-3xl font-bold text-white mb-4">🎙️ TTS Voice Tester</h1>
          <p className="text-gray-300 mb-6">
            Test Kokoro, XTTS, and Chatterbox voices with custom text. Compare different voice providers and characteristics.
          </p>

          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="flex-1">
              <label className="block text-sm text-gray-300 mb-2">Test Text</label>
              <input
                type="text"
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                placeholder="Enter text to synthesize..."
              />
            </div>
            <div className="flex items-end gap-2">
              <button
                onClick={testAllKokoroVoices}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium"
                disabled={testingVoice !== null}
              >
                {testingVoice ? 'Testing...' : 'Test Top 5 Kokoro'}
              </button>
              {xttsVoices.length > 0 && (
                <button
                  onClick={testAllXTTSVoices}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-medium"
                  disabled={testingVoice !== null}
                >
                  {testingVoice ? 'Testing...' : 'Test Top 3 XTTS'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Kokoro Voices */}
        <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl border border-gray-700 p-6 mb-6">
          <h2 className="text-2xl font-bold text-white mb-4">
            🧠 Kokoro Voices (Neural TTS)
            <span className="ml-2 text-sm text-gray-400">({kokoroVoices.length} voices)</span>
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {kokoroVoices.map((voice) => (
              <div key={voice} className="bg-gray-700/50 rounded-lg p-4 border border-gray-600">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white">{voice}</h3>
                  <span className="text-xs px-2 py-1 bg-blue-600 text-white rounded">
                    kokoro
                  </span>
                </div>
                
                <div className="flex gap-2 mb-3">
                  <button
                    onClick={() => testVoice(voice, 'kokoro')}
                    disabled={testingVoice === voice}
                    className="flex-1 px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-sm rounded"
                  >
                    {testingVoice === voice ? (
                      <div className="flex items-center justify-center">
                        <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin mr-1"></div>
                        <span>Testing...</span>
                      </div>
                    ) : 'Test Voice'}
                  </button>
                </div>
                
                {audioUrls[voice] && (
                  <div className="mt-3">
                    <audio controls className="w-full">
                      <source src={audioUrls[voice]} type="audio/mpeg" />
                      Your browser does not support the audio element.
                    </audio>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* XTTS Voices */}
        {xttsVoices.length > 0 && (
          <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl border border-gray-700 p-6 mb-6">
            <h2 className="text-2xl font-bold text-white mb-4">
              🗣️ XTTS Voices (OpenTTS)
              <span className="ml-2 text-sm text-gray-400">({xttsVoices.length} voices)</span>
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {xttsVoices.map((voice) => (
                <div key={voice} className="bg-gray-700/50 rounded-lg p-4 border border-gray-600">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-white text-sm">{voice}</h3>
                    <span className="text-xs px-2 py-1 bg-green-600 text-white rounded">
                      xtts
                    </span>
                  </div>
                  
                  <div className="flex gap-2 mb-3">
                    <button
                      onClick={() => testVoice(voice, 'xtts')}
                      disabled={testingVoice === voice}
                      className="flex-1 px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white text-sm rounded"
                    >
                      {testingVoice === voice ? (
                        <div className="flex items-center justify-center">
                          <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin mr-1"></div>
                          <span>Testing...</span>
                        </div>
                      ) : 'Test Voice'}
                    </button>
                  </div>
                  
                  {audioUrls[voice] && (
                    <div className="mt-3">
                      <audio controls className="w-full">
                        <source src={audioUrls[voice]} type="audio/wav" />
                        <source src={audioUrls[voice]} type="audio/mpeg" />
                        Your browser does not support the audio element.
                      </audio>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chatterbox Voices */}
        <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl border border-gray-700 p-6 mb-6">
          <h2 className="text-2xl font-bold text-white mb-4">
            🎭 Chatterbox TTS Voices (Neural)
            <span className="ml-2 text-sm text-gray-400">({chatterboxVoices.length} voices)</span>
          </h2>
          <p className="text-sm text-yellow-400 mb-4">
            ⏳ Note: Chatterbox generates high-quality neural audio but takes 2-3 minutes per test on CPU
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {chatterboxVoices.map((voice) => (
              <div key={voice} className="bg-gray-700/50 rounded-lg p-4 border border-gray-600">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white">{voice}</h3>
                  <span className="text-xs px-2 py-1 bg-purple-600 text-white rounded">
                    chatterbox
                  </span>
                </div>
                
                <div className="flex gap-2 mb-3">
                  <button
                    onClick={() => testVoice(voice, 'chatterbox')}
                    disabled={testingVoice === voice}
                    className="flex-1 px-3 py-1 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white text-sm rounded"
                  >
                    {testingVoice === voice ? (
                      <div className="flex items-center justify-center">
                        <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin mr-1"></div>
                        <span>Testing...</span>
                      </div>
                    ) : 'Test Voice'}
                  </button>
                </div>
                
                {audioUrls[voice] && (
                  <div className="mt-3">
                    <audio controls className="w-full">
                      <source src={audioUrls[voice]} type="audio/mpeg" />
                      Your browser does not support the audio element.
                    </audio>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* OpenAI TTS Voices */}
        <div className="bg-gray-800/60 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
          <h2 className="text-2xl font-bold text-white mb-4">
            🤖 OpenAI TTS Voices
            <span className="ml-2 text-sm text-gray-400">(requires API key)</span>
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {openaiVoices.map((voice) => (
              <div key={voice} className="bg-gray-700/50 rounded-lg p-4 border border-gray-600 opacity-50">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white">{voice}</h3>
                  <span className="text-xs px-2 py-1 bg-purple-600 text-white rounded">
                    openai
                  </span>
                </div>
                
                <div className="flex gap-2 mb-3">
                  <button
                    disabled
                    className="flex-1 px-3 py-1 bg-gray-600 text-gray-400 text-sm rounded cursor-not-allowed"
                  >
                    API Required
                  </button>
                </div>
                
                <p className="text-xs text-yellow-400">
                  Requires OpenAI API key and costs per request
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default VoiceTester