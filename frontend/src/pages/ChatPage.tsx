import { useState, useRef, useEffect } from 'react'
import { PaperAirplaneIcon, TrashIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { useChat } from '../hooks/useChat'
import ChatMessage from '../components/ChatMessage'
import LoadingSpinner from '../components/LoadingSpinner'

export default function ChatPage() {
  const [input, setInput] = useState('')
  const [userName, setUserName] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  
  const {
    messages,
    sessionId,
    isConnected,
    isLoading,
    error,
    sendMessage,
    clearChat,
    resetSession,
  } = useChat()

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on load
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!input.trim() || isLoading) return

    const message = input.trim()
    setInput('')
    
    await sendMessage(message, userName || undefined)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const isFirstTime = messages.length === 0

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Welcome message for first-time users */}
      {isFirstTime && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-4l-4 4v-4z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Welcome to MF Agent
            </h2>
            <p className="text-gray-600 mb-6">
              Your AI-powered mutual funds assistant. Ask me anything about mutual funds, 
              fund performance, investment strategies, or get personalized recommendations.
            </p>
            
            {/* Optional name input */}
            <div className="mb-4">
              <input
                type="text"
                placeholder="Your name (optional)"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                className="input-field text-center"
                maxLength={50}
              />
            </div>
            
            <div className="space-y-2 text-sm text-gray-500">
              <p>Try asking:</p>
              <ul className="space-y-1">
                <li>"What is the NAV of SBI Bluechip Fund?"</li>
                <li>"Compare HDFC Top 100 with ICICI Focused Fund"</li>
                <li>"Best large cap funds for long term investment"</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Messages area */}
      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Session info */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-gray-500">
                {isConnected ? 'Connected' : 'Disconnected'}
                {sessionId && ` • Session: ${sessionId.substring(0, 8)}...`}
              </span>
            </div>
            
            <div className="flex space-x-2">
              <button
                onClick={clearChat}
                className="flex items-center px-3 py-1 text-sm text-gray-600 hover:text-red-600 transition-colors"
                title="Clear chat"
              >
                <TrashIcon className="w-4 h-4 mr-1" />
                Clear
              </button>
              <button
                onClick={resetSession}
                className="flex items-center px-3 py-1 text-sm text-gray-600 hover:text-blue-600 transition-colors"
                title="Reset session"
              >
                <ArrowPathIcon className="w-4 h-4 mr-1" />
                Reset
              </button>
            </div>
          </div>

          {/* Messages */}
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
            />
          ))}
          
          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="chat-bubble-bot flex items-center space-x-2">
                <LoadingSpinner size="small" />
                <span className="text-gray-500">AI is thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mx-4 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white p-4">
        <form onSubmit={handleSubmit} className="flex space-x-4">
          <div className="flex-1">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything about mutual funds..."
              rows={1}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              style={{ minHeight: '44px', maxHeight: '120px' }}
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center px-4 py-2"
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </form>
        
        <div className="mt-2 text-xs text-gray-500 text-center">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  )
}
