
import { useState } from "react";
import { LockKeyhole, UserRound, Eye, EyeOff, Gem } from "lucide-react";
import api from "../services/api";
import "./Login.css";

function Login({ onLogin, onRegister }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!username.trim() || !password) {
      setError("Please enter your username and password.");
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("login/", {
        username: username.trim(),
        password,
      });

      localStorage.setItem("access_token", response.data.access);
      localStorage.setItem("refresh_token", response.data.refresh);

      onLogin();
    } catch (err) {
      if (err.response?.status === 401) {
        setError("Invalid username or password.");
      } else {
        setError("Unable to connect. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-decoration">
        <div className="login-brand">
          <div className="login-logo">L</div>
          <div>
            <h1>LOANER</h1>
            <span>PAWN MANAGEMENT</span>
          </div>
        </div>

        <div className="login-message">
          <Gem size={42} />
          <h2>Manage your business with confidence.</h2>
          <p>
            Your shops, customers, loans and payments —
            all in one secure workspace.
          </p>
        </div>

        <span className="login-copyright">LOANER © 2026</span>
      </div>

      <div className="login-form-section">
        <form className="login-card" onSubmit={handleSubmit}>
          <p className="login-eyebrow">WELCOME BACK</p>
          <h2>Owner Login</h2>
          <p className="login-description">
            Sign in to access your business dashboard.
          </p>

          <label>Username</label>
          <div className="login-input">
            <UserRound size={18} />
            <input
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <label>Password</label>
          <div className="login-input">
            <LockKeyhole size={18} />
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          {error && <p className="login-error">{error}</p>}

          <button
            type="submit"
            className="login-submit"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>

          <p className="login-security">
            <LockKeyhole size={14} />
            Secure owner access
          </p>
        </form>

        <div className="login-footer">
            Don't have an account?{" "}
            <button type="button" onClick={onRegister}>
                Create Account
            </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
