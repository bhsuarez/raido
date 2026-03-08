import { useEffect } from 'react'

function rgbToHsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  let h = 0, s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break
      case g: h = ((b - r) / d + 2) / 6; break
      case b: h = ((r - g) / d + 4) / 6; break
    }
  }
  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)]
}

function applyArtColors(h: number, s: number, _l: number) {
  const bgS = Math.max(s * 0.35, 8)
  const bgL = 7
  const accentS = Math.min(s * 0.9 + 20, 90)
  const accentL = 62
  const root = document.documentElement
  root.style.setProperty('--art-bg',     `hsl(${h}, ${bgS}%, ${bgL}%)`)
  root.style.setProperty('--art-accent', `hsl(${h}, ${accentS}%, ${accentL}%)`)
  root.style.setProperty('--art-h',      String(h))
  root.style.setProperty('--art-s',      `${Math.round(s * 0.6)}%`)
}

function resetArtColors() {
  const root = document.documentElement
  root.style.setProperty('--art-bg',     'hsl(230, 15%, 7%)')
  root.style.setProperty('--art-accent', 'hsl(200, 70%, 62%)')
  root.style.setProperty('--art-h',      '230')
  root.style.setProperty('--art-s',      '15%')
}

export function useArtColor(artworkUrl: string | null | undefined) {
  useEffect(() => {
    if (!artworkUrl) {
      resetArtColors()
      return
    }

    const img = new Image()
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      try {
        const SIZE = 40
        const canvas = document.createElement('canvas')
        canvas.width = SIZE
        canvas.height = SIZE
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        ctx.drawImage(img, 0, 0, SIZE, SIZE)
        const { data } = ctx.getImageData(0, 0, SIZE, SIZE)

        let r = 0, g = 0, b = 0, count = 0
        for (let i = 0; i < data.length; i += 4) {
          const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3
          if (brightness < 15 || brightness > 240) continue
          r += data[i]; g += data[i + 1]; b += data[i + 2]
          count++
        }
        if (count === 0) { resetArtColors(); return }
        const [h, s, l] = rgbToHsl(
          Math.round(r / count),
          Math.round(g / count),
          Math.round(b / count)
        )
        applyArtColors(h, s, l)
      } catch {
        resetArtColors()
      }
    }

    img.onerror = resetArtColors
    img.src = artworkUrl
  }, [artworkUrl])
}
