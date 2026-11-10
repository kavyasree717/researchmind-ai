
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api import auth, documents, rag, web_research, analyzer, research_agent, critic, agents
from app.api import research_execution
from app.api import research_history


app = FastAPI(
    title="ResearchMind AI",
    version="0.1.0",
)

# Frontend CORS configuration.
# allow_credentials=True is required for refresh-token cookies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers.
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(rag.router)
app.include_router(web_research.router)
app.include_router(analyzer.router)
app.include_router(research_agent.router)
app.include_router(critic.router)
app.include_router(agents.router)
app.include_router(research_execution.router)
app.include_router(research_history.router)


@app.get("/")
def root():
    return {
        "message": "ResearchMind AI API",
        "docs": "/docs",
    }
