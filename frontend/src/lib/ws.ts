/** Browser WebSocket client for per-show LangGraph progress. */

export class ShowWebSocket {
  private ws: WebSocket | null = null;

  constructor(
    private readonly baseUrl: string,
    private readonly showId: string,
  ) {}

  /** Open connection; ``baseUrl`` must be ``host:port`` without a scheme. */
  connect(onMessage: (data: unknown) => void): void {
    const url = `ws://${this.baseUrl}/ws/shows/${this.showId}`;
    this.ws = new WebSocket(url);
    this.ws.onmessage = (event: MessageEvent<string>) => {
      try {
        onMessage(JSON.parse(event.data) as unknown);
      } catch {
        onMessage(event.data);
      }
    };
    this.ws.onerror = () => {
      this.disconnect();
    };
  }

  disconnect(): void {
    this.ws?.close();
    this.ws = null;
  }
}
