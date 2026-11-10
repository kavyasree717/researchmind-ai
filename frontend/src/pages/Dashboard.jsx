
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  CircleCheck,
  Play,
  ChartNoAxesColumn,
  ArrowRight,
  Bell,
  Search,
  Clock3,
  Sprout,
  FlaskConical,
  Scale,
  GraduationCap,
  Landmark,
  BrainCircuit,
} from "lucide-react";

import api from "../services/api";
import Sidebar from "../components/Sidebar";
import "./Dashboard.css";

const domainIcons = {
  scientific: FlaskConical,
  agriculture: Sprout,
  government_policy: Landmark,
  education: GraduationCap,
  law: Scale,
};

function formatTime(dateString) {
  if (!dateString) return "Recently";

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "Recently";

  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatDomain(domain) {
  const names = {
    scientific: "Scientific Research",
    agriculture: "Agriculture",
    government_policy: "Government & Public Policy",
    education: "Education",
    law: "Law",
  };

  return names[domain] || domain || "Research";
}

function Dashboard() {
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [userResponse, historyResponse] = await Promise.all([
          api.get("/auth/me"),
          api.get("/research/history", {
            params: { limit: 5, offset: 0 },
          }),
        ]);

        setUser(userResponse.data);

        const records = historyResponse.data.history || [];
        setHistory(records);
        setTotal(historyResponse.data.total ?? records.length);
      } catch (err) {
        setError(
          err.response?.data?.detail ||
          "Unable to load dashboard information."
        );
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const completed = history.filter(
    (item) => item.status === "completed"
  ).length;

  const inProgress = history.filter(
    (item) => item.status === "running"
  ).length;

  const savedReports = history.filter(
    (item) => item.report
  ).length;

  return (
    <div className="dashboard-layout">

      <Sidebar user={user} />

      <main className="dashboard-main">

        <header className="dashboard-header">
          <div>
            <h1>
              Welcome back{user?.username ? `, ${user.username}` : ""}!
            </h1>
            <p>Here's your research overview.</p>
          </div>

          <button
            className="notification-button"
            title="Notifications"
            aria-label="Notifications"
          >
            <Bell size={21} />
          </button>
        </header>

        {loading ? (
          <div className="dashboard-message">
            Loading your research overview...
          </div>
        ) : error ? (
          <div className="dashboard-error">
            {error}
            <p>
              Check that the backend is running and the research history
              endpoint is registered.
            </p>
          </div>
        ) : (
          <>
            {/* Statistics */}
            <section className="stats-grid">

              <StatCard
                icon={<FileText />}
                label="Total Research"
                value={total}
                color="green"
              />

              <StatCard
                icon={<CircleCheck />}
                label="Completed"
                value={completed}
                color="success"
              />

              <StatCard
                icon={<Play />}
                label="In Progress"
                value={inProgress}
                color="yellow"
              />

              <StatCard
                icon={<ChartNoAxesColumn />}
                label="Saved Reports"
                value={savedReports}
                color="brown"
              />

            </section>

            {/* Recent research */}
            <section className="recent-section">

              <div className="section-heading">
                <div>
                  <h2>Recent Research</h2>
                  <p>Your latest research sessions.</p>
                </div>

                <Link to="/history" className="view-all">
                  View all <ArrowRight size={16} />
                </Link>
              </div>

              <div className="recent-content">

                <div className="recent-list">

                  {history.length === 0 ? (
                    <div className="empty-research">
                      <Search size={30} />
                      <h3>No research yet</h3>
                      <p>Your completed research will appear here.</p>
                      <Link to="/research" className="primary-btn">
                        Start Research
                      </Link>
                    </div>
                  ) : (
                    history.map((item) => {
                      const DomainIcon =
                        domainIcons[item.domain] || FlaskConical;

                      return (
                        <Link
                          to={`/history/${item.run_id}`}
                          className="recent-item"
                          key={item.run_id}
                        >
                          <div className="recent-icon">
                            <DomainIcon size={22} />
                          </div>

                          <div className="recent-details">
                            <strong>{item.query}</strong>
                            <span>
                              {formatDomain(item.domain)}
                              <span className="dot">•</span>
                              <Clock3 size={12} />
                              {formatTime(item.created_at)}
                            </span>
                          </div>

                          <div className={`status status-${item.status}`}>
                            {item.status || "Unknown"}
                          </div>

                          <ArrowRight
                            className="recent-arrow"
                            size={17}
                          />
                        </Link>
                      );
                    })
                  )}

                </div>

                <aside className="dashboard-quote">
                  <div className="quote-icon">
                    <BrainCircuitIcon />
                  </div>

                  <h3>
                    Research is the key to a better tomorrow.
                  </h3>

                  <ChartNoAxesColumn size={48} />
                </aside>

              </div>
            </section>

            {/* Quick action */}
            <section className="dashboard-action">
              <div>
                <h2>Ready to explore something new?</h2>
                <p>Start a research session with your AI agents.</p>
              </div>

              <Link to="/research" className="primary-btn">
                New Research <ArrowRight size={17} />
              </Link>
            </section>
          </>
        )}

      </main>
    </div>
  );
}

function BrainCircuitIcon() {
  return <BrainCircuit size={27} />;
}

function StatCard({ icon, label, value, color }) {
  return (
    <article className="stat-card">
      <div className={`stat-icon ${color}`}>
        {icon}
      </div>

      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

export default Dashboard;
