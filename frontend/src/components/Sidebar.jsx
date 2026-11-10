
import { NavLink, useNavigate } from "react-router-dom";
import {
  BrainCircuit,
  LayoutDashboard,
  Search,
  History,
  Settings,
  LogOut,
  UserRound,
} from "lucide-react";

import api from "../services/api";
import "./Sidebar.css";

function Sidebar({ user }) {
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await api.post("/auth/logout");
    } catch (error) {
      console.error("Logout request failed:", error);
    } finally {
      localStorage.removeItem("access_token");
      navigate("/login", { replace: true });
    }
  }

  const username = user?.username || "Researcher";
  const email = user?.email || "";

  return (
    <aside className="sidebar">

      <a href="/dashboard" className="sidebar-brand">
        <BrainCircuit size={28} />
        <span>ResearchMind</span>
      </a>

      <nav className="sidebar-nav">

        <NavLink to="/dashboard" className="sidebar-link">
          <LayoutDashboard size={19} />
          <span>Dashboard</span>
        </NavLink>

        <NavLink to="/research" className="sidebar-link">
          <Search size={19} />
          <span>New Research</span>
        </NavLink>

        <NavLink to="/history" className="sidebar-link">
          <History size={19} />
          <span>History</span>
        </NavLink>

        <NavLink to="/settings" className="sidebar-link">
          <Settings size={19} />
          <span>Settings</span>
        </NavLink>

      </nav>

      <div className="sidebar-user">
        <div className="sidebar-avatar">
          <UserRound size={19} />
        </div>

        <div className="sidebar-user-info">
          <strong>{username}</strong>
          <span>{email}</span>
        </div>

        <button
          className="sidebar-logout"
          onClick={handleLogout}
          title="Logout"
          aria-label="Logout"
        >
          <LogOut size={17} />
        </button>
      </div>

    </aside>
  );
}

export default Sidebar;
