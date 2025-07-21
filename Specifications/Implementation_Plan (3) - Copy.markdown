# Implementation Plan for PromptFlow AI

## Phase 1: Project Setup (Day 1)
- [ ] Initialize git repository: `git init`, create GitHub repo.
- [ ] Set up Python environment (Python 3.11.4) in `promptflow-ai/` with `backend/` and `frontend/` (optional).
- [ ] Install dependencies: `fastapi`, `langgraph`, `langchain`, `openai`, `python-dotenv`, `pydantic`, `supabase-py`, `uvicorn`, `google-auth`, `requests-oauthlib`.
- [ ] Configure `.env` with Azure_OpenAI, Supabase, SMTP, and OAuth credentials (e.g., Google, HubSpot).
- [ ] Set up Supabase project with `pgvector` and `connectors` table during starting and gradually increase the required tables, functions, etc.
- [ ] Create context files: `PRD.md`, `generate.txt`, `workflow.txt`.

## Phase 2: Connector Development (Day 2–3)
- [ ] For building any connector (e.g., notion, google_sheets, openai, slack, etc) research:
  - Identify required authentication methods (OAuth, API keys) and permissions.
  - List supported operations/actions (e.g., read/write, list, update).
  - Note input/output data structures, rate limits, pagination, error handling.
  - Locate official docs, and any SDKs or client libraries to integrate.

- [ ] Define connector interface in `backend/types/connector.py`.
- [ ] Implement connectors in `backend/connectors/`:
  - `webhook.py`: support for all typical webhook operations
  - `google_sheets.py`: Support all common Google Sheets operations (append, read, update, delete rows and sheets), with OAuth authentication,
  - `openai.py`: Support all major OpenAI operations.
  - `http_request.py`: Implement a generic HTTP connector supporting all methods (GET, POST, PUT, DELETE, PATCH), header/query/body handling, auth types.
  - `gmail.py`: Provide full Gmail integration (send, read, search, list, reply, draft management) with OAuth.
  - `perplexity.py`: Perplexity AI for real-time web-augmented question answering, grounded search, follow-up reasoning, and retrieval-based responses using public sources.
  - `conditional_branch.py`: Implements conditional logic (IF Node).
  - `custom_logic.py`: Executes custom logic via LLM (Function Node).
  - `merge_data.py`: Combines data streams (Merge Node).
  - `error_trigger.py`: Handles workflow errors (Error Trigger Node).
  - `stop_and_error.py`: Stops on conditions (Stop And Error Node).
- [ ] Implement OAuth helper in `backend/utils/oauth.py` to simplify authentication:
  - Generate OAuth links for Google Sheets, HubSpot, etc.
  - Guide users to authorize via chat (e.g., “Click this link to connect Google Sheets: <url>”).
  - Store tokens securely in Supabase.
- [ ] Store connector metadata in Supabase with embeddings via ` text-embedding-3-small` for RAG.
- [ ] Write challenge prompts in `docs/challenge_prompts/` (e.g., “Sync Google Sheets with Notion,” “Notify Slack for Stripe payments”).
  
## Phase 2.5: Function Calling Setup for Azure GPT-4.1 (Day 3)

To enable GPT-4.1 to reason about, select, and call connectors directly via function calling, define each connector as a callable function schema using JSON.

### Tasks:
- [ ] Create a new folder `backend/connectors/schemas/` to store function schemas.
- [ ] For each connector (e.g., `send_email`, `google_sheets`, `webhook_trigger`), create a `.json` file describing the function in OpenAI-compatible format.

### Each function schema must include:
- `name`: The connector name (e.g., `"send_email"`)
- `description`: What the connector does (e.g., `"Sends an email with subject and body to the given address."`)
- `parameters`: A JSON Schema object describing the input fields

### Example: `send_email.json`
```json
{
  "name": "send_email",
  "description": "Sends an email with subject and body to the given address.",
  "parameters": {
    "type": "object",
    "properties": {
      "to": { "type": "string", "description": "Recipient's email address" },
      "subject": { "type": "string", "description": "Subject of the email" },
      "body": { "type": "string", "description": "Email body content" }
    },
    "required": ["to", "subject", "body"]
  }
}

## Phase 3: LangGraph Agent Workflow (Day 4–5)
- [ ] Build conversational LangGraph planner in `backend/agent/planner.py`:
  - Parse prompt and generate a graph of nodes (connectors) and edges.
  - Use OpenAI function-calling with CoT to map prompts to connectors (e.g., “Google Sheets” → `google_sheets`).
  - Retrieve connectors via Supabase vector search (RAG).
  - Implement multi-turn dialogue to:
    - Propose plans with app-specific connectors.
    - Handle modifications (e.g., “Use Slack instead of email”).
    - Request OAuth or minimal inputs (e.g., sheet ID, Slack channel).
    - Example dialogue for app integrations:
      ```
      User: "Add form submissions to Google Sheets and notify Slack daily."
      Agent: "Proposed plan: [schedule_trigger(time='08:00') → receive_webhook(url='your_form_url') → google_sheets(action='append') → slack(channel='your_channel')]. Provide form URL, Sheet ID, and Slack channel."
      User: "URL: https://myform.com, Sheet ID: <sheet_id>, Channel: #general."
      Agent: "I’ll need Google Sheets authorization. Click this link: <oauth_url>. Plan: [schedule_trigger → receive_webhook → google_sheets(sheet='<sheet_id>') → slack(channel='#general')]. Confirm?"
      User: "<Authorizes via link> Use Airtable instead."
      Agent: "Updated plan: [schedule_trigger → receive_webhook → airtable(table='<table_id>') → slack]. Airtable table ID?"
      User: "<table_id>"
      Agent: "Final plan: [schedule_trigger → receive_webhook → airtable → slack]. Confirmed?"
      ```
- [ ] Build LangGraph executor in `backend/agent/executor.py`:
  - Define nodes for each connector, with edges for data flow.
  - Implement trigger logic (scheduling, webhooks).
  - Log errors to `Bug_Tracking.md`.
- [ ] Test with Kiro AI, using challenge prompts to validate app-specific flows.

## Phase 4: API & Testing (Day 6)
- [ ] Create FastAPI server in `backend/main.py` with:
  - `/run-agent`: Initial prompt submission.
  - `/chat-agent`: Conversational planning with app connectors.
    - Example request/response:
      ```json
      POST /chat-agent
      {
        "prompt": "Add form submissions to Google Sheets and notify Slack",
        "form_url": "https://myform.com",
        "sheet_id": "<sheet_id>",
        "slack_channel": "#general",
        "conversation": []
      }
      Response:
      {
        "plan": [
          {"type": "receive_webhook", "params": {"url": "https://myform.com"}},
          {"type": "google_sheets", "params": {"action": "append", "sheet_id": "<sheet_id>"}},
          {"type": "slack", "params": {"channel": "#general", "message": "results.google_sheets.status"}}
        ],
        "status": "proposed",
        "message": "Proposed plan: [receive_webhook → google_sheets → slack]. Confirm or modify?"
      }
      ```
- [ ] Test endpoints with `backend/test.http`.
- [ ] Log errors to `Bug_Tracking.md`.

## Phase 5: Optional Enhancements (Day 7)
- [ ] Add Next.js frontend in `frontend/` for prompt input, chat, and trigger configuration.
- [ ] Add scheduling in `backend/scheduler.py` for `schedule_trigger`.
- [ ] Deploy to Render or Vercel.
- [ ] Update `Project_Structure.md` with deployment details.

## Notes:
- All LLM calls should route through Azure OpenAI.
- generate code, referencing context files.
- Ensure connectors handle OAuth (e.g., Google Sheets, HubSpot) via `oauth.py`.
- Validate flows against `docs/challenge_prompts/` (e.g., “Sync Shopify orders to Airtable”).