import React, { useEffect, useState } from 'react'

interface Snowflake {
  id: number
  left: number
  animationDuration: number
  opacity: number
  size: number
}

const Snowfall: React.FC = () => {
  const [snowflakes, setSnowflakes] = useState<Snowflake[]>([])

  useEffect(() => {
    // Create 50 snowflakes with random properties
    const flakes: Snowflake[] = Array.from({ length: 50 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      animationDuration: 10 + Math.random() * 20, // 10-30 seconds
      opacity: 0.3 + Math.random() * 0.7,
      size: 0.5 + Math.random() * 1.5, // 0.5em to 2em
    }))
    setSnowflakes(flakes)
  }, [])

  return (
    <>
      {snowflakes.map((flake) => (
        <div
          key={flake.id}
          className="snowflake"
          style={{
            left: `${flake.left}%`,
            animationDuration: `${flake.animationDuration}s`,
            animationDelay: `${Math.random() * 5}s`,
            opacity: flake.opacity,
            fontSize: `${flake.size}em`,
          }}
        >
          ❄
        </div>
      ))}
      <div className="frost-overlay" />
    </>
  )
}

export default Snowfall
