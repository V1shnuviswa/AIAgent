import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface ChatMessage {
  message: string
  session_id?: string
  user_name?: string
}

export interface ChatResponse {
  response: string
  session_id: string
  timestamp: string
  confidence?: number
}

export interface SessionRequest {
  user_name?: string
}

export interface SessionResponse {
  session_id: string
  user_name?: string
  timestamp: string
}

export interface FundSearchRequest {
  fund_name: string
  search_type?: string
}

export interface FundSearchResponse {
  found: boolean
  results: any[]
  confidence: number
  source: string
  error?: string
}

export interface ConversationHistory {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface SessionInfo {
  session_id: string
  user_name?: string
  conversation_history: ConversationHistory[]
  created_at?: string
}

class ApiClient {
  private client = axios.create({
    baseURL: API_BASE_URL,
    timeout: 90000, // Increased to 90 seconds to match agent timeout (70s + 20s buffer)
    headers: {
      'Content-Type': 'application/json',
    },
  })

  constructor() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`)
        return config
      },
      (error) => {
        console.error('Request error:', error)
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log(`Response from ${response.config.url}:`, response.status)
        return response
      },
      (error) => {
        console.error('Response error:', error.response?.data || error.message)
        return Promise.reject(error)
      }
    )
  }

  // Session management
  async createSession(request: SessionRequest): Promise<SessionResponse> {
    const response = await this.client.post<SessionResponse>('/api/session', request)
    return response.data
  }

  async getSession(sessionId: string): Promise<SessionInfo> {
    const response = await this.client.get<SessionInfo>(`/api/session/${sessionId}`)
    return response.data
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/api/session/${sessionId}`)
  }

  // Chat functionality
  async sendMessage(message: ChatMessage): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/api/chat', message)
    return response.data
  }

  // Fund search
  async searchFunds(request: FundSearchRequest): Promise<FundSearchResponse> {
    const response = await this.client.post<FundSearchResponse>('/api/funds/search', request)
    return response.data
  }

  // Health check
  async healthCheck(): Promise<any> {
    const response = await this.client.get('/api/health')
    return response.data
  }

  // Get API base URL for WebSocket connections
  getWebSocketUrl(): string {
    return API_BASE_URL.replace('http', 'ws')
  }
}

export const apiClient = new ApiClient()

// WebSocket manager for real-time chat
export class WebSocketManager {
  private ws: WebSocket | null = null
  private sessionId: string | null = null
  private onMessageCallback?: (data: any) => void
  private onErrorCallback?: (error: any) => void
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3

  connect(sessionId: string, onMessage: (data: any) => void, onError?: (error: any) => void) {
    this.sessionId = sessionId
    this.onMessageCallback = onMessage
    this.onErrorCallback = onError

    const wsUrl = `${apiClient.getWebSocketUrl()}/ws/${sessionId}`
    console.log(`Connecting to WebSocket: ${wsUrl}`)

    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('WebSocket message received:', data)
        if (this.onMessageCallback) {
          this.onMessageCallback(data)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      if (this.onErrorCallback) {
        this.onErrorCallback(error)
      }
    }

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason)
      
      // Try to reconnect if not intentionally closed
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
        setTimeout(() => {
          if (this.sessionId) {
            this.connect(this.sessionId, this.onMessageCallback!, this.onErrorCallback)
          }
        }, 2000 * this.reconnectAttempts) // Exponential backoff
      }
    }
  }

  sendMessage(message: string, userName?: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const data = {
        message,
        user_name: userName,
        timestamp: new Date().toISOString()
      }
      console.log('Sending WebSocket message:', data)
      this.ws.send(JSON.stringify(data))
    } else {
      console.error('WebSocket is not connected')
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'User disconnected')
      this.ws = null
    }
    this.sessionId = null
    this.onMessageCallback = undefined
    this.onErrorCallback = undefined
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const webSocketManager = new WebSocketManager()
