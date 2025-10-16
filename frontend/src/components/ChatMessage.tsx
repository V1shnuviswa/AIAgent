import { formatDate } from '../utils'

interface ChatMessageProps {
  message: {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: string
    isLoading?: boolean
  }
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`chat-message flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] ${isUser ? 'chat-bubble-user' : 'chat-bubble-bot'}`}>
        {isUser ? (
          <p className="text-white whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="text-gray-800">
            <div className="whitespace-pre-wrap">
              {message.content}
            </div>
          </div>
        )}
        
        {/* Timestamp */}
        <div className={`text-xs mt-1 ${isUser ? 'text-primary-100' : 'text-gray-500'}`}>
          {formatDate(message.timestamp)}
        </div>
      </div>
    </div>
  )
}
