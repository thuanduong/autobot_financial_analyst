"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/app/context/AuthContext";
import { tradeApi } from "@/services/tradeApi";
import { getSymbolLabel } from "@/config/symbols";
import { formatDateTime } from "@/utils/timeHelper";

// --- INTERFACES ---
interface Order {
  id: number;
  symbol: string;
  order_type: string;
  volume: number;
  open_price: number;
  close_price: number;
  open_time: string;
  status: string;
  profit_loss: number;
}

interface BotOrder {
  time: number;
  strategy_id: string;
  symbol: string; // Tùy thuộc API của bạn có trả về không, tạm mặc định hiển thị theo mã đang chọn
  signal: string;
  outcome: string;
  entry_price?: number;
  close_price?: number;
  sl?: number;
  tp?: number;
  pnl?: number;
}

interface Props {
  refreshTrigger: number;
  symbol: string; 
  tf: string;
}

export const OrderList = ({ refreshTrigger, symbol, tf }: Props) => {
  const { token } = useAuth();
  
  const [activeTab, setActiveTab] = useState<'MANUAL' | 'BOT'>('BOT');
  const [orders, setOrders] = useState<Order[]>([]);
  const [botOrders, setBotOrders] = useState<BotOrder[]>([]);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const limit = 10;
  
  // 1. Fetch Lệnh Thủ Công
  const fetchManualOrders = async () => {
    if (!token) return;
    try {
      const data = await tradeApi.getOrders(token);
      console.log(data);
      setOrders(data);
    } catch (err) {
      console.error(err);
    }
  };

  // 2. Fetch Lịch Sử Bot 
  const fetchBotHistory = async (pageNum: number, append: boolean = false) => {
    setIsLoading(true);
    try {
      const result = await tradeApi.getBotHistory(symbol, tf, pageNum * limit);
      
      if (result && result.status === "success") {
        const newData = result.data;
        setBotOrders(newData);
        // Nếu số lượng trả về ít hơn số lượng yêu cầu, nghĩa là đã hết dữ liệu
        setHasMore(newData.length >= pageNum * limit);
      }
    } catch (err) {
      console.error("Lỗi lấy lịch sử Bot:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Tự động load lại data
  useEffect(() => {
    setPage(1);
    fetchManualOrders();
    fetchBotHistory(1);
  }, [token, refreshTrigger, symbol, tf]);

  // Đóng lệnh thủ công
  const handleCloseOrder = async (orderId: number) => {
    if (!token) return;
    setLoadingId(orderId);
    try {
      const data = await tradeApi.closeOrder(token, orderId);
      alert(data.message); 
      fetchManualOrders(); 
    } catch (err: any) {
      alert(`Lỗi: ${err.message}`);
    } finally {
      setLoadingId(null);
    }
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchBotHistory(nextPage, true);
  };

  // Render Badge cho Trạng thái Bot
  const renderOutcomeBadge = (outcome: string) => {
    if (outcome === 'WIN') return <span className="px-2 py-1 rounded bg-green-500/20 text-green-400 font-bold text-xs border border-green-500/30">WIN</span>;
    if (outcome === 'LOSS') return <span className="px-2 py-1 rounded bg-red-500/20 text-red-400 font-bold text-xs border border-red-500/30">LOSS</span>;
    return <span className="px-2 py-1 rounded bg-yellow-500/20 text-yellow-400 font-bold text-xs border border-yellow-500/30 animate-pulse">PENDING</span>;
  };

  return (
    <div className="flex flex-col h-full relative">
      
      {/* TABS NAVIGATION */}
      <div className="flex gap-4 border-b border-slate-700 mb-4 pb-2">
        <button 
          onClick={() => setActiveTab('BOT')}
          className={`font-bold transition-colors ${activeTab === 'BOT' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-500 hover:text-slate-300'}`}
        >
          🤖 Lịch Sử Bot
        </button>
        <button 
          onClick={() => setActiveTab('MANUAL')}
          className={`font-bold transition-colors ${activeTab === 'MANUAL' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-500 hover:text-slate-300'}`}
        >
          👤 Lệnh Thủ Công
        </button>
      </div>

      {/* NỘI DUNG TAB */}
      <div className="flex-1 overflow-auto custom-scrollbar pr-2">
        <div className="w-full">
          {/* ======================= TAB 1: LỊCH SỬ BOT ======================= */}
          {activeTab === 'BOT' && (
            isLoading ? (
              <p className="text-slate-500 text-sm text-center mt-10 animate-pulse">Đang tải lịch sử Bot...</p>
            ) : botOrders.length === 0 ? (
              <p className="text-slate-500 text-sm text-center mt-10">Hệ thống chưa ghi nhận lệnh Bot nào.</p>
            ) : (
              <table className="w-full text-sm text-left text-slate-300">
                <thead className="text-[10px] text-slate-500 uppercase bg-slate-800/50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 rounded-tl-lg">Thời Gian</th>
                    <th className="px-4 py-3">Chiến Thuật</th>
                    <th className="px-4 py-3">Tín Hiệu</th>
                    <th className="px-4 py-3 text-center">Trạng Thái</th>
                    <th className="px-4 py-3 text-right">Mức SL/TP</th>
                    <th className="px-4 py-3 text-right rounded-tr-lg">PnL</th>
                  </tr>
                </thead>
                <tbody>
                  {botOrders.map((order, idx) => (
                    <tr key={idx} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                        {formatDateTime(order.time)}
                      </td>
                      <td className="px-4 py-3 font-bold text-slate-200">{order.strategy_id}</td>
                      <td className={`px-4 py-3 font-bold ${order.signal.includes('BUY') ? 'text-green-500' : 'text-red-500'}`}>
                        {order.signal}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {renderOutcomeBadge(order.outcome)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-slate-400">
                        SL: {order.sl} <br/> TP: {order.tp}
                      </td>
                      <td className={`px-4 py-3 text-right font-bold font-mono ${order.pnl && order.pnl > 0 ? 'text-green-400' : order.pnl && order.pnl < 0 ? 'text-red-400' : 'text-slate-500'}`}>
                        {order.outcome === 'PENDING' ? '--' : `${order.pnl! > 0 ? '+' : ''}${order.pnl}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
          
          {/* NÚT TẢI THÊM LỊCH SỬ (LAZY LOAD) */}
          {activeTab === 'BOT' && botOrders.length > 0 && hasMore && (
            <div className="flex justify-center mt-4 mb-2">
              <button 
                onClick={handleLoadMore}
                disabled={isLoading}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-6 py-2 rounded-full text-xs font-bold transition-all border border-slate-600 disabled:opacity-50"
              >
                {isLoading ? 'Đang tải...' : '👇 Xem lịch sử cũ hơn'}
              </button>
            </div>
          )}
        </div>
        {/* ======================= TAB 2: LỆNH THỦ CÔNG ======================= */}
        {activeTab === 'MANUAL' && (
          orders.length === 0 ? (
            <p className="text-slate-500 text-sm text-center mt-10">Bạn chưa có lệnh thủ công nào đang mở.</p>
          ) : (
            <table className="w-full text-sm text-left text-slate-300">
              <thead className="text-[10px] text-slate-500 uppercase bg-slate-800/50 sticky top-0">
                <tr>
                  <th className="px-4 py-3 rounded-tl-lg">Mã</th>
                  <th className="px-4 py-3">Loại</th>
                  <th className="px-4 py-3">Khối lượng</th>
                  <th className="px-4 py-3">Giá mở</th>
                  <th className="px-4 py-3">Giá đóng</th>
                  <th className="px-4 py-3">Profit</th>
                  <th className="px-4 py-3 text-right rounded-tr-lg">Hành động</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-bold text-white">{getSymbolLabel(order.symbol)}</td>
                    <td className={`px-4 py-3 font-bold ${order.order_type === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                      {order.order_type}
                    </td>
                    <td className="px-4 py-3 font-mono">{order.volume}</td>
                    <td className="px-4 py-3 font-mono">{order.open_price}</td>
                    <td className="px-4 py-3 font-mono">{order.close_price}</td>
                    <td className={`px-4 py-3 font-mono ${order.profit_loss > 0 ? 'text-green-400' : order.profit_loss < 0 ? 'text-red-400' : 'text-slate-500'}`}>
                      {order.profit_loss}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        disabled={loadingId === order.id || order.status === 'CLOSED'}
                        onClick={() => handleCloseOrder(order.id)}
                        className="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1.5 rounded transition-colors disabled:opacity-50"
                      >
                        {loadingId === order.id ? "Đang đóng..." : "Đóng lệnh"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </div>
    </div>
  );
};