/**
 * WebSocket client for real-time event streaming.
 */

import type { WinterFoxEvent } from '../types/api';

type EventHandler = (event: WinterFoxEvent) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Set<EventHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private url: string;
  private shouldReconnect = true;

  constructor(workspaceId: string = 'default') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    this.url = `${protocol}//${host}/ws/events?workspace_id=${workspaceId}`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    console.log('Connecting to WebSocket:', this.url);

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WinterFoxEvent;
          console.log('WebSocket event:', data.type, data.data);

          // Notify all handlers
          this.handlers.forEach((handler) => {
            try {
              handler(data);
            } catch (error) {
              console.error('Error in event handler:', error);
            }
          });
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.ws = null;

        // Attempt reconnect
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

          console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

          setTimeout(() => {
            this.connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  subscribe(handler: EventHandler): () => void {
    this.handlers.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.delete(handler);
    };
  }

  send(message: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  ping(): void {
    this.send('ping');
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient();
export default wsClient;
