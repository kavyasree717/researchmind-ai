
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  User,
  Mail,
  ShieldCheck,
  LogOut,
  Settings as SettingsIcon,
  LoaderCircle,
  AlertCircle,
} from "lucide-react";

import api from "../services/api";
import Sidebar from "../components/Sidebar";
import "./Settings.css";

function Settings() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadProfile = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await api.get("/auth/me");

        if (!cancelled) {
          setUser(response.data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              "Unable to load your account information."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadProfile();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLogout() {
    if (loggingOut) return;

    setLoggingOut(true);

    try {
      await api.post("/auth/logout");
    } catch (error) {
      console.error("Logout request failed:", error);
    } finally {
      localStorage.removeItem("access_token");
      navigate("/login", { replace: true });
    }
  }

  return (
    <div className="app-layout">
      <Sidebar user={user} />

      <main className="settings-page">
        <header className="settings-header">
          <div>
            <p className="page-eyebrow">PREFERENCES</p>
            <h1>Settings</h1>
            <p>Manage your account and application access.</p>
          </div>

          <div className="settings-header-icon">
            <SettingsIcon size={25} />
          </div>
        </header>

        {loading ? (
          <div className="settings-message">
            <LoaderCircle className="spin" size={28} />
            <p>Loading account information...</p>
          </div>
        ) : (
          <>
            {error && (
              <div className="settings-error">
                <AlertCircle size={19} />
                <span>{error}</span>
              </div>
            )}

            <section className="settings-section">
              <div className="settings-section-heading">
                <User size={21} />

                <div>
                  <h2>Account Information</h2>
                  <p>Your registered ResearchMind account.</p>
                </div>
              </div>

              {user ? (
                <div className="settings-profile">
                  <div className="settings-avatar">
                    {(user.username || user.email || "U")
                      .charAt(0)
                      .toUpperCase()}
                  </div>

                  <div className="settings-profile-details">
                    <h3>{user.username || "User"}</h3>
                    <p>{user.email || "Email unavailable"}</p>
                  </div>
                </div>
              ) : (
                <p className="settings-empty">
                  Account information is unavailable.
                </p>
              )}

              <div className="settings-info-row">
                <div className="settings-info-icon">
                  <User size={19} />
                </div>

                <div>
                  <span>Username</span>
                  <strong>{user?.username || "Not available"}</strong>
                </div>
              </div>

              <div className="settings-info-row">
                <div className="settings-info-icon">
                  <Mail size={19} />
                </div>

                <div>
                  <span>Email address</span>
                  <strong>{user?.email || "Not available"}</strong>
                </div>
              </div>

              <div className="settings-info-row">
                <div className="settings-info-icon">
                  <ShieldCheck size={19} />
                </div>

                <div>
                  <span>Account status</span>
                  <strong>
                    {user?.is_active === false
                      ? "Inactive"
                      : user
                        ? "Active"
                        : "Unavailable"}
                  </strong>
                </div>
              </div>
            </section>

            <section className="settings-section">
              <div className="settings-section-heading">
                <ShieldCheck size={21} />

                <div>
                  <h2>Application Information</h2>
                  <p>About your research workspace.</p>
                </div>
              </div>

              <div className="settings-info-row">
                <div className="settings-info-icon">
                  <SettingsIcon size={19} />
                </div>

                <div>
                  <span>Application</span>
                  <strong>ResearchMind AI</strong>
                </div>
              </div>

              <div className="settings-info-row">
                <div className="settings-info-icon">
                  <ShieldCheck size={19} />
                </div>

                <div>
                  <span>Authentication</span>
                  <strong>
                    JWT-based authentication with automatic refresh
                  </strong>
                </div>
              </div>
            </section>

            <section className="settings-section logout-section">
              <div className="settings-section-heading">
                <LogOut size={21} />

                <div>
                  <h2>Sign Out</h2>
                  <p>
                    Sign out of your ResearchMind account on this browser.
                  </p>
                </div>
              </div>

              <button
                className="settings-logout-btn"
                onClick={handleLogout}
                disabled={loggingOut}
              >
                <LogOut size={18} />
                {loggingOut ? "Signing out..." : "Log Out"}
              </button>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default Settings;
