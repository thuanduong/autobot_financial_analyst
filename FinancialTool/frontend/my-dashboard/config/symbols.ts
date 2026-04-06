// config/symbols.ts

export interface SymbolDisplayInfo {
  label: string;       // Tên ngắn gọn hiển thị trên Chart, Bảng (VD: XAU/USD)
  fullName: string;    // Tên đầy đủ (VD: Gold / US Dollar)
  category: string;    // Phân loại để sau này làm bộ lọc (Forex, Metal, Crypto)
  short: string;
}

export const SYMBOL_MAP: Record<string, SymbolDisplayInfo> = {
  "XAUUSD.sml": {
    label: "XAU/USD",
    fullName: "Gold vs US Dollar",
    category: "Metal",
    short: "XAUUSD",
  },
  "EURUSD.sml": {
    label: "EUR/USD",
    fullName: "Euro vs US Dollar",
    category: "Forex",
    short: "EURUSD",
  },
  "GBPUSD.sml": {
    label: "GBP/USD",
    fullName: "Pound vs US Dollar",
    category: "Forex",
    short: "GBPUSD",
  },
  "USDJPY.sml": {
    label: "USD/JPY",
    fullName: "US Dollar vs Japan Yen",
    category: "Forex",
    short: "USDJPY",
  },
  "BTCUSD": {
    label: "BTC/USD",
    fullName: "Bitcoin",
    category: "Crypto",
    short: "BTCUSD",
  },
};

export const getSymbolLabel = (rawSymbol: string): string => {
  return SYMBOL_MAP[rawSymbol]?.label || rawSymbol;
};

export const getSymbolShortName = (rawSymbol: string): string => {
  return SYMBOL_MAP[rawSymbol]?.short || rawSymbol;
};

export const getSymbolFullName = (rawSymbol: string): string => {
  return SYMBOL_MAP[rawSymbol]?.fullName || rawSymbol;
};

export const getRawSymbolFromLabel = (labelToFind: string): string | undefined => {
  const allKeys = Object.keys(SYMBOL_MAP);
  const foundKey = allKeys.find(key => SYMBOL_MAP[key].label === labelToFind);
  
  return foundKey;
};

export const WATCH_TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4"];
export const RADAR_TIMEFRAMES = ["M1", "M5", "M15"];