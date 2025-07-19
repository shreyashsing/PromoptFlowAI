# Project Requirements Document (PRD)

## Project Name: PromptFlow AI

## Purpose:
PromptFlow AI is a no-code platform that enables non-technical users to create and run AI-driven automation workflows by describing tasks in natural language (e.g., "Find top 5 AI blogs, summarize them, and email me weekly"). The system uses a conversational AI agent to interactively plan workflows, retrieve connectors via Retrieval-Augmented Generation (RAG), generate a graph-based workflow using LangGraph, execute it with minimal user input (e.g., API keys or URLs, Oauth), and support dynamic modifications during planning.

## Target Users:
- Non-technical users: Marketers, small business owners, educators
- Developers: For rapid prototyping of automation workflows
- Businesses: Seeking simple automation without coding expertise

## Core Features:
- **Prompt Input**: Users describe tasks in plain English via a text input, API, or conversational chat interface.
- **Conversational Planning**: AI agent interactively plans workflows, confirming steps, handling modifications (e.g., switching APIs, adding steps), and finalizing with user approval.
- **Auto-Plan**: AI parses prompts, retrieves connectors via RAG (using Supabase + pgvector), and generates a LangGraph workflow with nodes and edges.
- **Execution**: Runs the LangGraph workflow deterministically, chaining connector outputs, with user-defined triggers (e.g., schedule, webhook).
- **Minimal Configuration**: Users provide only necessary inputs (e.g., API keys, email addresses, URLs) by clicking on the node in UI.
- **Connector Library**: Modular tools for data sourcing (e.g., web search), AI utilities (e.g., summarization), and output (e.g., email).

## Optional Features:
- **Scheduling**: Run workflows on a schedule (e.g., weekly blog summaries).
- **Webhook Triggers**: Start workflows based on external events.
- **Visualization**: Display LangGraph workflow steps and results in a simple UI using a library like react-flow.
- **User Authentication**: Secure user accounts for saving workflows.

## Non-Functional Requirements:
- **Scalability**: Handle 1000+ concurrent users.
- **Performance**: Generate plans in <5 seconds, execute workflows in <30 seconds.
- **Security**: Encrypt API keys and sensitive user inputs.
- **Usability**: Intuitive for non-technical users, requiring no coding knowledge.

## Preferred Tech Stack:
- **Frontend**: Next.js + Tailwind CSS (optional for MVP)
- **Backend**: Python + FastAPI (for LangGraph integration)
- **LLM**: Azure OpenAI (GPT-4o deployment) for conversational planning and function calling.
- **Database**: Supabase + pgvector (for RAG and connector metadata)
- **Auth**: Supabase Auth
- **Orchestration**: LangGraph (for graph-based workflow execution)
- **Embeddings**: OpenAI  text-embedding-3-small (for RAG-based connector retrieval)