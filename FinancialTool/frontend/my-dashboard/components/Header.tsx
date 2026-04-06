"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/app/context/AuthContext";
import { BalanceWidget } from "./BalanceWidget";

export const Header = () => {
    const pathname = usePathname();
    const { logout } = useAuth();
    const isActive = (path: string) => pathname === path ? "text-blue-400 border-b-2 border-blue-400" : "text-slate-300 hover:text-white";

    return (
        <header className="bg-slate-900 border-b border-slate-800 h-16 flex items-center justify-between px-6">
            {/* Cụm Logo & Menu bên trái */}
            <div className="flex items-center gap-8">
                <Link href="/dashboard" className="text-xl font-black text-white tracking-wider">
                  SHINSEI <span className="text-blue-500">PRO</span>
                </Link>
                
                <nav className="flex items-center gap-6 h-16">
                    <Link href="/dashboard" className={`h-full flex items-center px-1 font-medium transition-colors ${isActive("/dashboard")}`}>
                      Giao Dịch
                    </Link>
                    <Link href="/profile" className={`h-full flex items-center px-1 font-medium transition-colors ${isActive("/profile")}`}>
                      Tài Khoản
                    </Link>
                </nav>
            </div>

            {/* Cụm Số dư & Nút Đăng xuất bên phải */}
            <div className="flex items-center gap-4">
                <BalanceWidget />
                <button 
                      onClick={logout}
                      className="text-sm text-slate-400 hover:text-red-400 transition-colors px-3 py-2 rounded-md hover:bg-slate-800"
                >
                  Đăng xuất
                </button>
            </div>
        </header>
    );
};