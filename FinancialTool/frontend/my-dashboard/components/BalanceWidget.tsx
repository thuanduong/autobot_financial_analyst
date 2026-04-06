"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/app/context/AuthContext";
import { userApi } from "@/services/userApi";
import { useSocket } from "@/app/context/SocketContext"; 

export const BalanceWidget = () => {
  const { token } = useAuth();
  const [balance, setBalance] = useState<number>(0);
  const { subscribe, unsubscribe } = useSocket(); 

  useEffect(() => {
    if (!token) return;
    // Gọi API lấy số dư ngay khi Component này xuất hiện
    const fetchBalance = async () => {
      try {
        const data = await userApi.getProfile(token);
        setBalance(data.wallet.balance);
      } catch (err) {
        console.error("Lỗi lấy số dư:", err);
      }
    };
    fetchBalance();

    const handleBalanceUpdate = (msg: any) => {
      setBalance(msg.balance);
    };
    subscribe("BALANCE_UPDATE", handleBalanceUpdate);
    return () => {
      unsubscribe("BALANCE_UPDATE", handleBalanceUpdate);
    };
    
  }, [token, subscribe, unsubscribe]);

  return (
    <div className="bg-slate-800 px-4 py-2 rounded-lg border border-slate-700 flex items-center gap-3">
      <span className="text-slate-400 text-sm">Ví Ảo:</span>
      <span className="text-green-400 font-bold font-mono">
        ${balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}
      </span>
    </div>
  );
};