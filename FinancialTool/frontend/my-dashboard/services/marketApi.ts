import { Candle } from "@/types/market";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const getMarketHistoryData = async (
  symbol: string, 
  tf: string, 
  limit: number = 500
): Promise<Candle[]> => {
  try {
    const res = await fetch(
      `${API_URL}/api/chart/history/initial?symbol=${symbol}&tf=${tf}&limit=${limit}`,
      { cache: 'no-store' }
    );
    
    if (!res.ok) throw new Error("Failed to fetch market history");
    
    return await res.json();
  } catch (error) {
    console.error("API Error:", error);
    return [];
  }
};

export const getMarketHistoryRange = async (
  symbol: string, 
  tf: string, 
  fromTime: number, 
  toTime: number
): Promise<Candle[]> => {
  try {
    const res = await fetch(
      `${API_URL}/api/chart/history/range?symbol=${symbol}&tf=${tf}&from_time=${fromTime}&to_time=${toTime}`,
      { cache: 'no-store' }
    );
    if (!res.ok) throw new Error("Failed to fetch range history");
    return await res.json();
  } catch (error) {
    console.error("Range API Error:", error);
    return [];
  }
};

export const getMarketSignalsHistory = async (symbol: string, tf: string, limit: number = 100) => {
  try {
    const response = await fetch(`${API_URL}/api/signals/history?symbol=${symbol}&tf=${tf}&limit=${limit}`);
    const result = await response.json();
    return result.data || [];
  } catch (error) {
    console.error("Lỗi lấy lịch sử tín hiệu:", error);
    return [];
  }
};
