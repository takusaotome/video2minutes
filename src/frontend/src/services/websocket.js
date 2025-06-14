class WebSocketManager {
  constructor() {
    this.connections = new Map()
    this.listeners = new Map()
  }

  connect(taskId, callbacks = {}) {
    if (this.connections.has(taskId)) {
      return this.connections.get(taskId)
    }

    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/v1/minutes/ws/${taskId}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log(`WebSocket connected for task ${taskId}`)
      callbacks.onOpen?.(taskId)
    }

    ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data)
        console.log(`WebSocket message for task ${taskId}:`, data)
        callbacks.onMessage?.(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onclose = () => {
      console.log(`WebSocket closed for task ${taskId}`)
      this.connections.delete(taskId)
      callbacks.onClose?.(taskId)
    }

    ws.onerror = error => {
      console.error(`WebSocket error for task ${taskId}:`, error)
      callbacks.onError?.(error)
    }

    this.connections.set(taskId, ws)
    return ws
  }

  disconnect(taskId) {
    const ws = this.connections.get(taskId)
    if (ws) {
      ws.close()
      this.connections.delete(taskId)
    }
  }

  disconnectAll() {
    this.connections.forEach((ws, taskId) => {
      ws.close()
    })
    this.connections.clear()
  }

  isConnected(taskId) {
    const ws = this.connections.get(taskId)
    return ws && ws.readyState === WebSocket.OPEN
  }
}

export default new WebSocketManager()
