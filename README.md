# researchmind-ai
ResearchMind AI

A Domain-Adaptive Multi-Agent Research Platform

ResearchMind AI is an AI-powered research platform that uses multiple specialized AI agents to conduct, analyze, verify, and organize research information.

Unlike traditional AI tools that provide a single response, ResearchMind AI follows a multi-agent approach where different agents perform specialized tasks, evaluate information, identify trends, verify facts, and generate a structured research report.

The platform supports multiple research domains, helping users obtain more organized, evidence-based, and reliable research results.

Problem Statement

Traditional AI research tools may produce incomplete information, outdated results, unsupported claims, or one-sided answers. Users often need to verify information manually and compare multiple sources.

ResearchMind AI addresses these challenges through a collaborative multi-agent workflow that improves research organization, evidence evaluation, and information verification.

Objectives

Develop a domain-adaptive research platform.

Use multiple specialized AI agents for research tasks.

Improve the reliability of information through fact verification.

Identify recent developments and emerging trends.

Support web-based research and document-based research.

Generate structured and understandable research reports.

Supported Research Domains

ResearchMind AI supports five research domains:

Domain

Description

Scientific Research

Scientific studies and research topics

Agriculture

Agricultural technologies and developments

Government Policy

Policies, regulations, and government initiatives

Education

Educational systems, methods, and technologies

Law

Legal topics, laws, and regulations

Multi-Agent Architecture

The platform uses six specialized agents:

Agent

Responsibility

Research Agent

Collects relevant information from available sources.

Critic Agent

Evaluates research findings and identifies weaknesses or gaps.

Trend Agent

Identifies emerging trends and recent developments.

Fact Verification Agent

Checks claims against available evidence.

Judge Agent

Evaluates agent outputs and helps resolve conflicting findings.

Report Agent

Combines the research results into a structured report.

Each agent performs a specific responsibility, contributing to the overall research process.

How It Works

User Input: The user enters a research question and selects a domain.

Query Analysis: The query analyzer identifies the research intent, complexity, and required agents.

Information Retrieval: Relevant information is collected through web research and uploaded documents when enabled.

Multi-Agent Processing: Selected agents perform their specialized research tasks.

Evaluation and Verification: Findings are evaluated, and claims are checked against available evidence.

Report Generation: The report agent organizes the results into a structured research report.

Result Presentation: The user receives the generated research report through the frontend.

Key Features

Domain-adaptive research.

Multi-agent research workflow.

Dynamic agent selection based on query analysis.

Web-based information retrieval.

PDF document upload and research.

Evidence-based fact verification.

Research trend identification.

Structured research report generation.

PostgreSQL-based data storage.

Vector similarity search using pgvector.

Technology Stack

Category

Technologies

Frontend

React.js, Vite, CSS

Backend

Python, FastAPI

Database

PostgreSQL

Vector Database

pgvector

AI Integration

Groq / OpenRouter

AI Models

Configurable LLM models

Agent Workflow

Custom multi-agent architecture

ORM

SQLAlchemy

API Communication

REST API

Containerization

Docker

Project Structure

researchmind-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── .gitignore
└── README.md

Note: The folder structure above illustrates the main project organization. Adjust it to match the actual folders in your repository.

Installation and Setup

Prerequisites

Python

Node.js and npm

PostgreSQL with pgvector

Docker (if using the Docker database setup)

Groq or OpenRouter API credentials

1. Clone the Repository

git clone https://github.com/kavyasree717/researchmind-ai.git
cd researchmind-ai

2. Backend Setup

cd backend

python -m venv .venv

Activate the environment on Windows:

.\.venv\Scripts\Activate.ps1

Install dependencies:

pip install -r requirements.txt

Configure your environment variables using .env.example as a reference. Add your own API credentials and database configuration to backend/.env.

Start the backend:

uvicorn app.main:app --reload --port 8000

Backend API documentation:

http://localhost:8000/docs

3. Frontend Setup

Open another terminal:

cd frontend
npm install
npm run dev

Frontend:

http://localhost:5173

Database

ResearchMind AI uses PostgreSQL for storing application and research data.

The pgvector extension supports vector embeddings and similarity-based retrieval, helping the platform identify relevant previously stored research information.

Expected Output

The platform takes a research question and selected domain as input and produces an organized research report containing relevant findings, supporting evidence, verification results, and research trends where applicable.

Future Enhancements

Improve conflict detection and resolution between agents.

Enhance evidence quality assessment and source credibility evaluation.

Implement improved research freshness monitoring.

Expand domain-specific research capabilities.

Improve report export and visualization options.

Optimize agent coordination and research performance.

Project Goal

The goal of ResearchMind AI is to make AI-assisted research more systematic, evidence-oriented, and transparent by combining multiple specialized agents into a single research platform.