// Helpers for media URLs (artwork, audio) to handle API origin

const RAW_API_URL = (import.meta as any)?.env?.VITE_API_URL
  ? String((import.meta as any).env.VITE_API_URL).replace(/\/$/, '')
  : ''

export function resolveMediaUrl(pathOrUrl?: string | null): string | null {
  if (!pathOrUrl) return null
  // Absolute URL -> return as-is
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl
  // If it is an API-served static path and we know API origin, prefix it
  if (pathOrUrl.startsWith('/static/') && RAW_API_URL) {
    return `${RAW_API_URL}${pathOrUrl}`
  }
  // Otherwise return unchanged (dev proxy or same-origin cases)
  return pathOrUrl
}

