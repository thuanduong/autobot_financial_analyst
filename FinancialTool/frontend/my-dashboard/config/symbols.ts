// config/symbols.ts

export interface SymbolDisplayInfo {
  label: string;       // Tên ngắn gọn hiển thị trên Chart, Bảng (VD: XAU/USD)
  fullName: string;    // Tên đầy đủ (VD: Gold / US Dollar)
  category: string;    // Phân loại để sau này làm bộ lọc (Forex, Metal, Crypto)
  short: string;
}

// 1. Lấy thông tin Broker từ biến môi trường (Mặc định là exness nếu không có)
// Lưu ý: Trong Next.js biến phải bắt đầu bằng NEXT_PUBLIC_ để browser có thể đọc được
const ACTIVE_BROKER = process.env.NEXT_PUBLIC_BROKER || "exness";
const SUFFIX = ACTIVE_BROKER === "oanda" ? ".sml" : "m";

// 2. Danh sách Metadata gốc (Không chứa suffix)
const BASE_SYMBOLS = [
  { id: "XAUUSD", label: "XAU/USD", fullName: "Gold vs US Dollar", category: "Metal" },
  { id: "EURUSD", label: "EUR/USD", fullName: "Euro vs US Dollar", category: "Forex" },
  { id: "GBPUSD", label: "GBP/USD", fullName: "Pound vs US Dollar", category: "Forex" },
  { id: "USDJPY", label: "USD/JPY", fullName: "US Dollar vs Japan Yen", category: "Forex" },
  { id: "BTCUSD", label: "BTC/USD", fullName: "Bitcoin", category: "Crypto" },
];

// 3. Tự động tạo SYMBOL_MAP dựa trên Suffix của sàn đang chạy
export const SYMBOL_MAP: Record<string, SymbolDisplayInfo> = {};

BASE_SYMBOLS.forEach(item => {
  // Logic mirror với Backend: BTC/ETH thường không có suffix
  const rawKey = (item.id === "BTCUSD" || item.id === "ETHUSD") 
    ? item.id 
    : `${item.id}${SUFFIX}`;

  SYMBOL_MAP[rawKey] = {
    label: item.label,
    fullName: item.fullName,
    category: item.category,
    short: item.id
  };
});

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