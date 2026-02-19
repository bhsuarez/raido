import React from 'react'

interface LoadingSkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string
  height?: string
  lines?: number
}

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  className = '',
  variant = 'rectangular',
  width = 'w-full',
  height = 'h-4',
  lines = 1
}) => {
  const baseClasses = 'animate-pulse bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 bg-[length:200%_100%]'
  
  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg'
  }

  if (variant === 'text' && lines > 1) {
    return (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={`${baseClasses} ${variantClasses.text} ${width} ${height} ${
              index === lines - 1 ? 'w-3/4' : ''
            }`}
            style={{
              animationDelay: `${index * 0.1}s`,
              animation: 'pulse 1.5s ease-in-out infinite, shimmer 2s ease-in-out infinite'
            }}
          />
        ))}
      </div>
    )
  }

  return (
    <div
      className={`${baseClasses} ${variantClasses[variant]} ${width} ${height} ${className}`}
      style={{
        animation: 'pulse 1.5s ease-in-out infinite, shimmer 2s ease-in-out infinite'
      }}
    />
  )
}

// Specific skeleton components for common use cases
export const NowPlayingSkeleton: React.FC = () => (
  <div className="card overflow-hidden animate-pulse">
    <div className="flex flex-col lg:flex-row">
      {/* Art skeleton */}
      <div className="lg:w-72 lg:flex-shrink-0 aspect-square lg:h-72 bg-gray-800" />
      {/* Info skeleton */}
      <div className="flex-1 p-5 lg:p-7 space-y-5">
        <div className="space-y-2">
          <div className="h-3 bg-gray-800 rounded w-20" />
          <div className="h-7 bg-gray-800 rounded w-3/4 mt-2" />
          <div className="h-5 bg-gray-800 rounded w-1/2" />
          <div className="h-5 bg-gray-800 rounded w-24 rounded-full" />
        </div>
        <div className="space-y-2">
          <div className="h-1.5 bg-gray-800 rounded-full w-full" />
          <div className="flex justify-between">
            <div className="h-3 bg-gray-800 rounded w-8" />
            <div className="h-3 bg-gray-800 rounded w-8" />
          </div>
        </div>
        <div className="h-10 bg-gray-800 rounded-xl w-32" />
      </div>
    </div>
  </div>
)

export const AnalyticsCardSkeleton: React.FC = () => (
  <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
    <div className="flex items-center justify-between mb-6">
      <LoadingSkeleton width="w-48" height="h-8" />
      <LoadingSkeleton width="w-32" height="h-8" />
    </div>
    
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="space-y-2">
          <div className="flex items-center justify-between">
            <LoadingSkeleton width="w-32" height="h-6" />
            <LoadingSkeleton width="w-20" height="h-4" />
          </div>
          <LoadingSkeleton width="w-full" height="h-3" />
        </div>
      ))}
    </div>
  </div>
)

export default LoadingSkeleton