"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from "next/navigation";

import { useMarketData } from '@/hooks/useMarketStream';
import { TradingViewChart } from '@/components/TradingViewChart';
import { useAuth } from "@/app/context/AuthContext";
import { Header } from "@/components/Header";
import { OrderPanel } from "@/components/OrderPanel";
import { OrderList } from "@/components/OrderList";
import { SymbolConfigPopup } from "@/components/SymbolConfigPopup";
import { StrategyRadar } from "@/components/StrategyRadar";
import { SYMBOL_MAP, getSymbolLabel, WATCH_TIMEFRAMES } from "@/config/symbols";

export default function Dashboard() {
  const RawSymbols = Object.keys(SYMBOL_MAP);

  // State quản lý Symbol/Timeframe
  const [symbol, setSymbol] = useState(RawSymbols[0]);
  const [tf, setTf] = useState("M5");
  const [refreshTick, setRefreshTick] = useState(0);

  // State quản lý Toggle Chiến thuật
  const [activeStrategies, setActiveStrategies] = useState<string[]>([]);
  const [isConfigOpen, setIsConfigOpen] = useState(false);

  // Gọi Hook lấy dữ liệu
  const { data, isConnected, markers, loadMoreHistory } = useMarketData(symbol, tf);
  const { token, isLoading } = useAuth();
  const router = useRouter();

  // Redirect nếu chưa đăng nhập
  useEffect(() => {
    if (isLoading) return;
    if (!token) {
        router.push("/login");
    }
  }, [token, router, isLoading]);

  // Tự động thu thập danh sách chiến thuật từ markers để tạo nút Toggle
  useEffect(() => {
    const uniqueStrats = Array.from(new Set(markers.map(m => m.strategy_id).filter(Boolean)));
    // Nếu lần đầu load data về, tự động bật tất cả các chiến thuật lên
    if (uniqueStrats.length > 0 && activeStrategies.length === 0) {
      setActiveStrategies(uniqueStrats);
    }
  }, [markers]);

  // Lọc Mũi tên (Markers) dựa trên các Toggle đang được bật
  const filteredMarkers = useMemo(() => {
    if (activeStrategies.length === 0) return []; // Tắt hết thì không hiện gì
    return markers.filter(marker => activeStrategies.includes(marker.strategy_id));
  }, [markers, activeStrategies]);

  const toggleStrategy = (stratId: string) => {
    setActiveStrategies(prev => 
      prev.includes(stratId) 
        ? prev.filter(id => id !== stratId) 
        : [...prev, stratId]
    );
  };

  if (isLoading) {
    return <div className="min-h-screen bg-[#0f172a] flex items-center justify-center text-white">Đang kiểm tra đăng nhập...</div>;
  }

  // Lấy giá hiện tại
  const currentPrice = data.length > 0 ? data[data.length - 1].close : 0;
  const previousPrice = data.length > 1 ? data[data.length - 2].close : 0;
  const isUp = currentPrice >= previousPrice;
  
  const handleOrderSuccess = () => {
    setRefreshTick(prev => prev + 1);
  };

  // Trích xuất danh sách chiến thuật hiện có để render nút Toggle
  const availableStrategies = Array.from(new Set(markers.map(m => m.strategy_id).filter(Boolean)));

  return (
    <div className="min-h-screen bg-[#0f172a] text-white font-sans flex flex-col">
      <Header />
      
      {/* 1. THANH ĐIỀU HƯỚNG & TRẠNG THÁI (Dàn ngang, Responsive) */}
      <div className="px-4 py-2">
        <header className="flex flex-col md:flex-row justify-between items-center bg-[#1e293b] p-4 rounded-xl border border-slate-700 shadow-lg gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent hidden sm:block">
              MARKET TERMINAL
            </h1>
            <div className="flex gap-2">
              <select 
                value={symbol} 
                onChange={(e) => setSymbol(e.target.value)}
                className="bg-[#334155] font-bold text-sm rounded px-3 py-2 outline-none border border-slate-600 focus:border-blue-500"
              >
                {RawSymbols.map((s) => (
                  <option key={s} value={s}>{getSymbolLabel(s)}</option>
                ))}
              </select>
              <select 
                value={tf} 
                onChange={(e) => setTf(e.target.value)}
                className="bg-[#334155] font-bold text-sm rounded px-3 py-2 outline-none border border-slate-600 focus:border-blue-500"
              >
                {
                  WATCH_TIMEFRAMES.map((s)=> (
                    <option key={s} value={s}>{s}</option>
                  ))
                }
              </select>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className={`text-2xl font-mono font-bold ${isUp ? 'text-green-400' : 'text-red-400'}`}>
              {currentPrice.toFixed(2)}
            </div>
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold border ${isConnected ? 'bg-green-500/10 text-green-400 border-green-500/30' : 'bg-red-500/10 text-red-400 border-red-500/30'}`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              {isConnected ? "LIVE STREAM" : "CONNECTING..."}
            </div>
            <button 
              className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-4 py-1.5 rounded-lg text-sm transition-colors"
              onClick={() => setIsConfigOpen(true)}>
              ⚙️ Cấu Hình
            </button>
          </div>
        </header>
      </div>

      {/* 2. KHU VỰC BIỂU ĐỒ CHÍNH */}
      <div className="px-4 pb-2 w-full">
        <div className="bg-[#1e293b] rounded-xl border border-slate-700 shadow-2xl relative overflow-hidden h-[50vh] md:h-[60vh]">
          {/* Watermark ẩn phía sau */}
          <div className="absolute top-4 left-6 z-0 pointer-events-none opacity-20">
            <h3 className="text-6xl font-black text-slate-500 tracking-tighter">{symbol}</h3>
          </div>

          <div className="w-full h-full p-2 relative z-10">
              {data.length > 0 ? (
                // Truyền mảng ĐÃ LỌC vào Chart
                <TradingViewChart data={data} markers={filteredMarkers} onLoadMore={loadMoreHistory} />
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 font-medium animate-pulse">
                  Đang tải dữ liệu nến...
                </div>
              )}
          </div>
        </div>
      </div>

      {/* 3. THANH TOGGLE CHIẾN THUẬT */}
      <div className="px-4 py-2 w-full">
        <div className="flex flex-wrap items-center gap-2 bg-[#1e293b] p-3 rounded-xl border border-slate-700">
          <span className="text-sm font-bold text-slate-400 mr-2">BỘ LỌC CHART:</span>
          {availableStrategies.length === 0 ? (
            <span className="text-xs text-slate-500 italic">Chưa có tín hiệu để lọc</span>
          ) : (
            availableStrategies.map(stratId => (
              <button 
                key={stratId}
                onClick={() => toggleStrategy(stratId)}
                className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all border ${
                  activeStrategies.includes(stratId) 
                    ? 'bg-blue-600/20 border-blue-500 text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.2)]' 
                    : 'bg-slate-800 border-slate-600 text-slate-500 hover:border-slate-500'
                }`}
              >
                {activeStrategies.includes(stratId) ? '✅' : '❌'} {stratId}
              </button>
            ))
          )}
        </div>
      </div>

      {/* 4. KHU VỰC RADAR & ĐẶT LỆNH THỦ CÔNG (Grid layout) */}
      <div className="px-4 py-2 w-full grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Radar chiến thuật chiếm 3 cột trên PC */}
        <div className="lg:col-span-3">
          <StrategyRadar symbol={symbol} />
        </div>
        
        {/* Panel đặt lệnh thủ công chiếm 1 cột */}
        <div className="lg:col-span-1 bg-[#1e293b] border border-slate-700 rounded-xl p-4">
          <h3 className="text-sm font-bold text-slate-400 mb-4 border-b border-slate-700 pb-2">ĐẶT LỆNH THỦ CÔNG</h3>
          <OrderPanel symbol={symbol} onOrderSuccess={handleOrderSuccess} />
        </div>
      </div>

      {/* 5. LỊCH SỬ GIAO DỊCH DƯỚI CÙNG */}
      <div className="px-4 py-4 w-full flex-1">
        <div className="bg-[#1e293b] border border-slate-700 rounded-xl h-full p-4 min-h-[300px]">
          <h3 className="text-sm font-bold text-slate-400 mb-4 border-b border-slate-700 pb-2">SỔ LỆNH (ORDER BOOK)</h3>
          <OrderList symbol={symbol} tf={tf} refreshTrigger={refreshTick} />
        </div>
      </div>

      {/* MODAL CẤU HÌNH */}
      <SymbolConfigPopup 
          isOpen={isConfigOpen} 
          onClose={() => setIsConfigOpen(false)} 
      />
    </div>
  );
}