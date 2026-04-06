// src/services/tradeApi.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const tradeApi = {
  async placeOrder(token: string, symbol: string, orderType: "BUY" | "SELL", volume: number) {
    const res = await fetch(`${API_URL}/api/trade/order`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ symbol, order_type: orderType, volume })
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Lỗi đặt lệnh");
    }
    return res.json();
  },

  async closeOrder(token: string, orderId: number) {
    const res = await fetch(`${API_URL}/api/trade/close_order`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ order_id: orderId })
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Lỗi đóng lệnh");
    }
    return res.json();
  },

  async getOrders(token: string, status?: "OPEN" | "CLOSED") {
    const url = status ? `${API_URL}/api/trade/orders?status=${status}` : `${API_URL}/api/trade/orders`;
    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Không thể tải danh sách lệnh");
    return res.json();
  },

  async getSymbols(token: string) {
    const res = await fetch(`${API_URL}/api/trade/get_symbols`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Lỗi tải danh sách mã giao dịch");
    return res.json();
  },
  async addSymbolConfig(token: string, symbol: string, contractSize: number, leverage: number) {
    const res = await fetch(`${API_URL}/api/trade/add_symbol`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        symbol: symbol,
        contract_size: contractSize,
        base_leverage: leverage,
        is_active: true
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Lỗi thêm mã giao dịch");
    }
    return res.json();
  },
  async deleteSymbolConfig(token: string, id: number) {
    const res = await fetch(`${API_URL}/api/trade/del_symbol/${id}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Lỗi xóa mã giao dịch");
    return res.json();
  },
  getBotHistory: async (symbol: string, tf: string, limit: number = 50) => {
    const response = await fetch(`${API_URL}/api/trade/signals/history?symbol=${symbol}&tf=${tf}&limit=${limit}`);
    
    if (!response.ok) {
      throw new Error('Lỗi fetch lịch sử Bot');
    }
    const result = await response.json();
    return result; 
  },
  getBotHistoryRange: async (symbol: string, tf: string, limit: number = 50, fromtime: number, totime: number) => {
    const response = await fetch(`${API_URL}/api/trade/signals/history?symbol=${symbol}&tf=${tf}&limit=${limit}&from_time=${fromtime}&to_time=${totime}`);
    
    if (!response.ok) {
      throw new Error('Lỗi fetch lịch sử Bot');
    }
    const result = await response.json();
    return result; 
  },
  async getRadarHistory() {
    const response = await fetch(`${API_URL}/api/trade/radar/state`);
    if (!response.ok) {
      throw new Error('Lỗi fetch lịch sử Bot');
    }
    const result = await response.json();
    return result;
  }
};