import { useState, useEffect, useCallback } from 'react'
import { apiClient, type ChatMessage } from '../utils/api'
import { getStoredValue, setStoredValue, getErrorMessage } from '../utils'
import toast from 'react-hot-toast'

interface ChatState {
  messages: Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: string
    isLoading?: boolean
  }>
  sessionId: string | null
  isConnected: boolean
  isLoading: boolean
  error: string | null
}

export function useChat() {
  const [state, setState] = useState<ChatState>({
    messages: getStoredValue('chat_messages', []),
    sessionId: getStoredValue('session_id', null),
    isConnected: false,
    isLoading: false,
    error: null,
  })

  // Save messages to localStorage
  useEffect(() => {
    setStoredValue('chat_messages', state.messages)
  }, [state.messages])

  // Save session ID to localStorage
  useEffect(() => {
    if (state.sessionId) {
      setStoredValue('session_id', state.sessionId)
    }
  }, [state.sessionId])

  const createSession = useCallback(async (userName?: string) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }))
      
      const response = await apiClient.createSession({ user_name: userName })
      setState(prev => ({
        ...prev,
        sessionId: response.session_id,
        isConnected: true,
        isLoading: false,
      }))
      
      toast.success('Session created successfully!')
      return response.session_id
    } catch (error) {
      const errorMessage = getErrorMessage(error)
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }))
      toast.error(`Failed to create session: ${errorMessage}`)
      throw error
    }
  }, [])

  const sendMessage = useCallback(async (message: string, userName?: string) => {
    if (!message.trim()) return

    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    // Add user message immediately
    const userMessage = {
      id: messageId,
      role: 'user' as const,
      content: message.trim(),
      timestamp: new Date().toISOString(),
    }

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null,
    }))

    try {
      const chatMessage: ChatMessage = {
        message: message.trim(),
        session_id: state.sessionId || undefined,
        user_name: userName,
      }

      const response = await apiClient.sendMessage(chatMessage)

      // Update session ID if it's new
      if (response.session_id !== state.sessionId) {
        setState(prev => ({ ...prev, sessionId: response.session_id }))
      }

      // Add assistant response
      const assistantMessage = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        role: 'assistant' as const,
        content: response.response,
        timestamp: response.timestamp,
      }

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
        isLoading: false,
        isConnected: true,
      }))

    } catch (error) {
      const errorMessage = getErrorMessage(error)
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }))
      
      // Add error message
      const errorMsg = {
        id: `error_${Date.now()}`,
        role: 'assistant' as const,
        content: `Sorry, I encountered an error: ${errorMessage}. Please try again.`,
        timestamp: new Date().toISOString(),
      }

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, errorMsg],
      }))

      toast.error(`Failed to send message: ${errorMessage}`)
    }
  }, [state.sessionId])

  const clearChat = useCallback(() => {
    setState(prev => ({
      ...prev,
      messages: [],
      error: null,
    }))
    setStoredValue('chat_messages', [])
    toast.success('Chat cleared')
  }, [])

  const resetSession = useCallback(async () => {
    try {
      if (state.sessionId) {
        await apiClient.deleteSession(state.sessionId)
      }
    } catch (error) {
      console.error('Error deleting session:', error)
    }

    setState({
      messages: [],
      sessionId: null,
      isConnected: false,
      isLoading: false,
      error: null,
    })
    
    setStoredValue('chat_messages', [])
    setStoredValue('session_id', null)
    toast.success('Session reset')
  }, [state.sessionId])

  return {
    messages: state.messages,
    sessionId: state.sessionId,
    isConnected: state.isConnected,
    isLoading: state.isLoading,
    error: state.error,
    sendMessage,
    createSession,
    clearChat,
    resetSession,
  }
}
