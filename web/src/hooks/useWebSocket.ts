import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import { useRadioStore } from '../store/radioStore'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()
  const { setIsConnected, updateNowPlaying } = useRadioStore()
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  const connect = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws`
      
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('🏴‍☠️ WebSocket connected')
        setIsConnected(true)
        // If we had previous failed attempts, celebrate the reconnect before resetting
        if (reconnectAttempts.current > 0) {
          toast.success('🏴‍☠️ Reconnected to the radio!')
        }
        reconnectAttempts.current = 0
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          
          switch (message.type) {
            case 'now_playing':
            case 'track_change':
              updateNowPlaying(message.data)
              queryClient.invalidateQueries({ queryKey: ['nowPlaying'] })
              queryClient.invalidateQueries({ queryKey: ['nextUp'] })
              queryClient.invalidateQueries({ queryKey: ['history'] })
              break
              
            case 'commentary':
              toast('🗣️ New DJ commentary!', {
                icon: '🎙️',
                duration: 3000
              })
              queryClient.invalidateQueries({ queryKey: ['history'] })
              break
              
            default:
              console.log('Unknown WebSocket message type:', message.type)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setIsConnected(false)
        
        // Attempt to reconnect if not a normal close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          reconnectAttempts.current++
          
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          toast.error('🏴‍☠️ Lost connection to the radio. Please refresh.')
        }
      }

      wsRef.current.onerror = (error) => {
        // Errors can fire during normal reloads or transient reconnects; log only.
        console.error('WebSocket error:', error)
      }

    } catch (error) {
      console.error('Error creating WebSocket:', error)
      setIsConnected(false)
    }
  }

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting')
      }
    }
  }, [])

  return {
    isConnected: useRadioStore(state => state.isConnected),
    reconnect: connect
  }
}
