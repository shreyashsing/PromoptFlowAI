# Project Structure for PromptFlow AI

## Overview:
The project uses a monorepo structure for modularity and scalability, with clear separation of backend, frontend (optional), and context files. LangGraph orchestrates workflows, ensuring stateful, graph-based execution.

## Folder Structure:
```
promptflow-ai/
├── backend/
│   ├── connectors/         # Modular connector modules
│   │   ├── search_blogs.py
│   │   ├── summarize_text.py
│   │   ├── send_email.py
│   ├── agent/             # LangGraph planner and executor
│   │   ├── planner.py
│   │   ├── executor.py
│   ├── utils/             # Helper functions (e.g., Supabase client)
│   ├── types/             # Pydantic models
│   │   ├── connector.py
│   ├── main.py            # FastAPI server
│   ├── test.http          # REST Client tests
│   └── .env               # Environment variables
├── frontend/              # Optional Next.js UI
│   ├── pages/
│   ├── components/
│   ├── public/
│   └── styles/
├── context/               # Context Engineering files
│   ├── PRD.md
│   ├── generate.txt
│   ├── workflow.txt
│   ├── Implementation_Plan.md
│   ├── UI_UX_Documentation.md
│   ├── Project_Structure.md
│   └── Bug_Tracking.md
├── docs/                  # Additional docs and challenge prompts
│   └── challenge_prompts/
└── requirements.txt
```

## Reasoning:
- **Backend**: Separates concerns (connectors, agent logic, utilities) for modularity, with LangGraph as the orchestration layer.
- **Frontend**: Optional for MVP, using Next.js for rapid UI development.
- **Context**: Stores specifications as versionable Markdown files, per Context Engineering principles.
- **Docs**: Includes challenge prompts for testing connectors, ensuring alignment with intent.

## Notes:
- create files, referencing this structure.
- Update this file if new folders or files are added during development.
- Ensure `.env` is gitignored for security.