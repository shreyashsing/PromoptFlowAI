# Database Setup Guide

This guide explains how to set up and configure the database layer for PromptFlow AI.

## Prerequisites

1. **Supabase Project**: Create a new project at [supabase.com](https://supabase.com)
2. **Python Environment**: Python 3.8+ installed on your system

## Virtual Environment Setup (Recommended)

It's highly recommended to use a virtual environment to avoid dependency conflicts.

### Option 1: Automated Setup

**Windows:**
```bash
cd backend
setup.bat
```

**Unix/Linux/macOS:**
```bash
cd backend
chmod +x setup.sh
./setup.sh
```

**Cross-platform Python script:**
```bash
cd backend
python setup_env.py
```

### Option 2: Manual Setup

**Create virtual environment:**
```bash
cd backend
python -m venv venv
```

**Activate virtual environment:**

Windows:
```bash
venv\Scripts\activate.bat
```

Unix/Linux/macOS:
```bash
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

## Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your Supabase credentials:
   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-anon-key-here
   SECRET_KEY=your-secret-key-for-encryption
   ```

   **Important**: 
   - Get your Supabase URL and anon key from your Supabase project dashboard
   - Generate a strong SECRET_KEY for encryption (32+ characters recommended)

## Database Schema Setup

### Option 1: Automatic Setup (Recommended)

Run the initialization script:
```bash
cd backend
python scripts/init_db.py
```

This script will:
- Create all required tables and indexes
- Set up Row Level Security (RLS) policies
- Insert initial connector metadata
- Configure database extensions (uuid-ossp, vector)

### Option 2: Manual Setup

1. Open your Supabase SQL editor
2. Copy and paste the contents of `backend/app/database/schema.sql`
3. Execute the SQL to create the schema

## Database Structure

### Core Tables

1. **users** - User profiles (extends Supabase auth.users)
2. **workflows** - Workflow definitions and metadata
3. **connectors** - Available connector metadata with embeddings
4. **auth_tokens** - Encrypted authentication tokens for connectors
5. **workflow_executions** - Execution history and logs
6. **conversations** - Chat history for workflow planning

### Security Features

- **Row Level Security (RLS)**: Users can only access their own data
- **Token Encryption**: All sensitive tokens are encrypted before storage
- **Automatic Timestamps**: Created/updated timestamps are managed automatically

## Authentication System

### Features

- **Supabase Auth Integration**: Built on Supabase's authentication system
- **JWT Token Verification**: Secure token-based authentication
- **User Profile Management**: Automatic profile creation and updates
- **Token Storage**: Secure storage of third-party API tokens

### API Endpoints

All authentication endpoints are available under `/api/v1/auth/`:

- `POST /auth/signup` - Register new user
- `POST /auth/signin` - Sign in existing user
- `POST /auth/refresh` - Refresh access token
- `POST /auth/signout` - Sign out user
- `GET /auth/me` - Get current user profile
- `PUT /auth/me` - Update user profile
- `POST /auth/tokens` - Store connector authentication token
- `GET /auth/tokens` - List user's stored tokens
- `DELETE /auth/tokens/{connector}/{type}` - Delete stored token

## Token Encryption

### How It Works

1. **Encryption**: Uses Fernet (AES 128) with PBKDF2 key derivation
2. **Storage**: Tokens are encrypted before database storage
3. **Retrieval**: Tokens are decrypted when retrieved for use
4. **Security**: Only the user who stored a token can decrypt it

### Supported Token Types

- `api_key` - Simple API keys
- `oauth2` - OAuth 2.0 access/refresh tokens
- `basic` - Basic authentication credentials

## Testing

### Run Authentication Tests

```bash
cd backend
python tests/test_auth.py
```

### Run Full Test Suite (requires pytest)

```bash
pip install pytest pytest-asyncio
pytest tests/test_auth.py -v
```

## Usage Examples

### Starting the Application

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### User Registration

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password",
    "full_name": "John Doe"
  }'
```

### Storing a Connector Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/tokens" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "connector_name": "gmail",
    "token_type": "oauth2",
    "token_data": {
      "access_token": "ya29.a0...",
      "refresh_token": "1//04...",
      "expires_in": 3600
    }
  }'
```

## Troubleshooting

### Common Issues

1. **Connection Failed**: Check SUPABASE_URL and SUPABASE_KEY in .env
2. **Schema Errors**: Ensure you have proper permissions in Supabase
3. **Encryption Errors**: Verify SECRET_KEY is set and sufficiently long
4. **RLS Errors**: Make sure you're using the correct JWT token

### Logs

The application logs important events:
- Database connection status
- Authentication attempts
- Token operations
- Error details

Check the console output when running the application for debugging information.

## Security Best Practices

1. **Environment Variables**: Never commit .env files to version control
2. **Secret Key**: Use a strong, randomly generated SECRET_KEY
3. **Token Expiry**: Set appropriate expiration times for stored tokens
4. **HTTPS**: Always use HTTPS in production
5. **Regular Cleanup**: Implement token cleanup for expired credentials

## Next Steps

After setting up the database layer:

1. Test the authentication endpoints
2. Store some connector tokens
3. Proceed to implement the RAG system (Task 3)
4. Build the connector framework (Task 4)

For questions or issues, refer to the main project documentation or create an issue in the project repository.