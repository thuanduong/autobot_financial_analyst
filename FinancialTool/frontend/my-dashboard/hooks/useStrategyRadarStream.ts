import { useState, useEffect, useCallback } from 'react';
import { useSocket } from '@/app/context/SocketContext';
import { getSymbolShortName } from "@/config/symbols";
import { tradeApi } from "@/services/tradeApi";

export interface StrategyResult {
  strategy_name: string;
  signal: 'BUY' | 'SELL' | 'NEUTRAL';
  score: number;
  reason: string;
  sl?: number;
  tp?: number;
  timestamp?: number;
}

export type RadarMatrix = Record<string, Record<string, StrategyResult>>; // { [StrategyName]: { [TF]: Data } }

export const useStrategyRadarStream = (symbol: string) => {
  // State lưu trữ toàn bộ matrix của tất cả các cặp tiền để làm cache
  const [cache, setCache] = useState<Record<string, RadarMatrix>>({});
  const { subscribe, unsubscribe } = useSocket();

  // Helper biến đổi dữ liệu từ Backend (TF -> Array) sang Frontend (Strategy -> TF)
  const transformData = useCallback((symbolData: any) => {
    const matrix: RadarMatrix = {};
    Object.entries(symbolData).forEach(([tf, strategies]) => {
      (strategies as StrategyResult[]).forEach((strat) => {
        if (!matrix[strat.strategy_name]) {
          matrix[strat.strategy_name] = {};
        }
        matrix[strat.strategy_name][tf] = strat;
      });
    });
    return matrix;
  }, []);

  // 1. Fetch dữ liệu ban đầu cho toàn bộ hệ thống
  useEffect(() => {
    const fetchInitialState = async () => {
      try {
        const result = await tradeApi.getRadarHistory();
        if (result.status === "success") {
          const newCache: Record<string, RadarMatrix> = {};
          Object.entries(result.data).forEach(([sym, data]) => {
            newCache[sym] = transformData(data);
          });
          setCache(newCache);
        }
      } catch (err) {
        console.error("Failed to fetch radar state", err);
      }
    };
    fetchInitialState();
  }, [transformData]);

  // 2. Lắng nghe WebSocket để cập nhật Real-time vào Cache
  useEffect(() => {
    const handleRadarUpdate = (msg: any) => {
      const msgSymbol = msg.symbol; // Symbol từ server (VD: XAUUSD)
      const tf = msg.tf;
      
      setCache(prev => {
        const symbolMatrix = { ...(prev[msgSymbol] || {}) };
        msg.data.forEach((strat: StrategyResult) => {
          const name = strat.strategy_name;
          symbolMatrix[name] = { ...symbolMatrix[name], [tf]: strat };
        });
        return { ...prev, [msgSymbol]: symbolMatrix };
      });
    };

    subscribe("RADAR_UPDATE", handleRadarUpdate);
    return () => unsubscribe("RADAR_UPDATE", handleRadarUpdate);
  }, [subscribe, unsubscribe]);

  // Trả về dữ liệu của symbol đang được chọn
  const currentSymbolRaw = getSymbolShortName(symbol);
  return cache[currentSymbolRaw] || {};
};