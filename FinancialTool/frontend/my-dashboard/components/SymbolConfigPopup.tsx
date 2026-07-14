"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/app/context/AuthContext";
import { tradeApi } from "@/services/tradeApi";
import { getSymbolLabel } from "@/config/symbols";

interface SymbolData {
  id: number;
  symbol: string;
  contract_size: number;
  leverage: number;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const SymbolConfigPopup = ({ isOpen, onClose }: Props) => {
  const { token } = useAuth();
  const [symbols, setSymbols] = useState<SymbolData[]>([]);
  const [loading, setLoading] = useState(false);

  // State cho Global Settings (Sound)
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [volume, setVolume] = useState(0.5);
  
  // State cho Form thêm mới
  const [newSymbol, setNewSymbol] = useState("");
  const [newSize, setNewSize] = useState(100);
  const [newLeverage, setNewLeverage] = useState(500);
  const [msg, setMsg] = useState("");

  // Load settings âm thanh từ localStorage khi mở popup
  useEffect(() => {
    if (isOpen) {
      const s = localStorage.getItem("trading_sound_enabled");
      const v = localStorage.getItem("trading_sound_volume");
      if (s !== null) setSoundEnabled(s === "true");
      if (v !== null) setVolume(parseFloat(v));
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && token) {
      fetchSymbols();
      setMsg(""); // Reset thông báo mỗi khi mở lại
    }
  }, [isOpen, token]);

  const fetchSymbols = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await tradeApi.getSymbols(token);
      setSymbols(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    
    try {
      await tradeApi.addSymbolConfig(token, newSymbol, newSize, newLeverage);
      setMsg("✅ Đã thêm cấu hình thành công!");
      setNewSymbol(""); // Xóa rỗng ô nhập liệu
      fetchSymbols();   // Load lại bảng ngay lập tức
    } catch (err: any) {
      setMsg(`❌ ${err.message}`);
    }
  };

  const handleDelete = async (id: number) => {
    if (!token || !confirm("Bạn có chắc chắn muốn xóa cấu hình này?")) return;
    
    try {
      await tradeApi.deleteSymbolConfig(token, id);
      fetchSymbols(); // Load lại bảng
    } catch (err: any) {
      alert(`Lỗi: ${err.message}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-3xl p-6 shadow-2xl overflow-y-auto max-h-[90vh]">
        
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Quản lý Mã Giao Dịch (Của Riêng Bạn)</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-3xl leading-none">&times;</button>
        </div>

        {/* Form Thêm Mới */}
        <form onSubmit={handleAdd} className="bg-slate-800 p-4 rounded-xl mb-6 border border-slate-700">
          <h3 className="text-sm font-bold text-slate-300 mb-3 uppercase tracking-wider">Thêm Mã Mới</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Tên Mã (VD: XAUUSD.sml)</label>
              <input 
                required type="text" value={newSymbol} onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                className="w-full bg-slate-950 border border-slate-600 rounded px-3 py-2 text-white focus:border-blue-500 focus:outline-none uppercase"
                placeholder="XAUUSD"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Contract Size</label>
              <input 
                required type="number" step="0.01" value={newSize} onChange={(e) => setNewSize(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-600 rounded px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Đòn Bẩy (1:X)</label>
              <input 
                required type="number" value={newLeverage} onChange={(e) => setNewLeverage(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-600 rounded px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div className="flex items-end">
              <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded transition-colors h-[42px]">
                + Thêm
              </button>
            </div>
          </div>
          {msg && <p className={`mt-3 text-sm ${msg.includes('✅') ? 'text-green-400' : 'text-red-400'}`}>{msg}</p>}
        </form>

        {/* Bảng Hiển Thị */}
        {loading ? (
          <div className="text-center py-8 text-slate-400">Đang tải danh sách...</div>
        ) : (
          <div className="overflow-x-auto border border-slate-700 rounded-lg">
            <table className="w-full text-sm text-left text-slate-300">
              <thead className="text-xs text-slate-400 uppercase bg-slate-800 border-b border-slate-700">
                <tr>
                  <th className="px-4 py-3">Mã (Symbol)</th>
                  <th className="px-4 py-3 text-right">Contract Size</th>
                  <th className="px-4 py-3 text-right">Đòn bẩy</th>
                  <th className="px-4 py-3 text-center">Hành động</th>
                </tr>
              </thead>
              <tbody>
                {symbols.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-slate-500 bg-slate-900/50">
                      Bạn chưa cấu hình mã nào. Hệ thống sẽ dùng giá trị mặc định cho mọi lệnh.
                    </td>
                  </tr>
                ) : (
                  symbols.map((s) => (
                    <tr key={s.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                      <td className="px-4 py-3 font-bold text-blue-400">
                        {getSymbolLabel(s.symbol)} 
                        <span className="block text-xs text-slate-500 font-normal">{s.symbol}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{s.contract_size}</td>
                      <td className="px-4 py-3 text-right font-mono text-green-400">1:{s.leverage}</td>
                      <td className="px-4 py-3 text-center">
                        <button 
                          onClick={() => handleDelete(s.id)}
                          className="text-red-400 hover:text-red-300 hover:bg-red-400/10 px-3 py-1 rounded transition-colors text-xs border border-red-500/30"
                        >
                          Xóa
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Cài đặt âm thanh */}
        <div className="mt-8 pt-6 border-t border-slate-700">
          <h3 className="text-sm font-bold text-slate-300 mb-4 uppercase tracking-wider">Cài đặt hệ thống</h3>
          <div className="flex flex-col md:flex-row gap-8 items-start md:items-center bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
            <div className="flex items-center gap-3">
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" checked={soundEnabled} 
                  onChange={(e) => {
                    setSoundEnabled(e.target.checked);
                    localStorage.setItem("trading_sound_enabled", String(e.target.checked));
                  }} 
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
              <span className="text-sm font-medium text-slate-300">Âm báo tín hiệu mới</span>
            </div>
            
            <div className="flex-1 w-full max-w-xs">
              <div className="flex justify-between mb-1">
                <span className="text-xs text-slate-400">Âm lượng</span>
                <span className="text-xs font-mono text-blue-400">{Math.round(volume * 100)}%</span>
              </div>
              <input 
                type="range" min="0" max="1" step="0.1" value={volume} 
                onChange={(e) => {
                  setVolume(parseFloat(e.target.value));
                  localStorage.setItem("trading_sound_volume", e.target.value);
                }}
                className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 flex justify-end">
          <button onClick={onClose} className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition">
            Đóng
          </button>
        </div>

      </div>
    </div>
  );
};