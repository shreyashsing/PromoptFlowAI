# PromptFlow AI Platform

A no-code AI automation platform that enables users to create complex workflows through natural language conversations.

## 🚀 Features

- **Conversational Workflow Builder**: Create workflows by describing what you want in natural language
- **Smart Connector Recommendations**: AI-powered RAG system suggests the best connectors for your needs
- **Visual Workflow Editor**: Drag-and-drop interface for fine-tuning workflows
- **Secure Authentication**: Multi-layered security with encrypted token storage
- **Real-time Execution**: Monitor and manage workflow executions in real-time
- **Vector-based Search**: Semantic similarity search using pgvector and Azure OpenAI embeddings

## 🏗️ Architecture

### Backend (FastAPI)
- **RAG System**: Retrieval-Augmented Generation for intelligent connector recommendations
- **Vector Database**: pgvector for semantic similarity search
- **Authentication**: Secure token-based auth with encryption
- **Database**: Supabase (PostgreSQL) with real-time capabilities
- **AI Integration**: Azure OpenAI for embeddings and completions

### Frontend (Next.js)
- **Modern React**: Next.js 14 with App Router
- **TypeScript**: Full type safety
- **UI Components**: Shadcn/ui with Tailwind CSS
- **Real-time Updates**: Supabase real-time subscriptions

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend API** | FastAPI, Python 3.8+ |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **AI Services** | Azure OpenAI (GPT-4, text-embedding-3-small) |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS |
| **Authentication** | Supabase Auth + Custom JWT |
| **Vector Search** | pgvector with cosine similarity |
| **Testing** | pytest, pytest-asyncio |

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- Supabase account
- Azure OpenAI access (for RAG system)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/promptflow-ai.git
cd promptflow-ai
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 3. Configure Environment Variables
Edit `backend/.env`:
```env
# Database (Required)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# Azure OpenAI (Required for RAG system)
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_OPENAI_API_KEY=your_azure_openai_api_key

# Security
SECRET_KEY=your_secret_key
```

### 4. Initialize Database
```bash
# Set up database schema
python scripts/init_db.py

# Populate with sample connectors (requires Azure OpenAI)
python scripts/setup_rag_database.py
```

### 5. Start Backend Server
```bash
uvicorn app.main:app --reload
```

### 6. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 7. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📁 Project Structure

```
promptflow-ai/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   └── rag.py         # RAG system endpoints
│   │   ├── core/              # Core functionality
│   │   │   ├── auth.py        # Authentication logic
│   │   │   ├── database.py    # Database connection
│   │   │   └── exceptions.py  # Custom exceptions
│   │   ├── models/            # Pydantic models
│   │   ├── services/          # Business logic
│   │   │   └── rag.py         # RAG system implementation
│   │   ├── data/              # Sample data
│   │   └── connectors/        # Connector implementations
│   ├── scripts/               # Setup and utility scripts
│   ├── tests/                 # Test suite
│   └── requirements.txt       # Python dependencies
├── frontend/                  # Next.js frontend
│   ├── app/                   # App Router pages
│   ├── components/            # React components
│   ├── lib/                   # Utilities and types
│   └── package.json           # Node.js dependencies
├── .kiro/                     # Kiro IDE specifications
│   └── specs/                 # Feature specifications
└── docs/                      # Documentation
```

## 🧠 RAG System

The platform includes a sophisticated RAG (Retrieval-Augmented Generation) system for intelligent connector recommendations:

### Features
- **Semantic Search**: Uses Azure OpenAI embeddings for understanding user intent
- **Vector Storage**: pgvector extension for fast similarity search
- **Smart Ranking**: Combines semantic similarity with usage statistics
- **Category Filtering**: Filter connectors by category for precision
- **Performance Optimized**: Sub-second query response times

### API Endpoints
- `GET /api/v1/rag/search?query=send email` - Search connectors
- `GET /api/v1/rag/connectors/popular` - Get popular connectors
- `GET /api/v1/rag/categories` - List all categories
- `GET /api/v1/rag/health` - System health check

## 🧪 Testing

### Backend Tests
```bash
cd backend

# Run all tests
python -m pytest

# Run specific test files
python -m pytest tests/test_rag.py -v

# Run performance tests
python -m pytest tests/test_rag_performance.py -v

# Test RAG system structure (no external dependencies)
python test_rag_simple.py
```

### API Testing
```bash
# Test RAG API endpoints (requires running server)
python test_rag_api.py
```

## 🔧 Development

### Adding New Connectors
1. Define connector metadata in `backend/app/data/sample_connectors.py`
2. Implement connector logic in `backend/app/connectors/`
3. Update embeddings: `POST /api/v1/rag/admin/update-embeddings`

### Database Migrations
```bash
# Apply schema changes
python scripts/init_db.py

# Update connector embeddings
python scripts/setup_rag_database.py
```

## 🚀 Deployment

### Backend (FastAPI)
- Deploy to any Python-compatible platform (Heroku, Railway, etc.)
- Ensure environment variables are configured
- Run database initialization scripts

### Frontend (Next.js)
- Deploy to Vercel, Netlify, or similar
- Configure environment variables for API endpoints

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow Python PEP 8 for backend code
- Use TypeScript for all frontend code
- Write tests for new features
- Update documentation as needed

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` folder
- **Issues**: Create a GitHub issue
- **Discussions**: Use GitHub Discussions for questions

## 🎯 Roadmap

- [x] Authentication system with secure token storage
- [x] RAG system for intelligent connector recommendations
- [ ] Visual workflow editor
- [ ] More connector integrations
- [ ] Workflow templates
- [ ] Team collaboration features
- [ ] Advanced scheduling options
- [ ] Workflow analytics dashboard

---

**Note**: The RAG system requires Azure OpenAI credentials to function fully. You can develop other parts of the application and add the AI credentials later before implementing task 4.