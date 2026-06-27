# 🚀 AI LinkedIn Post Generator & Fact-Checker

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28.0-ff4b4b.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent application that generates engaging LinkedIn posts and automatically fact-checks them for accuracy. Built with modern AI technologies.

---

## ✨ Features

### 🤖 AI-Powered Generation
- Generate multiple unique LinkedIn posts from any topic
- Multiple writing styles: storytelling, data-driven, thought leadership
- Support for Groq, Google Gemini, and OpenAI models
- Customizable tone, length, and target audience

### ✅ Intelligent Fact-Checking
- Automatic extraction of factual claims
- Real-time verification using web search
- Confidence scoring for each claim
- Detailed reports with evidence sources

### 📊 Advanced Analytics
- Engagement score prediction
- Performance tracking over time
- Sentiment and readability analysis
- Visual trend charts and metrics
- Improvement recommendations

### 🌍 Multi-Language Support
- Generate posts in 17+ languages
- Automatic language detection
- Cultural adaptation
- Bulk translation

### 🔄 Automated Scheduling
- Schedule posts at regular intervals
- Cron expression support
- Persistent job storage
- Job management UI

### 🚀 Production-Ready
- Docker containerization
- Redis caching for performance
- SQLite/PostgreSQL database
- Comprehensive logging
- CI/CD pipeline
- Extensive test coverage

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Backend | Python 3.10+ |
| LLM Integration | LangChain |
| LLM Providers | Groq, Google Gemini, OpenAI |
| Database | SQLAlchemy + SQLite/PostgreSQL |
| Caching | Redis |
| Scheduling | APScheduler |
| Analytics | Pandas, Plotly |
| Testing | Pytest |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Logging | Loguru |

---

## 📋 Prerequisites

- Python 3.10+
- Docker (optional)
- API Keys for:
  - [Groq](https://groq.com/) (recommended)
  - [SerpAPI](https://serpapi.com/) for fact-checking
  - [Google Gemini](https://ai.google.dev/) (optional)
  - [OpenAI](https://openai.com/) (optional)

---

## 🚀 Quick Start

### Option 1: Run with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/linkedin-post-generator.git
cd linkedin-post-generator

# Create .env file with your API keys
cp .env.example .env
# Edit .env with your API keys

# Run with Docker Compose
docker-compose up -d

# Access the application
open http://localhost:8501

# Clone the repository
git clone https://github.com/yourusername/linkedin-post-generator.git
cd linkedin-post-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python -c "from models import init_db; init_db()"

# Run the application
streamlit run app.py

# Access the application
open http://localhost:8501