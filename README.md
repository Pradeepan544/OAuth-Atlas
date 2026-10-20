# OAuth Atlas — Integration Guide Builder

An AI-assisted OAuth integration research tool that helps developers understand provider setup requirements, implementation effort, potential blockers, and approval uncertainties. Users can enter an app name or website and generate a source-backed integration guide.

## Features

- **Live guide generation:** Enter an app URL, requested permissions, and integration goal.
- **AI-assisted research:** Investigates provider documentation and generates actionable setup steps.
- **Effort estimation:** Provides estimated hands-on time and difficulty.
- **Evidence and uncertainty:** Surfaces sources, prerequisites, known blockers, and details requiring verification.
- **Developer handoff:** Distinguishes actions the developer must perform from AI-generated guidance.
- **Persistent guides:** Saves generated guides so they can be retrieved by their guide ID.

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, JavaScript
- **AI:** OpenRouter-compatible chat completions API
- **Web research:** Tavily Search API
- **Storage:** SQLite

## Prerequisites

- Python 3.11 or later
- Git (optional, for cloning the repository)
- API keys for the configured AI provider and Tavily Search

## Setup and Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/oauth-atlas.git
cd oauth-atlas
```

Alternatively, download the repository ZIP from GitHub and extract it.

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use the environment's Python executable directly in the following steps.

### 3. Install dependencies

From the project root, run:

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create your local `.env` file by copying `.env.example`:

```powershell
Copy-Item .env.example .env
```

Open `.env` and enter your own API credentials. Never commit `.env` or expose API keys in the frontend or repository.

Configure the required variables using the names and formats provided in `.env.example`. For the OpenRouter setup used during development, the relevant settings include:

```dotenv
MISTRAL_API_KEY=your_openrouter_api_key
MISTRAL_MODEL=dots-studio/dots-3-note-preview:free
MISTRAL_URL=https://openrouter.ai/api/v1/chat/completions
MISTRAL_MAX_TOKENS=6000
TAVILY_API_KEY=your_tavily_api_key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```

Use the remaining configuration values and variable names from `.env.example`. Free model availability and output behavior may vary.

### 5. Start the backend

Open a PowerShell terminal in the project root:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

The backend will be available at:

- API: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Keep this terminal running.

### 6. Start the frontend

Open a **second PowerShell terminal**:

```powershell
cd oauth_atlas_local_frontend
python -m http.server 3000 --bind 127.0.0.1
```

If you are already in the frontend folder, run only the second command.

Open the application in your browser:

`http://localhost:3000`

### 7. Generate an integration guide

1. Enter an app name or website, such as `notion.so`.
2. Describe the requested permissions, if applicable.
3. Explain what the integration should do.
4. Generate the guide.
5. Review the setup steps, effort estimate, prerequisites, blockers, sources, and items requiring verification.

Generated guides are stored by the backend and can be retrieved using their guide IDs through the API, subject to the implemented endpoints.

## Project Structure

```text
oauth-atlas/
├── app/                         # FastAPI backend and research logic
├── oauth_atlas_local_frontend/  # Browser-based frontend
├── tests/                       # Automated tests
├── .env.example                 # Environment configuration template
├── .gitignore
├── requirements.txt
└── README.md
```

The exact files may vary slightly depending on the repository version.

## Limitations

- This is a focused take-home prototype, not a production-ready OAuth integration platform.
- Generated guidance depends on the availability and quality of retrieved documentation and AI model responses.
- Effort and approval-time estimates are indicative and may vary by provider, application type, and review requirements.
- Researching a provider does not mean that its OAuth setup or approval process has been completed or tested.
- Some details may remain uncertain and should be verified against official provider documentation before production use.
- The free AI model router may select different models, and generation can occasionally fail.

## Security

- API credentials must remain in the local `.env` file.
- `.env` and local development artifacts should not be committed to Git.
- Use environment variables or a secrets manager for deployed environments.

## Status

Built as an Associate Product Manager take-home assignment to explore how AI-assisted research can help developers make progress on unfamiliar OAuth setup and approval workflows.
