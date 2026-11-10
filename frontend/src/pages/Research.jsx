import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Upload,
  FileText,
  Globe,
  BrainCircuit,
  X,
  LoaderCircle,
  Sparkles,
  CheckCircle2,
  Circle,
  ShieldCheck,
  ChartNoAxesCombined,
  ClipboardCheck,
  FileCheck2,
  Clock3,
} from "lucide-react";

import api from "../services/api";
import Sidebar from "../components/Sidebar";
import "./Research.css";

const domains = [
  { value: "scientific", label: "Scientific Research" },
  { value: "agriculture", label: "Agriculture" },
  { value: "government_policy", label: "Government & Public Policy" },
  { value: "education", label: "Education" },
  { value: "law", label: "Law" },
];

const workflowStages = [
  {
    name: "Research Agent",
    description: "Collecting relevant information and source evidence.",
    icon: Search,
  },
  {
    name: "Trend Agent",
    description: "Identifying patterns, developments and research gaps.",
    icon: ChartNoAxesCombined,
  },
  {
    name: "Fact Verification Agent",
    description: "Checking claims against the collected evidence.",
    icon: ShieldCheck,
  },
  {
    name: "Report Agent",
    description: "Organizing the findings into your final report.",
    icon: FileCheck2,
  },
];

function ResearchProgress({ activeStage, uploadStatus }) {
  const progress = [18, 40, 64, 86][activeStage];

  return (
    <section className="workflow-screen">
      <div className="workflow-card">
        <div className="workflow-heading">
          <div className="workflow-orbit">
            <BrainCircuit size={34} />
            <span className="orbit-dot orbit-dot-one" />
            <span className="orbit-dot orbit-dot-two" />
          </div>

          <span className="workflow-eyebrow">
            RESEARCHMIND WORKSPACE
          </span>

          <h1>Building your research report</h1>

          <p>
            Your research workflow is underway. The findings are being
            organized into a structured report.
          </p>
        </div>

        <div className="workflow-progress-header">
          <span>Research workflow</span>
          <span>{progress}%</span>
        </div>

        <div className="workflow-progress-track">
          <div
            className="workflow-progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="workflow-stages">
          {workflowStages.map((stage, index) => {
            const Icon = stage.icon;
            const completed = index < activeStage;
            const active = index === activeStage;

            return (
              <div
                className={`workflow-stage ${
                  completed ? "completed" : ""
                } ${active ? "active" : ""}`}
                key={stage.name}
              >
                <div className="workflow-stage-icon">
                  {completed ? (
                    <CheckCircle2 size={20} />
                  ) : active ? (
                    <LoaderCircle size={20} className="spin" />
                  ) : (
                    <Circle size={20} />
                  )}
                </div>

                <div className="workflow-stage-symbol">
                  <Icon size={19} />
                </div>

                <div className="workflow-stage-content">
                  <strong>{stage.name}</strong>
                  <p>{stage.description}</p>
                </div>

                <span className="workflow-stage-status">
                  {completed
                    ? "Completed"
                    : active
                      ? "In progress"
                      : "Upcoming"}
                </span>
              </div>
            );
          })}
        </div>

        <div className="workflow-footer">
          <div className="workflow-footer-icon">
            <Clock3 size={17} />
          </div>

          <div>
            <strong>
              {uploadStatus || "Research is in progress"}
            </strong>
            <p>
              Keep this page open while your report is being prepared.
            </p>
          </div>
        </div>

        <p className="workflow-transparency">
          Stage indicators are a visual workflow guide. Individual agent
          completion events are not yet streamed by the backend.
        </p>
      </div>
    </section>
  );
}

function Research() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("scientific");
  const [useWeb, setUseWeb] = useState(true);
  const [useDocuments, setUseDocuments] = useState(false);
  const [file, setFile] = useState(null);

  const [loading, setLoading] = useState(false);
  const [activeStage, setActiveStage] = useState(0);
  const [uploadStatus, setUploadStatus] = useState("");
  const [error, setError] = useState("");

  // Visual stage progression while the API request is running.
  useEffect(() => {
    if (!loading) return undefined;

    const timer = window.setInterval(() => {
      setActiveStage((current) =>
        Math.min(current + 1, workflowStages.length - 1)
      );
    }, 6500);

    return () => window.clearInterval(timer);
  }, [loading]);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) return;

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF file.");
      event.target.value = "";
      return;
    }

    if (selectedFile.size > 20 * 1024 * 1024) {
      setError("The PDF must be smaller than 20 MB.");
      event.target.value = "";
      return;
    }

    setFile(selectedFile);
    setUseDocuments(true);
    setError("");
    setUploadStatus("");
  };

  const removeFile = () => {
    setFile(null);
    setUploadStatus("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleStartResearch = async () => {
    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      setError("Please enter a research question.");
      return;
    }

    if (!useWeb && !useDocuments) {
      setError("Select at least one research source.");
      return;
    }

    setLoading(true);
    setActiveStage(0);
    setError("");
    setUploadStatus("");

    try {
      if (file) {
        setUploadStatus("Uploading your PDF...");

        const formData = new FormData();
        formData.append("file", file);

        await api.post("/documents/upload", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          timeout: 120000,
        });

        setUploadStatus("PDF uploaded. Starting research...");
      } else {
        setUploadStatus("Preparing your research workflow...");
      }

      const response = await api.post(
        "/research/execute",
        {
          query: trimmedQuery,
          domain,
          use_web: useWeb,
          use_documents: useDocuments,
        },
        {
          timeout: 180000,
        }
      );

      const data = response.data;

      const runId =
        data.run_id ||
        data.research_run_id ||
        data.run?.id ||
        data.research_run?.id;

      if (!runId) {
        throw new Error(
          "Research completed, but no research run ID was returned."
        );
      }

      navigate(`/report/${runId}`, {
        state: {
          result: data,
          query: trimmedQuery,
          domain,
        },
      });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to start research. Please try again."
      );

      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="app-layout">
        <Sidebar />

        <main className="research-page">
          <ResearchProgress
            activeStage={activeStage}
            uploadStatus={uploadStatus}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar />

      <main className="research-page">
        <div className="research-header">
          <div>
            <p className="page-eyebrow">YOUR RESEARCH WORKSPACE</p>
            <h1>What would you like to discover?</h1>
            <p>
              Start with a question. ResearchMind will organize the
              research into a clear, structured report.
            </p>
          </div>

          <div className="research-header-icon">
            <BrainCircuit size={27} />
          </div>
        </div>

        <section className="research-container">
          <div className="research-card">
            <div className="research-card-heading">
              <div className="heading-icon">
                <Sparkles size={22} />
              </div>

              <div>
                <h2>Start a new research project</h2>
                <p>
                  Describe the topic or problem you want to understand.
                </p>
              </div>
            </div>

            <label className="research-label" htmlFor="research-query">
              Research question
            </label>

            <textarea
              id="research-query"
              className="research-textarea"
              placeholder="Example: How is artificial intelligence transforming modern agricultural practices?"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              rows={5}
            />

            <div className="research-field">
              <label className="research-label" htmlFor="research-domain">
                Research domain
              </label>

              <select
                id="research-domain"
                className="research-select"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
              >
                {domains.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="research-field">
              <label className="research-label">Research sources</label>

              <div className="source-options">
                <label className={`source-option ${useWeb ? "selected" : ""}`}>
                  <input
                    type="checkbox"
                    checked={useWeb}
                    onChange={(event) => setUseWeb(event.target.checked)}
                  />

                  <Globe size={23} />

                  <span>
                    <strong>Web research</strong>
                    <small>
                      Discover information from online sources.
                    </small>
                  </span>
                </label>

                <label
                  className={`source-option ${
                    useDocuments ? "selected" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={useDocuments}
                    onChange={(event) =>
                      setUseDocuments(event.target.checked)
                    }
                  />

                  <FileText size={23} />

                  <span>
                    <strong>Document research</strong>
                    <small>
                      Use your uploaded PDF documents.
                    </small>
                  </span>
                </label>
              </div>
            </div>

            <div className="research-field">
              <label className="research-label">
                Add a research document
                <span className="optional-label"> OPTIONAL</span>
              </label>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                hidden
                onChange={handleFileChange}
              />

              {!file ? (
                <button
                  type="button"
                  className="upload-area"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="upload-icon">
                    <Upload size={23} />
                  </div>

                  <strong>Choose a PDF document</strong>
                  <span>PDF format · Maximum 20 MB</span>
                </button>
              ) : (
                <div className="selected-file">
                  <FileText size={24} />

                  <div className="selected-file-info">
                    <strong>{file.name}</strong>
                    <small>
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </small>
                  </div>

                  <button
                    type="button"
                    onClick={removeFile}
                    aria-label="Remove selected PDF"
                  >
                    <X size={19} />
                  </button>
                </div>
              )}
            </div>

            {error && (
              <p className="research-error">{error}</p>
            )}

            <button
              type="button"
              className="start-research-btn"
              onClick={handleStartResearch}
            >
              <Sparkles size={19} />
              Generate Research Report
              <Search size={18} />
            </button>

            <p className="research-note">
              ResearchMind gathers information, checks evidence and
              prepares your report.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

export default Research;