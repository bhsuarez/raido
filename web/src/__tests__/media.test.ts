import { describe, it, expect, beforeEach } from 'vitest'
import { resolveMediaUrl } from '../utils/media'

describe('resolveMediaUrl', () => {
  const oldEnv = (import.meta as any).env

  beforeEach(() => {
    ;(import.meta as any).env = { ...oldEnv }
  })

  it('returns null for empty', () => {
    expect(resolveMediaUrl(undefined)).toBeNull()
    expect(resolveMediaUrl(null as unknown as string)).toBeNull()
  })

  it('passes through absolute URLs', () => {
    expect(resolveMediaUrl('http://x/y')).toBe('http://x/y')
    expect(resolveMediaUrl('https://x/y')).toBe('https://x/y')
  })

  it('prefixes API origin for /static paths', () => {
    ;(import.meta as any).env.VITE_API_URL = 'http://api.local/'
    expect(resolveMediaUrl('/static/tts/a.mp3')).toBe('http://api.local/static/tts/a.mp3')
  })

  it('leaves relative non-static paths unchanged', () => {
    ;(import.meta as any).env.VITE_API_URL = 'http://api.local/'
    expect(resolveMediaUrl('/img/x.png')).toBe('/img/x.png')
  })
})

