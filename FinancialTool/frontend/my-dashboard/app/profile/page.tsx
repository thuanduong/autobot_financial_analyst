"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/app/context/AuthContext";
import { userApi } from "@/services/userApi";

interface UserProfile {
    id: number;
    email: string;
    created_at: string;
    wallet: {
        balance: number;
        equity: number;
    };
}

export default function ProfilePage() {
    const { token, logout, isLoading } = useAuth();
    const router = useRouter();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        if (isLoading) return;

        if (!token) {
            router.push("/login");
            console.log(`empty token ${token}`);
            return;
        }

        // 2. Gọi API lấy thông tin
        const fetchProfile = async () => {
            try {
                const data = await userApi.getProfile(token);
                setProfile(data);
            } catch (err: any) {
                setError(err.message);
                // Nếu token hết hạn hoặc lỗi, cho đăng xuất luôn
                if (err.message.includes("401")) logout(); 
            } finally {
                setLoading(false);
            }
        };

        fetchProfile();
    }, [token, router, logout]);

    if (isLoading) {
        return <div className="min-h-screen bg-[#0f172a] flex items-center justify-center text-white">Đang kiểm tra đăng nhập...</div>;
    }

    if (loading) {
        return <div className="min-h-screen bg-[#0f172a] flex items-center justify-center text-white">Đang tải dữ liệu...</div>;
    }

    if (error) {
        return <div className="min-h-screen bg-[#0f172a] flex items-center justify-center text-red-500">{error}</div>;
    }

    return (
        <div className="min-h-screen bg-[#0f172a] p-8 text-slate-200">
          <div className="max-w-3xl mx-auto space-y-6">
            
            {/* Header Navigation */}
            <div className="flex justify-between items-center mb-8">
              <h1 className="text-3xl font-black text-white">Tài Khoản Của Tôi</h1>
              <button 
                onClick={() => router.push("/dashboard")}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition"
              >
                Quay lại Dashboard
              </button>
            </div>

            {/* Thông tin ví ảo (Nổi bật nhất) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-[#1e293b] p-6 rounded-2xl border border-slate-700 shadow-xl">
                <h2 className="text-sm text-slate-400 font-medium mb-1">Số dư thực tế (Balance)</h2>
                <p className="text-4xl font-bold text-blue-500">
                  ${profile?.wallet.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </p>
              </div>

              <div className="bg-[#1e293b] p-6 rounded-2xl border border-slate-700 shadow-xl">
                <h2 className="text-sm text-slate-400 font-medium mb-1">Tài sản ròng (Equity)</h2>
                <p className="text-4xl font-bold text-green-500">
                  ${profile?.wallet.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </p>
              </div>
            </div>

            {/* Thông tin cá nhân */}
            <div className="bg-[#1e293b] p-6 rounded-2xl border border-slate-700 shadow-xl space-y-4">
              <h2 className="text-xl font-bold text-white mb-4 border-b border-slate-700 pb-2">Hồ sơ cá nhân</h2>
              
              <div className="flex justify-between items-center">
                <span className="text-slate-400">ID Người dùng</span>
                <span className="font-mono text-white">#{profile?.id}</span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Email đăng nhập</span>
                <span className="text-white font-medium">{profile?.email}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-400">Ngày tham gia</span>
                <span className="text-white">
                  {profile?.created_at ? new Date(profile.created_at).toLocaleDateString('vi-VN') : 'N/A'}
                </span>
              </div>
            </div>

            {/* Nút Đăng xuất */}
            <div className="pt-6">
              <button 
                onClick={logout}
                className="w-full md:w-auto px-8 py-3 bg-red-600 hover:bg-red-500 text-white font-bold rounded-lg transition shadow-lg shadow-red-500/20"
              >
                Đăng Xuất
              </button>
            </div>

          </div>
        </div>
    );
}