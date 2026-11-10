
import { useEffect, useState } from "react";
import {
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  ArrowLeft,
  Download,
  FileText,
  LoaderCircle,
  ExternalLink,
  BookOpen,
  Sparkles,
  Lightbulb,
  Target,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  CalendarDays,
} from "lucide-react";

import ReactMarkdown from "react-markdown";

import api from "../services/api";
import Sidebar from "../components/Sidebar";
import "./Report.css";


function parseObject(value) {
  if (!value) return {};

  if (typeof value === "object") return value;

  try {
    return JSON.parse(value);
  } catch {
    return {};
  }
}


function getReport(result) {
  if (!result) return {};

  const candidates = [
    result.report,
    result.report_result,
    result.research?.report,
  ];

  for (const candidate of candidates) {
    if (!candidate) continue;

    const parsed = parseObject(candidate);

    if (Object.keys(parsed).length > 0) {
      return parsed;
    }
  }

  return {};
}


function getList(value) {
  if (Array.isArray(value)) return value;

  if (typeof value === "string" && value.trim()) {
    return value
      .split("\n")
      .map((item) => item.replace(/^[-•]\s*/, "").trim())
      .filter(Boolean);
  }

  return [];
}


function getText(item) {
  if (typeof item === "string") return item;

  if (item && typeof item === "object") {
    return (
      item.description ||
      item.claim ||
      item.finding ||
      item.statement ||
      item.text ||
      ""
    );
  }

  return String(item ?? "");
}


function cleanEvidenceReferences(value) {
  if (typeof value !== "string") return value;

  return value
    .replace(/\[(?:E\d+)(?:\s*,\s*E\d+)*\]/gi, "")
    .replace(/\bE\d+\b/gi, "")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}


function parseTrend(item) {
  if (typeof item === "object" && item !== null) {
    return {
      title: item.trend_name || item.title || "Research trend",
      description: item.description || "",
      evidence: [],
      confidence: item.confidence || "",
    };
  }

  const value = cleanEvidenceReferences(getText(item));
  const cleaned = value.replace(/^- /, "").trim();

  const separator = cleaned.indexOf(":");

  if (separator > 0 && separator < 90) {
    return {
      title: cleaned.slice(0, separator).trim(),
      description: cleaned.slice(separator + 1).trim(),
      evidence: [],
      confidence: "",
    };
  }

  return {
    title: "Research insight",
    description: cleaned,
    evidence: [],
    confidence: "",
  };
}


function buildFallbackMarkdown(report) {
  const sections = [];

  const summary = report.executive_summary || report.summary;

  if (summary) {
    sections.push(
      `## Executive Summary\n\n${cleanEvidenceReferences(getText(summary))}`
    );
  }

  const findings = getList(report.key_findings);

  if (findings.length) {
    sections.push(
      `## Key Findings\n\n${findings
        .map((item) => cleanEvidenceReferences(getText(item)))
        .join("\n\n")}`
    );
  }

  if (report.conclusion) {
    sections.push(
      `## Conclusion\n\n${cleanEvidenceReferences(getText(report.conclusion))}`
    );
  }

  return `# ${report.title || "Research Report"}\n\n${sections.join("\n\n")}`;
}


function Report() {
  const { runId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [result, setResult] = useState(
    location.state?.result || null
  );

  const [loading, setLoading] = useState(
    !location.state?.result
  );

  const [error, setError] = useState("");


  useEffect(() => {
    let cancelled = false;

    async function loadReport() {
      if (location.state?.result) {
        setResult(location.state.result);
        setLoading(false);
        return;
      }

      if (!runId) {
        setError("No research report was selected.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const response = await api.get(
          `/research/history/${runId}`
        );

        const data = response.data;
        const savedReport = data.reports?.[0] || {};

        const parsedContent = parseObject(savedReport.content);

        const reportData = {
          ...parsedContent,
          title: savedReport.title || parsedContent.title,
          report_markdown:
            savedReport.markdown_content ||
            parsedContent.report_markdown ||
            parsedContent.markdown_content ||
            "",
        };

        if (!cancelled) {
          setResult({
            ...data,
            report: reportData,
            evidence: data.evidence || [],
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              "Unable to load this research report."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadReport();

    return () => {
      cancelled = true;
    };
  }, [runId, location.state?.result]);


  const report = getReport(result);

  const title = report.title || "Your Research Report";

  const summary =
    report.executive_summary ||
    report.summary ||
    "";

  const findings = getList(report.key_findings);

  const trends = getList(report.trend_analysis)
    .map(parseTrend)
    .filter((item) => item.description);

  const evidence = Array.isArray(result?.evidence)
    ? result.evidence
    : [];

  const conclusion = report.conclusion || "";

  const markdown =
    report.report_markdown ||
    report.markdown_content ||
    buildFallbackMarkdown(report);

  const domain =
    result?.domain ||
    result?.run?.domain ||
    report.domain ||
    "";

  const query =
    result?.query ||
    result?.run?.query ||
    "";


  function downloadReport() {
    const cleanedMarkdown = cleanEvidenceReferences(markdown);

    const blob = new Blob(
      [cleanedMarkdown],
      { type: "text/markdown;charset=utf-8" }
    );

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download = "ResearchMind-Report.md";

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    URL.revokeObjectURL(url);
  }


  if (loading) {
    return (
      <div className="app-layout">
        <Sidebar />

        <main className="report-page">
          <div className="report-loading">
            <LoaderCircle size={35} className="spin" />
            <p>Preparing your report...</p>
          </div>
        </main>
      </div>
    );
  }


  if (error) {
    return (
      <div className="app-layout">
        <Sidebar />

        <main className="report-page">
          <div className="report-error">
            <AlertCircle size={30} />
            <h2>Unable to load report</h2>
            <p>{error}</p>

            <button onClick={() => navigate("/research")}>
              <ArrowLeft size={17} />
              Back to Research
            </button>
          </div>
        </main>
      </div>
    );
  }


  if (!result) return null;


  return (
    <div className="app-layout">
      <Sidebar />

      <main className="report-page">

        {/* Header */}
        <header className="report-topbar">
          <div>
            <p className="page-eyebrow">YOUR RESEARCH LIBRARY</p>
            <h1>Research Report</h1>
          </div>

          <div className="report-topbar-actions">
            <button
              className="report-back-btn"
              onClick={() => navigate("/research")}
            >
              <ArrowLeft size={17} />
              New Research
            </button>

            <button
              className="report-download-btn"
              onClick={downloadReport}
            >
              <Download size={17} />
              Download
            </button>
          </div>
        </header>


        {/* Report title card */}
        <section className="report-hero">
          <div className="report-hero-icon">
            <FileText size={25} />
          </div>

          <div className="report-hero-content">
            <span className="report-complete-label">
              <CheckCircle2 size={14} />
              Research completed
            </span>

            <h2>{title}</h2>

            {query && (
              <p className="report-question">
                {query}
              </p>
            )}

            {domain && (
              <div className="report-domain">
                {domain.replaceAll("_", " ")}
              </div>
            )}
          </div>

          <div className="report-hero-decoration">
            <Sparkles size={55} />
          </div>
        </section>


        {/* Overview cards */}
        <section className="report-overview">
          <div className="overview-card">
            <div className="overview-icon green">
              <Lightbulb size={20} />
            </div>

            <div>
              <strong>{findings.length}</strong>
              <span>Key findings</span>
            </div>
          </div>

          <div className="overview-card">
            <div className="overview-icon sand">
              <TrendingUp size={20} />
            </div>

            <div>
              <strong>{trends.length}</strong>
              <span>Research insights</span>
            </div>
          </div>

          <div className="overview-card">
            <div className="overview-icon blue">
              <BookOpen size={20} />
            </div>

            <div>
              <strong>{evidence.length}</strong>
              <span>Sources collected</span>
            </div>
          </div>
        </section>


        {/* Executive summary */}
        {summary && (
          <section className="report-section">
            <div className="report-section-title">
              <div className="section-icon">
                <Sparkles size={19} />
              </div>

              <div>
                <h2>Executive Summary</h2>
                <p>The central ideas from your research.</p>
              </div>
            </div>

            <div className="summary-card">
              <ReactMarkdown>
                {cleanEvidenceReferences(String(summary))}
              </ReactMarkdown>
            </div>
          </section>
        )}


        {/* Key findings - normal paragraphs */}
        {findings.length > 0 && (
          <section className="report-section">
            <div className="report-section-title">
              <div className="section-icon">
                <Target size={19} />
              </div>

              <div>
                <h2>Key Findings</h2>
                <p>Important findings identified during research.</p>
              </div>
            </div>

            <div className="key-findings-paragraphs">
              {findings.map((item, index) => (
                <ReactMarkdown key={index}>
                  {cleanEvidenceReferences(getText(item))}
                </ReactMarkdown>
              ))}
            </div>
          </section>
        )}


        {/* Trends */}
        {trends.length > 0 && (
          <section className="report-section">
            <div className="report-section-title">
              <div className="section-icon">
                <TrendingUp size={19} />
              </div>

              <div>
                <h2>Trends & Insights</h2>
                <p>Patterns and developments found in the research.</p>
              </div>
            </div>

            <div className="trend-grid">
              {trends.map((trend, index) => (
                <article className="trend-card" key={index}>
                  <div className="trend-card-top">
                    <span>
                      INSIGHT {String(index + 1).padStart(2, "0")}
                    </span>

                    <TrendingUp size={17} />
                  </div>

                  <h3>{cleanEvidenceReferences(trend.title)}</h3>

                  <p>
                    {cleanEvidenceReferences(trend.description)}
                  </p>
                </article>
              ))}
            </div>
          </section>
        )}


        {/* Conclusion */}
        {conclusion && (
          <section className="report-section">
            <div className="report-section-title">
              <div className="section-icon">
                <CheckCircle2 size={19} />
              </div>

              <div>
                <h2>Conclusion</h2>
                <p>What the research tells us overall.</p>
              </div>
            </div>

            <div className="conclusion-card">
              <ReactMarkdown>
                {cleanEvidenceReferences(String(conclusion))}
              </ReactMarkdown>
            </div>
          </section>
        )}


        {/* Sources */}
        {evidence.length > 0 && (
          <section className="report-section">
            <div className="report-section-title">
              <div className="section-icon">
                <BookOpen size={19} />
              </div>

              <div>
                <h2>Research Sources</h2>
                <p>Explore the material used to prepare this report.</p>
              </div>
            </div>

            <div className="source-grid">
              {evidence.map((item, index) => (
                <article
                  className="report-source-card"
                  key={item.evidence_id || item.id || index}
                >
                  <div className="source-card-top">
                    <span className="source-type">
                      {item.source_type || "Research Source"}
                    </span>
                  </div>

                  <h3>{item.title || "Research source"}</h3>

                  {item.published_date && (
                    <div className="source-date">
                      <CalendarDays size={13} />
                      {item.published_date}
                    </div>
                  )}

                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Explore source
                      <ExternalLink size={14} />
                    </a>
                  )}
                </article>
              ))}
            </div>
          </section>
        )}


        {/* Footer */}
        <footer className="report-footer">
          <span>ResearchMind AI</span>
          <span>Explore. Analyze. Discover.</span>
        </footer>

      </main>
    </div>
  );
}

export default Report;
