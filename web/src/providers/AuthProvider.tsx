import React, { createContext, useCallback, useContext, useEffect, useMemo } from 'react'
import { AuthProvider as OidcAuthProvider, AuthProviderProps, useAuth } from 'react-oidc-context'
import { WebStorageStateStore, User } from 'oidc-client-ts'

import { setAccessToken, setUnauthorizedHandler } from '../utils/authTokens'

interface AuthContextValue {
  isEnabled: boolean
  isAuthenticated: boolean
  isLoading: boolean
  user: User | null
  accessToken: string | null
  error: Error | null
  signin: () => void
  signout: () => void
  refresh: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

function useEnvConfig() {
  const env = (import.meta as any)?.env ?? {}
  const authority = env.VITE_OIDC_AUTHORITY || env.VITE_AUTHENTIK_ISSUER || env.VITE_AUTHENTIK_AUTHORITY
  const clientId = env.VITE_OIDC_CLIENT_ID || env.VITE_AUTHENTIK_CLIENT_ID
  const scope = env.VITE_OIDC_SCOPE || 'openid profile email'
  const defaultOrigin = typeof window !== 'undefined' ? window.location.origin : undefined
  const redirectUri = env.VITE_OIDC_REDIRECT_URI || (defaultOrigin ? `${defaultOrigin}/auth/callback` : undefined)
  const postLogoutRedirectUri = env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI || defaultOrigin

  return {
    enabled: Boolean(authority && clientId && redirectUri),
    authority,
    clientId,
    scope,
    redirectUri,
    postLogoutRedirectUri,
  }
}

const DisabledAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  useEffect(() => {
    setAccessToken(null)
    setUnauthorizedHandler(null)
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    isEnabled: false,
    isAuthenticated: true,
    isLoading: false,
    user: null,
    accessToken: null,
    error: null,
    signin: () => {},
    signout: () => {},
    refresh: () => {},
  }), [])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

const OidcBridge: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const auth = useAuth()

  const signin = useCallback(() => {
    auth.signinRedirect()
  }, [auth])

  const signout = useCallback(() => {
    auth.signoutRedirect()
  }, [auth])

  const refresh = useCallback(() => {
    auth.signinSilent().catch(() => {
      auth.signinRedirect()
    })
  }, [auth])

  useEffect(() => {
    setAccessToken(auth.user?.access_token ?? null)
    return () => {
      setAccessToken(null)
    }
  }, [auth.user])

  useEffect(() => {
    const handler = () => {
      auth.removeUser().catch(() => undefined)
      auth.signinRedirect()
    }
    setUnauthorizedHandler(handler)
    return () => setUnauthorizedHandler(null)
  }, [auth])

  const value = useMemo<AuthContextValue>(() => ({
    isEnabled: true,
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.isLoading,
    user: auth.user ?? null,
    accessToken: auth.user?.access_token ?? null,
    error: auth.error ?? null,
    signin,
    signout,
    refresh,
  }), [auth.error, auth.isAuthenticated, auth.isLoading, auth.user, refresh, signin, signout])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const RaidoAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const config = useEnvConfig()

  const userStore = useMemo(() => {
    if (typeof window === 'undefined') {
      return undefined
    }
    return new WebStorageStateStore({ store: window.localStorage, prefix: 'raido_auth' })
  }, [])

  const oidcProps = useMemo<AuthProviderProps | null>(() => {
    if (!config.enabled) {
      return null
    }

    return {
      authority: config.authority!,
      client_id: config.clientId!,
      redirect_uri: config.redirectUri!,
      post_logout_redirect_uri: config.postLogoutRedirectUri || config.redirectUri!,
      scope: config.scope,
      loadUserInfo: true,
      automaticSilentRenew: true,
      userStore,
      onSigninCallback: () => {
        if (typeof window !== 'undefined') {
          const newUrl = window.location.pathname + window.location.hash
          window.history.replaceState({}, document.title, newUrl)
        }
      },
    }
  }, [config.enabled, config.authority, config.clientId, config.postLogoutRedirectUri, config.redirectUri, config.scope, userStore])

  if (!config.enabled || !oidcProps) {
    return (
      <DisabledAuthProvider>
        {children}
      </DisabledAuthProvider>
    )
  }

  return (
    <OidcAuthProvider {...oidcProps}>
      <OidcBridge>
        {children}
      </OidcBridge>
    </OidcAuthProvider>
  )
}

export function useRaidoAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useRaidoAuth must be used within a RaidoAuthProvider')
  }
  return context
}
