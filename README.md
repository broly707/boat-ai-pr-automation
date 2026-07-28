# boat-ai-pr-automation

AI Code Reviewer — automatically reviews Pull Requests using Groq LLM and posts feedback as a GitHub comment.

## Requirements

- Python 3.11+
- Git
- Groq API Key
- GitHub App (with webhook configured)

## Install

```bash
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```
GROQ_API_KEY=
GITHUB_WEBHOOK_SECRET=
GITHUB_APP_ID=
GITHUB_INSTALLATION_ID=
GITHUB_APP_PRIVATE_KEY=
```

## Run Locally

```bash
uvicorn main:app --reload
```

## Deploy

The app is configured for Render via `Procfile`. Push to `main` to trigger auto-deploy.
