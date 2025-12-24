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
  <div className="bg-gradient-to-br from-pirate-900 via-pirate-800 to-gray-800 rounded-2xl p-8 shadow-2xl border border-pirate-600/30">
    {/* Header Skeleton */}
    <div className="flex items-center justify-between mb-8">
      <div className="flex items-center gap-3">
        <LoadingSkeleton variant="circular" width="w-3" height="h-3" />
        <LoadingSkeleton width="w-64" height="h-8" />
      </div>
      <LoadingSkeleton width="w-24" height="h-6" />
    </div>

    {/* Main Content Skeleton */}
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
      {/* Album Art Skeleton */}
      <div className="lg:col-span-1">
        <LoadingSkeleton 
          variant="rectangular" 
          className="w-full max-w-sm mx-auto lg:max-w-none aspect-square" 
        />
      </div>

      {/* Track Info Skeleton */}
      <div className="lg:col-span-2 space-y-6">
        <div className="space-y-4">
          <LoadingSkeleton width="w-full" height="h-8" />
          <LoadingSkeleton width="w-3/4" height="h-6" />
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
            <LoadingSkeleton width="w-20" height="h-6" />
            <LoadingSkeleton width="w-32" height="h-4" />
          </div>
        </div>

        {/* Progress Bar Skeleton */}
        <div className="space-y-3">
          <div className="flex justify-between">
            <LoadingSkeleton width="w-12" height="h-4" />
            <LoadingSkeleton width="w-12" height="h-4" />
          </div>
          <LoadingSkeleton width="w-full" height="h-3" />
        </div>

        {/* Button Skeleton */}
        <div className="flex justify-center pt-4">
          <LoadingSkeleton width="w-32" height="h-12" />
        </div>
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