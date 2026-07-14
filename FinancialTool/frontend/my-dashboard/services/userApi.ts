// src/services/userApi.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export const userApi = {
    async getProfile(token: string) {
        const res = await fetch(`${API_URL}/api/user/me`, {
            method: "GET",
            headers: { 
                "Content-Type": "application/json", 
                "Authorization": `Bearer ${token}`
            },
        });
        if (!res.ok) {
            const error = await res.json();
        }
        return res.json(); 
    },
};