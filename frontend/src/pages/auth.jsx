import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BrainCircuit,
  Mail,
  LockKeyhole,
  Eye,
  EyeOff,
  ArrowRight,
  UserRound,
} from "lucide-react";
import api from "../services/api";
import "./Auth.css";

function Auth() {
  const navigate = useNavigate();

  const [mode, setMode] = useState("login");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [rememberMe, setRememberMe] = useState(true);

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
  });

  const isRegister = mode === "register";

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setError("");
    setSuccess("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (isRegister) {
        await api.post("/auth/register", {
          username: form.username,
          email: form.email,
          password: form.password,
        });

        setSuccess("Account created successfully. You can now sign in.");

        setMode("login");

        setForm((previous) => ({
          ...previous,
          password: "",
        }));
      } else {
        const response = await api.post("/auth/login", {
          email: form.email,
          password: form.password,
          remember_me: rememberMe,
        }, {
          timeout: 120000,
        });

        const token = response.data.access_token;

        if (!token) {
          throw new Error("The server did not return an access token.");
        }

        localStorage.setItem("access_token", token);

        navigate("/dashboard");
      }
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((item) => item.msg).join(", ")
            : err.message || "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">

      {/* Left branding panel */}
      <section className="auth-brand-panel">
        <a href="/" className="auth-brand">
          <BrainCircuit size={58} strokeWidth={1.5} />
          <h1>ResearchMind</h1>
        </a>

        <p className="auth-tagline">
          Explore. Analyze. Discover.
        </p>

        <div className="auth-brand-footer">
          Intelligent research starts here.
        </div>
      </section>

      {/* Right form panel */}
      <section className="auth-form-panel">
        <div className="auth-card">

          {/* Tabs */}
          <div className="auth-tabs">
            <button
              className={mode === "login" ? "active" : ""}
              onClick={() => switchMode("login")}
              type="button"
            >
              Login
            </button>

            <button
              className={mode === "register" ? "active" : ""}
              onClick={() => switchMode("register")}
              type="button"
            >
              Register
            </button>
          </div>

          <div className="auth-heading">
            <h2>
              {isRegister ? "Create Your Account" : "Welcome Back!"}
            </h2>

            <p>
              {isRegister
                ? "Join ResearchMind and begin your research journey."
                : "Sign in to continue your research journey."}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">

            {isRegister && (
              <label className="auth-input">
                <UserRound size={19} />

                <input
                  type="text"
                  name="username"
                  placeholder="Username"
                  value={form.username}
                  onChange={handleChange}
                  minLength={3}
                  maxLength={100}
                  required
                />
              </label>
            )}

            <label className="auth-input">
              <Mail size={19} />

              <input
                type="email"
                name="email"
                placeholder="Email address"
                value={form.email}
                onChange={handleChange}
                required
              />
            </label>

            <label className="auth-input">
              <LockKeyhole size={19} />

              <input
                type={showPassword ? "text" : "password"}
                name="password"
                placeholder="Password"
                value={form.password}
                onChange={handleChange}
                minLength={8}
                maxLength={128}
                required
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
              </button>
            </label>

            {!isRegister && (
              <div className="auth-options">
                <span className="remember-option">
                  <input
                    type="checkbox"
                    id="remember"
                    checked={rememberMe}
                    onChange={(event) =>
                      setRememberMe(event.target.checked)
                    }
                  />

                  <label htmlFor="remember">
                    Remember me
                  </label>
                </span>

                <span className="forgot-label">
                  Forgot password?
                </span>
              </div>
            )}

            {error && (
              <div className="auth-message error-message">
                {error}
              </div>
            )}

            {success && (
              <div className="auth-message success-message">
                {success}
              </div>
            )}

            <button
              type="submit"
              className="auth-submit"
              disabled={loading}
            >
              {loading
                ? "Please wait..."
                : isRegister
                  ? "Create Account"
                  : "Sign In"}

              {!loading && <ArrowRight size={18} />}
            </button>

          </form>

          <p className="auth-switch">
            {isRegister
              ? "Already have an account?"
              : "Don't have an account?"}

            <button
              type="button"
              onClick={() =>
                switchMode(isRegister ? "login" : "register")
              }
            >
              {isRegister ? "Sign in" : "Sign up"}
            </button>
          </p>

        </div>
      </section>

    </main>
  );
}

export default Auth;