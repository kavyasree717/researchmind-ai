
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Clock3,
  FileText,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  Trash2,
} from "lucide-react";

import api from "../services/api";
import Sidebar from "../components/Sidebar";
import "./History.css";

const domains = [
  { value: "all", label: "All domains" },
  { value: "scientific", label: "Scientific Research" },
  { value: "agriculture", label: "Agriculture" },
  { value: "government_policy", label: "Government & Public Policy" },
  { value: "education", label: "Education" },
  { value: "law", label: "Law" },
];

function getRunId(item) {
  return item.id || item.run_id || item.research_run_id;
}

function getQuery(item) {
  return (
    item.query_text ||
    item.query ||
    item.title ||
    "Untitled research"
  );
}

function formatDate(value) {
  if (!value) return "Date unavailable";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }

  return date.toLocaleString();
}

function History() {
  const navigate = useNavigate();

  const [runs, setRuns] = useState([]);
  const [search, setSearch] = useState("");
  const [domain, setDomain] = useState("all");
  const [status, setStatus] = useState("all");

  const [loading, setLoading] = useState(true);
  const [deletingRunId, setDeletingRunId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/research/history", {
        params: {
          limit: 100,
          offset: 0,
        },
      });

      const data = response.data;

      const historyItems = Array.isArray(data)
        ? data
        : data.items ||
          data.runs ||
          data.history ||
          data.results ||
          [];

      setRuns(historyItems);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load research history."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const filteredRuns = useMemo(() => {
    return runs.filter((item) => {
      const query = getQuery(item).toLowerCase();
      const searchMatch = query.includes(search.toLowerCase());

      const domainMatch =
        domain === "all" || item.domain === domain;

      const statusMatch =
        status === "all" ||
        (item.status || "").toLowerCase() === status;

      return searchMatch && domainMatch && statusMatch;
    });
  }, [runs, search, domain, status]);

  const openReport = (item) => {
    const runId = getRunId(item);

    if (!runId) {
      setError("This research entry does not have a valid run ID.");
      return;
    }

    navigate(`/report/${runId}`);
  };

  const deleteResearch = async (item) => {
    const runId = getRunId(item);

    if (!runId) {
      setError("This research entry does not have a valid run ID.");
      return;
    }

    const confirmed = window.confirm(
      `Are you sure you want to delete this research?\n\n"${getQuery(item)}"\n\nIts report, evidence, and agent outputs will also be deleted. This action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      setDeletingRunId(runId);
      setError("");
      setSuccess("");

      await api.delete(`/research/history/${runId}`);

      setRuns((previousRuns) =>
        previousRuns.filter(
          (run) => getRunId(run) !== runId
        )
      );

      setSuccess("Research history deleted successfully.");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to delete this research."
      );
    } finally {
      setDeletingRunId(null);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar />

      <main className="history-page">
        <header className="history-header">
          <div>
            <p className="page-eyebrow">YOUR WORKSPACE</p>
            <h1>Research History</h1>
            <p>
              Find and revisit your previous research and reports.
            </p>
          </div>

          <button
            className="history-new-btn"
            onClick={() => navigate("/research")}
          >
            Start New Research
            <ArrowRight size={18} />
          </button>
        </header>

        <section className="history-summary">
          <div className="history-summary-icon">
            <Clock3 size={23} />
          </div>

          <div>
            <strong>{runs.length}</strong>
            <span>Total research runs loaded</span>
          </div>
        </section>

        <section className="history-controls">
          <div className="history-search">
            <Search size={19} />

            <input
              type="text"
              placeholder="Search your research..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>

          <select
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            aria-label="Filter by domain"
          >
            {domains.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label="Filter by status"
          >
            <option value="all">All statuses</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="failed">Failed</option>
          </select>

          <button
            className="history-refresh-btn"
            onClick={loadHistory}
            disabled={loading}
            title="Refresh history"
          >
            <RefreshCw size={18} />
          </button>
        </section>

        {error && (
          <div className="history-error">
            <AlertCircle size={19} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="history-success">
            {success}
          </div>
        )}

        {loading ? (
          <div className="history-message">
            <RefreshCw className="spin" size={28} />
            <p>Loading your research history...</p>
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="history-empty">
            <FileText size={38} />

            <h2>No research found</h2>

            <p>
              {runs.length === 0
                ? "Your completed and previous research runs will appear here."
                : "Try changing your search or filters."}
            </p>

            <button onClick={() => navigate("/research")}>
              Start your first research
            </button>
          </div>
        ) : (
          <section className="history-list">
            <div className="history-list-heading">
              <h2>Previous research</h2>
              <span>{filteredRuns.length} results</span>
            </div>

            {filteredRuns.map((item, index) => {
              const runId = getRunId(item);
              const itemStatus = (
                item.status || "unknown"
              ).toLowerCase();

              const isDeleting = deletingRunId === runId;
              const isRunning = [
                "pending",
                "running",
              ].includes(itemStatus);

              return (
                <article
                  className="history-card"
                  key={runId || index}
                >
                  <div className="history-card-icon">
                    <FileText size={22} />
                  </div>

                  <div className="history-card-content">
                    <h3>{getQuery(item)}</h3>

                    <div className="history-card-meta">
                      <span>
                        {item.domain || "Domain unavailable"}
                      </span>

                      <span>
                        {formatDate(
                          item.created_at ||
                          item.started_at ||
                          item.completed_at
                        )}
                      </span>
                    </div>
                  </div>

                  <div className="history-card-actions">
                    <span
                      className={`history-status status-${itemStatus}`}
                    >
                      {itemStatus}
                    </span>

                    <button
                      onClick={() => openReport(item)}
                      disabled={!runId}
                    >
                      View report
                      <ArrowRight size={16} />
                    </button>

                    <button
                      className="history-delete-btn"
                      onClick={() => deleteResearch(item)}
                      disabled={!runId || isDeleting || isRunning}
                      title={
                        isRunning
                          ? "Cannot delete research while it is running"
                          : "Delete research"
                      }
                      aria-label={`Delete research: ${getQuery(item)}`}
                    >
                      {isDeleting ? (
                        <RefreshCw className="spin" size={17} />
                      ) : (
                        <Trash2 size={17} />
                      )}
                    </button>
                  </div>
                </article>
              );
            })}
          </section>
        )}
      </main>
    </div>
  );
}

export default History;
