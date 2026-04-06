"use client";

import { useState } from "react";
import { useAuth } from "@/app/context/AuthContext";
import { tradeApi } from "@/services/tradeApi";
import { getSymbolLabel, getSymbolFullName } from "@/config/symbols";

interface Props {
  symbol: string;
  onOrderSuccess?: () => void;
}

export const OrderPanel = ({ symbol, onOrderSuccess }: Props) => {
  const { token } = useAuth();
  const [volume, setVolume] = useState<number>(0.1); // Mặc định 0.1 Lot
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Hàm xử lý chung khi bấm Mua hoặc Bán
  const handleTrade = async (orderType: "BUY" | "SELL") => {
    if (!token) return;
    setLoading(true);
    setMessage("");

    try {
      const data = await tradeApi.placeOrder(token, symbol, orderType, volume);
      setMessage(`✅ Khớp lệnh ${orderType} giá ${data.open_price}`);
      
      // Gọi callback để Dashboard load lại danh sách Order
      if (onOrderSuccess) onOrderSuccess();
      
    } catch (error: any) {
      setMessage(`❌ ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
      {/* ... (Phần giao diện UI Input Volume, Nút Buy/Sell giữ nguyên như cũ của bạn) ... */}
      <h2 className="text-lg font-bold text-white mb-4 border-b border-slate-800 pb-2">
        Đặt lệnh <span className="text-blue-400">{getSymbolLabel(symbol)}</span>
      </h2>
      <p className="text-xs text-slate-500 mb-4 border-b border-slate-800 pb-2">
        {getSymbolFullName(symbol)}
      </p>
      <div className="mb-6">
        <label className="block text-sm text-slate-400 mb-2">Khối lượng (Lot)</label>
        <div className="flex items-center gap-3">
          <input 
            type="number" step="0.01" min="0.01" value={volume}
            onChange={(e) => setVolume(Number(e.target.value))}
            className="flex-1 h-10 bg-slate-950 border border-slate-700 rounded text-center text-white font-mono focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="flex gap-3 mt-auto">
        <button 
          disabled={loading} onClick={() => handleTrade("SELL")}
          className="flex-1 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-bold py-3 rounded-lg"
        >SELL</button>
        <button 
          disabled={loading} onClick={() => handleTrade("BUY")}
          className="flex-1 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white font-bold py-3 rounded-lg"
        >BUY</button>
      </div>

      {message && (
        <div className={`mt-4 p-2 rounded text-sm text-center ${message.includes('✅') ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          {message}
        </div>
      )}
    </div>
  );
};