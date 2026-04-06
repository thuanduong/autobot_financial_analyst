export interface Candle {
  time: number;   // Unix timestamp (seconds)
  open: number;
  high: number;
  low: number;
  close: number;
  value?: number; // Volume
}

export interface Marker {
  time: number;
  position: 'aboveBar' | 'belowBar' | 'inBar';
  color: string;
  shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown';
  text: string;
  size: number;
  strategy_id: string; 
  outcome?: string;
}

export interface WebSocketMessage {
  type: string;
  symbol: string;
  tf: string;
  data: Candle | Candle[];
}