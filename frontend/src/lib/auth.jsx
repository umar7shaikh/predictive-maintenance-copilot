import { createContext, useContext, useEffect, useState } from "react";
import api from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("pdm_token"));
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => setUser(null));
  }, [token]);

  async function login(email, password) {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const r = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    localStorage.setItem("pdm_token", r.data.access_token);
    setToken(r.data.access_token);
  }

  async function register(email, password) {
    await api.post("/auth/register", { email, password });
    await login(email, password);
  }

  function logout() {
    localStorage.removeItem("pdm_token");
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
