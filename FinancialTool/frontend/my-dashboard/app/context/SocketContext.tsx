"use client";

import React, { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react';

// Định nghĩa kiểu cho Callback
type MessageCallback = (payload: any) => void;

interface SocketContextType {
  isConnected: boolean;
  subscribe: (topic: string, callback: MessageCallback) => void;
  unsubscribe: (topic: string, callback: MessageCallback) => void;
  send: (data: any) => void;
}

const SocketContext = createContext<SocketContextType | null>(null);

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001";

export const SocketProvider = ({ children }: { children: ReactNode }) => {
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  
  // Lưu trữ danh sách người đăng ký: { "PRICE_UPDATE": [callback1, callback2], "ORDER_FILLED": [...] }
  const subscribers = useRef<Record<string, MessageCallback[]>>({});

  useEffect(() => {
    // 1. Khởi tạo kết nối Singleton
    const connect = () => {
      const token = localStorage.getItem("access_token");

      ws.current = new WebSocket(`${WS_URL}/ws/market?token=${token}`);

      ws.current.onopen = () => {
        console.log("🌐 System Socket Connected");
        setIsConnected(true);
      };

      ws.current.onclose = () => {
        console.log("🔌 System Socket Disconnected - Retrying...");
        setIsConnected(false);
        setTimeout(connect, 3000); // Auto Reconnect sau 3s
      };

      ws.current.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          // 2. Phân phối tin nhắn (Pub/Sub Pattern)
          // Chỉ gửi cho những ai đã đăng ký lắng nghe msg.type này
          if (msg.type && subscribers.current[msg.type]) {
            subscribers.current[msg.type].forEach(callback => callback(msg));
          }
        } catch (e) {
          console.error("Socket Parse Error:", e);
        }
      };
    };

    connect();

    return () => {
      ws.current?.close();
    };
  }, []);

  // 3. Hàm đăng ký lắng nghe
  const subscribe = (topic: string, callback: MessageCallback) => {
    if (!subscribers.current[topic]) {
      subscribers.current[topic] = [];
    }
    subscribers.current[topic].push(callback);
  };

  // 4. Hàm hủy đăng ký
  const unsubscribe = (topic: string, callback: MessageCallback) => {
    if (!subscribers.current[topic]) return;
    subscribers.current[topic] = subscribers.current[topic].filter(cb => cb !== callback);
  };

  const send = (data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  };

  return (
    <SocketContext.Provider value={{ isConnected, subscribe, unsubscribe, send }}>
      {children}
    </SocketContext.Provider>
  );
};

// Hook tiện ích để các component con sử dụng
export const useSocket = () => {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error("useSocket must be used within a SocketProvider");
  }
  return context;
};