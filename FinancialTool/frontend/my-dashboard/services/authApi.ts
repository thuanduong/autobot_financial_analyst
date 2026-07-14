// src/services/authApi.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export const authApi = {
  async login(email: string, password: string) {
    console.log('login', API_URL);
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Đăng nhập thất bại");
    }
    //console.log('login result', res.json());
    return res.json(); // Trả về { access_token, token_type }
  },

  async register(email: string, password: string) {
    const res = await fetch(`${API_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Đăng ký thất bại");
    }
    return res.json();
  },
};