import React from 'react';
import { RADAR_TIMEFRAMES } from "@/config/symbols";
import { useStrategyRadarStream } from "@/hooks/useStrategyRadarStream";

export const StrategyRadar = ({ symbol }: { symbol: string }) => {
  // Lấy dữ liệu đã được tối ưu từ Hook
  const matrixData = useStrategyRadarStream(symbol);

  // UI Helpers (Giữ nguyên logic tô màu)
  const getSignalColor = (signal?: string) => {
    if (signal === 'BUY') return 'bg-green-500/20 text-green-400 border-green-500/30';
    if (signal === 'SELL') return 'bg-red-500/20 text-red-400 border-red-500/30';
    return 'bg-slate-800 text-slate-500 border-slate-700';
  };

  const getScoreColor = (score?: number, signal?: string) => {
    if (!score || signal === 'NEUTRAL') return 'bg-slate-700';
    if (score >= 80) return signal === 'BUY' ? 'bg-green-500' : 'bg-red-500';
    if (score >= 50) return signal === 'BUY' ? 'bg-green-400' : 'bg-red-400';
    return 'bg-yellow-500'; 
  };

  const strategyNames = Object.keys(matrixData).sort();

  return (
    <div className="bg-[#1e293b] border border-slate-700 rounded-xl p-4 h-full flex flex-col">
      <h3 className="text-sm font-bold text-slate-400 mb-4 border-b border-slate-700 pb-2 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
        HỢP LƯU ĐA KHUNG (MTF MATRIX)
      </h3>
      
      <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
        {strategyNames.length === 0 ? (
           <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2 opacity-50 py-10">
             <span className="text-3xl">📡</span>
             <p className="text-sm italic">Đang chờ tín hiệu quét từ hệ thống...</p>
           </div>
        ) : (
          <div className="space-y-4">
            {strategyNames.map(stratName => (
              <div key={stratName} className="bg-[#0f172a] border border-slate-700 rounded-lg p-3">
                {/* Tên Chiến Thuật (Header của Block) */}
                <h4 className="font-bold text-slate-200 text-sm mb-3 border-b border-slate-800 pb-2 uppercase tracking-wide">
                  🔹 {stratName}
                </h4>
                
                {/* 3 Thẻ đại diện cho 3 Khung thời gian */}
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {RADAR_TIMEFRAMES.map(tf => {
                    const data = matrixData[stratName][tf];
                    
                    return (
                      <div key={tf} className="bg-[#1e293b] rounded p-2 border border-slate-700/50 flex flex-col justify-between min-h-[110px]">
                        {/* Dòng 1: Tên Khung Giờ & Badge Tín Hiệu */}
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-xs font-black text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">{tf}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSignalColor(data?.signal)}`}>
                            {data?.signal || 'WAITING'}
                          </span>
                        </div>

                        {/* Dòng 2: Thanh Sức Mạnh (Chỉ hiện khi có dữ liệu) */}
                        <div className="mb-2">
                          <div className="w-full bg-slate-800 rounded-full h-1">
                            <div 
                              className={`h-1 rounded-full ${getScoreColor(data?.score, data?.signal)} transition-all duration-500`} 
                              style={{ width: `${data?.score || 0}%` }}
                            ></div>
                          </div>
                        </div>

                        {/* Dòng 3: SL / TP (Chỉ hiện khi có lệnh Buy/Sell) */}
                        {data?.signal && data.signal !== 'NEUTRAL' ? (
                          <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
                            <span className="text-red-400">SL: {data.sl ? data.sl.toFixed(2) : '--'}</span>
                            <span className="text-green-400">TP: {data.tp ? data.tp.toFixed(2) : '--'}</span>
                          </div>
                        ) : (
                          <div className="text-[10px] text-slate-600 mb-1 italic">Không có vùng giá</div>
                        )}

                        {/* Dòng 4: Lý do rút gọn */}
                        <p className="text-[10px] text-slate-500 line-clamp-2 leading-tight" title={data?.reason}>
                          {data?.reason || "Đang phân tích..."}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
