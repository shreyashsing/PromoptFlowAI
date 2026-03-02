# PromptFlow AI

**PromptFlow AI** is an AI-first automation platform that enables anyone—"even a 10-year-old who knows English"—to create powerful, custom automations ("mini apps") using plain natural language. The system leverages a True ReAct-style intelligent agent for planning and execution, a modular connector architecture for interacting with external services, and a clean web interface for chat-driven workflow creation and app management.

---

## 🚀 Key Features

- **Natural language automation creation** – Describe what you need and the AI builds a workflow.
- **True ReAct Agent** – Sophisticated planning and step-by-step execution with real‑time narration.
- **Modular connectors** – Easily integrate with services like Gmail, Notion, Google Drive, Perplexity, and more.
- **Authentication management** – Handles user credentials and authorization for external APIs.
- **Mini‑apps dashboard** – Saved automations that you can run with custom inputs.
- **Streaming UI** – Chat interface shows planning/execution progress using Server‑Sent Events.
- **Database persistence** – Supabase backend stores mini‑apps and user data.

---

## 📁 Repository Structure

```
promptflow-ai/
├── backend/                # FastAPI server and core logic
│   ├── app/
│   │   ├── api/            # API route definitions
│   │   ├── connectors/     # Connector implementations
│   │   ├── services/       # Agent, auth, workflows, etc.
│   │   ├── core/           # Utilities (database, config, auth)
│   │   ├── models/         # Pydantic data models
│   │   └── main.py         # Entry point
│   ├── requirements.txt    # Python dependencies
│   ├── start_server.py     # Helper script to launch
│   └── .env                # Environment variables (ignored)
├── frontend/               # Next.js React UI (chat + dashboard)
│   ├── components/         # UI components (AIAgentChat, MiniAppsDashboard)
│   └── pages/              # Next.js pages
├── Specifications/         # Context engineering docs and PRD
└── Code/                   # Sandbox and validation utilities
```

Refer to `Specifications/Project_Structure (1).markdown` for more details.

---

## ⚙️ Getting Started

1. **Clone the repo**

   ```bash
   git clone https://github.com/shreyashsing/PromoptFlowAI.git
   cd "PromptFlow AI"
   ```

2. **Backend setup**

   - Create a Python virtual environment and install dependencies:
     ```bash
     cd backend
     python -m venv venv
     venv\Scripts\activate        # Windows
     pip install -r requirements.txt
     ```

   - Configure environment variables in `.env` (Supabase keys, OpenAI credentials, Gmail OAuth, etc.).

   - Initialize the database (run migrations or use provided scripts in `backend/scripts`).

   - Start the FastAPI server:
     ```bash
     python main.py
     ```

3. **Frontend setup (optional)**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   The UI runs on [http://localhost:3000](http://localhost:3000).

4. **Authentication**

   - Sign up/log in via Supabase or configure OAuth as needed.
   - Authenticate connectors (e.g., Gmail, Notion) through the UI when prompted.

5. **Create your first automation**

   - Use the chat interface to describe an automation (e.g., "create a blog writer").
   - Follow on‑screen prompts and authenticate connectors if required.
   - The generated mini‑app will appear in the dashboard ready to run.

---

## 🧠 Architecture Highlights

- **True ReAct Agent (`backend/app/services/true_react_agent.py`)**: Core AI agent leveraging LLMs and a planning/execution cycle. It communicates with a dynamic tool registry mapping to connectors.
- **Connector Registry**: Modular system under `backend/app/connectors/` where each service defines schema, auth requirements, and execution logic.
- **AuthContextManager**: Manages user credentials and connector tokens, prompting for authentication when necessary.
- **Streaming API**: Endpoints emit progress steps using `async_generator`s and FASTAPI `StreamingResponse` for live feedback.
- **MiniApp Model**: Defines persisted automations with inputs, workflow config, and UI metadata.
- **Frontend**: React components (`AIAgentChat`, `MiniAppsDashboard`) consume SSE events and display them in a user-friendly chat-style format.

---

## 📜 Additional Documentation

- **Specifications/** – contains PRD, UI/UX docs, bug tracking, and planning notes.
- **Frontend Markdown files** – various design fixes and connector integration guides.
- **Scripts folder** – utilities for database initialization and migrations.

---

## 🛠️ Development Notes

- Use `ai_workflow_agent.py` as the bridge between the chat front end and the True ReAct agent.
- Connectors must implement `get_auth_requirements`, `_define_schema`, and `execute` methods.
- Ensure any new connectors are registered in `app/connectors/registry.py`.
- Watch for session management across async generators when adding new features.
- Keep `.env` secrets out of version control.

---

## 🧩 Contributors & License

This project was bootstrapped as part of a Prompt Engineering initiative. Contributions are welcome—please open a pull request.

Licensed under the [MIT License](LICENSE).

---

Happy automating! 🎉
