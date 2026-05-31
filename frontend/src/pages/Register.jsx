import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../lib/auth.jsx";
import { Button, Card, Input } from "../components/ui.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await register(email, password);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Registration failed");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-base bg-grid px-4">
      <Card className="w-full max-w-sm p-7">
        <div className="mb-6 flex items-center gap-2.5">
          <span className="mono text-warn">▓</span>
          <span className="mono text-sm font-semibold tracking-[0.18em] text-fg">PDM&nbsp;COPILOT</span>
        </div>
        <h1 className="text-base font-semibold text-fg">Create account</h1>
        <p className="mb-5 mt-0.5 text-xs uppercase tracking-wider text-faint">Predictive maintenance console</p>
        <form onSubmit={submit} className="space-y-3">
          <Input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p className="mono text-xs text-crit">{error}</p>}
          <Button type="submit" className="w-full">Register</Button>
        </form>
        <p className="mt-4 text-sm text-muted">
          Have an account?{" "}
          <Link to="/login" className="text-fg underline decoration-faint hover:decoration-fg">Sign in</Link>
        </p>
      </Card>
    </div>
  );
}
