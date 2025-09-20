import React from 'react'
import LoadingSpinner from './LoadingSpinner'
import { useRaidoAuth } from '../providers/AuthProvider'

interface AuthGuardProps {
  children: React.ReactNode
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { isEnabled, isAuthenticated, isLoading, error, signin } = useRaidoAuth()

  if (!isEnabled) {
    return <>{children}</>
  }

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <LoadingSpinner message="Checking authentication..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="bg-gray-800 border border-red-500/50 rounded-2xl p-8 text-center max-w-md">
          <h2 className="text-xl font-semibold text-red-300 mb-2">Authentication Error</h2>
          <p className="text-gray-300 mb-4">
            We couldn't verify your Authentik session. Please try signing in again.
          </p>
          <button
            onClick={signin}
            className="px-6 py-2 rounded-lg bg-pirate-600 hover:bg-pirate-500 text-white transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="bg-gray-800 border border-gray-700 rounded-2xl p-8 text-center max-w-md">
          <h2 className="text-2xl font-bold text-white mb-3">Sign in required</h2>
          <p className="text-gray-300 mb-6">
            Use your Authentik account to access the Raido control room and analytics dashboards.
          </p>
          <button
            onClick={signin}
            className="px-6 py-2 rounded-lg bg-pirate-600 hover:bg-pirate-500 text-white transition-colors"
          >
            Sign in with Authentik
          </button>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

export default AuthGuard
