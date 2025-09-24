import React from 'react'
import LoadingSpinner from './LoadingSpinner'

const AuthCallback: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <LoadingSpinner message="Completing sign in..." />
    </div>
  )
}

export default AuthCallback
