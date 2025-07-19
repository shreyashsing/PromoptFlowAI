# PromptFlow AI Platform

A no-code AI automation platform that enables users to create and run AI-driven workflows through natural language prompts.

## Project Structure

```
promptflow-ai-platform/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── api/               # API routes and endpoints
│   │   ├── connectors/        # Connector implementations
│   │   │   ├── base.py       # Base connector interface
│   │   │   └── registry.py   # Connector registry
│   │   ├── core/             # Core application components
│   │   │   ├── config.py     # Application configuration
│   │   │   └── exceptions.py # Custom exceptions
│   │   ├── models/           # Pydantic data models
│   │   │   ├── base.py       # Base models and enums
│   │   │   ├── connector.py  # Connector-related models
│   │   │   ├── conversation.py # Chat and conversation models
│   │   │   └── execution.py  # Workflow execution models
│   │   ├── services/         # Business logic services
│   │   └── main.py          # FastAPI application entry point
│   ├── requirements.txt      # Python dependencies
│   ├── run.py               # Development server runner
│   └── .env.example         # Environment variables template
├── frontend/                 # Next.js frontend application
│   ├── app/                 # Next.js app directory
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout component
│   │   └── page.tsx         # Home page component
│   ├── lib/                 # Utility libraries
│   │   ├── api.ts          # API client configuration
│   │   └── types.ts        # TypeScript type definitions
│   ├── package.json        # Node.js dependencies
│   ├── next.config.js      # Next.js configuration
│   ├── tailwind.config.js  # Tailwind CSS configuration
│   └── tsconfig.json       # TypeScript configuration
└── .kiro/specs/            # Feature specifications
    └── promptflow-ai-platform/
        ├── requirements.md  # Feature requirements
        ├── design.md       # Technical design
        └── tasks.md        # Implementation tasks
```

## Getting Started

### Backend Setup

#### Option 1: Automated Setup (Recommended)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Run the setup script:
   
   **Windows:**
   ```bash
   setup.bat
   ```
   
   **Unix/Linux/macOS:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Activate the virtual environment:
   
   **Windows:**
   ```bash
   activate.bat
   ```
   
   **Unix/Linux/macOS:**
   ```bash
   source venv/bin/activate
   ```

#### Option 2: Manual Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate.bat
   
   # Unix/Linux/macOS
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

5. Configure your environment variables in `.env`

6. Initialize the database:
   ```bash
   python scripts/init_db.py
   ```

7. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

The backend API will be available at `http://localhost:8000`

#### Testing

Run basic tests to verify setup:
```bash
python tests/test_basic.py
```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`

## Core Interfaces

### BaseConnector

All connectors must inherit from `BaseConnector` and implement:
- `execute()`: Main connector logic
- `validate_params()`: Parameter validation
- `get_auth_requirements()`: Authentication requirements

### Data Models

- **WorkflowPlan**: Complete workflow definition with nodes and edges
- **ConnectorMetadata**: Connector information for RAG retrieval
- **ConversationContext**: Chat session management
- **ExecutionResult**: Workflow execution results

## Environment Variables

Key environment variables to configure:

- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anonymous key
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `SECRET_KEY`: Application secret key

## Next Steps

1. Set up database layer and authentication (Task 2)
2. Implement RAG system for connector retrieval (Task 3)
3. Build base connector framework (Task 4)
4. Create core connectors (Task 5)

See `.kiro/specs/promptflow-ai-platform/tasks.md` for the complete implementation plan.