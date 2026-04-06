"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/services/authApi";
import { useAuth } from "@/app/context/AuthContext";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true); // Toggle giữa Login và Register
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const router = useRouter();
  const { token, saveToken } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let data;
      if (isLogin) {
        data = await authApi.login(email, password);
      } else {
        data = await authApi.register(email, password);
      }
      
      // Lưu token và đẩy vào Dashboard
      saveToken(data.access_token);
      router.push("/dashboard");
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      router.push("/dashboard");
    }
  }, [token, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0f172a] p-4">
      <div className="w-full max-w-md bg-[#1e293b] rounded-2xl border border-slate-700 shadow-2xl p-8">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-black text-white tracking-tight">
            SHINSEI <span className="text-blue-500">TRADING</span>
          </h1>
          <p className="text-slate-400 mt-2">
            {isLogin ? "Đăng nhập để vào hệ thống" : "Tạo tài khoản và nhận ngay $10,000 ảo"}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-500 text-sm text-center">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#0f172a] border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
              placeholder="trader@shinsei.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">Mật khẩu</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#0f172a] border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Đang xử lý..." : isLogin ? "Đăng Nhập" : "Đăng Ký"}
          </button>
        </form>

        {/* Toggle Mode */}
        <div className="mt-6 text-center text-sm text-slate-400">
          {isLogin ? "Chưa có tài khoản? " : "Đã có tài khoản? "}
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setError(""); // Xóa lỗi khi chuyển tab
            }}
            className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
          >
            {isLogin ? "Đăng ký ngay" : "Đăng nhập"}
          </button>
        </div>

      </div>
    </div>
  );
}