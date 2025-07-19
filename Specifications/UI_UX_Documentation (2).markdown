# UI/UX Documentation for PromptFlow AI

## Overview:
The UI for PromptFlow AI is minimal for the MVP, focusing on a single-page interface for non-technical users to submit prompts, engage in conversational planning, and view results. It should be intuitive, clean, and aligned with Tailwind CSS for styling.

## Key Screens:
### 1. Prompt Input and Chat Interface
- **Purpose**: Allow users to enter a natural language prompt and interact with the AI agent to refine the workflow plan.
- **Components**:
  - **Text Input**: Large text field for initial prompt (e.g., "Summarize AI blogs and email me").
  - **Chat Interface**: Chatbot-like UI for multi-turn dialogue to confirm or modify the plan (e.g., switch APIs, add steps).
  - **Optional Fields**: Email input, API key input (with toggle to hide/show).
  - **Submit Button**: Triggers the `/chat-agent` API call to start or continue planning.
  - **Result Display**: Shows JSON or formatted output of the finalized plan and execution results.
- **Layout**:
  - Centered form with Tailwind’s `flex`, `max-w-lg`, and `p-4`.
  - Chat interface with scrollable message history, using `bg-gray-100` for user messages and `bg-blue-100` for agent responses.
  - Clean typography with `text-lg` for inputs and chat, `text-red-500` for errors.
- **Interaction Flow**:
  - User enters prompt → Submits → Agent proposes plan → User modifies via chat (e.g., “Use Perplexity instead”) → Agent updates plan → User confirms → Plan is saved and scheduled.
  - Error messages shown in red with retry options.

### 2. Optional Workflow Visualization (Post-MVP)
- **Purpose**: Display the LangGraph workflow (e.g., nodes: search → summarize → email).
- **Components**:
  - Flowchart or list view of nodes with status (e.g., “Planned”, “Scheduled”).
  - Use a library like react-flow to render LangGraph nodes and edges, showing status (e.g., “Running”, “Failed”).
  - Tailwind’s `grid` or `flex` for layout.
- **Interaction Flow**:
  - Auto-updates as the plan is refined, with clickable nodes to view details.
  - When the user clicks on a node, a side panel or modal should appear, allowing them to view and input any required fields (e.g., API keys, webhook URLs, email addresses, etc) that are missing or customizable for that specific connector.

## Accessibility:
- Use ARIA labels for inputs and chat (`aria-label="Prompt input"`, `aria-label="Chat message"`).
- Ensure high contrast (e.g., `text-gray-900` on `bg-white`).
- Support keyboard navigation (`tabindex` for buttons and chat input).

## Notes:
- Keep UI minimal for MVP, focusing on conversational planning and result display.
- generate Next.js components, referencing this file.
- Validate design against `PRD.md` for non-technical usability.