
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import Auth from "./pages/auth";
import Dashboard from "./pages/Dashboard";
import Research from "./pages/Research";
import Report from "./pages/Report";
import History from "./pages/History";
import Settings from "./pages/Settings";

import ProtectedRoute from "./components/ProtectedRoute";

import "./App.css";

function Landing() {
  return (
    <div className="landing-page">
      <nav className="navbar container">
        <a href="/" className="brand">
          🧠 ResearchMind
        </a>

        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#about">About</a>
          <a href="#features">How it works</a>
        </div>

        <a href="/login" className="nav-cta">
          Get Started
        </a>
      </nav>

      <main className="hero container" id="about">
        <section className="hero-content">
          <div className="hero-tag">
            Intelligent research platform
          </div>

          <h1>
            Smarter Research.
            <span>Deeper Insights.</span>
          </h1>

          <p className="hero-description">
            AI-powered research assistant that finds,
            verifies and organizes reliable information for you.
          </p>

          <div className="hero-actions">
            <a href="/login" className="primary-btn">
              Start Research →
            </a>

            <a href="#features" className="secondary-btn">
              Learn More
            </a>
          </div>
        </section>

        <section className="hero-visual">
          <div className="visual-background"></div>

          <div className="laptop">
            <div className="laptop-screen">
              <span>🧠</span>
              <span>ResearchMind</span>
            </div>

            <div className="laptop-base"></div>
          </div>
        </section>
      </main>

      <section className="features container" id="features">
        <div className="feature">
          <h3>Multi-Agent Analysis</h3>
          <p>
            Specialized AI agents work together to analyze your research.
          </p>
        </div>

        <div className="feature">
          <h3>Verified Sources</h3>
          <p>
            Evaluate evidence and identify unsupported claims.
          </p>
        </div>

        <div className="feature">
          <h3>Research Memory</h3>
          <p>
            Reuse and revalidate previous research.
          </p>
        </div>

        <div className="feature">
          <h3>Beautiful Reports</h3>
          <p>
            Organized findings with traceable sources.
          </p>
        </div>
      </section>

      <section className="intro container">
        <p className="section-label">
          Research, reimagined
        </p>

        <h2>Explore. Analyze. Discover.</h2>

        <p>
          Bring your documents, web information and intelligent
          research agents together in one workspace.
        </p>
      </section>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Auth />} />
        <Route path="/register" element={<Auth />} />

        <Route element={<ProtectedRoute />}>
          <Route
            path="/dashboard"
            element={<Dashboard />}
          />

          <Route
            path="/research"
            element={<Research />}
          />

          <Route
            path="/report/:runId"
            element={<Report />}
          />

          <Route
            path="/report"
            element={<Report />}
          />

          <Route
            path="/history"
            element={<History />}
          />

          <Route
            path="/history/:runId"
            element={<Report />}
          />

          <Route
            path="/settings"
            element={<Settings />}
          />
        </Route>

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
