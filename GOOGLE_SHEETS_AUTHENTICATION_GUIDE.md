# Google Sheets Authentication Setup Guide

## Overview

The Google Sheets connector requires OAuth2 authentication to access your Google Sheets. This guide explains how to set up and use Google Sheets authentication in your workflow.

## Current Status

✅ **Fixed**: Google Sheets OAuth support has been added to the authentication endpoints
✅ **Working**: OAuth initiation and callback endpoints now support `google_sheets` connector
✅ **Configured**: Uses the same Google OAuth credentials as Gmail (GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET)

## Authentication Requirements

### 1. OAuth2 Credentials Required
- **Access Token**: Required for all Google Sheets API calls
- **Refresh Token**: Used to renew expired access tokens
- **Scopes**: 
  - `https://www.googleapis.com/auth/spreadsheets` (read/write sheets)
  - `https://www.googleapis.com/auth/drive.file` (access specific files)

### 2. Google Cloud Console Setup
Your existing Gmail OAuth credentials work for Google Sheets since they're both Google services.

**Current Configuration:**
```
GMAIL_CLIENT_ID=446020143437-93isfn0k190il2c4d4747s7js2546di1.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=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
```

## How to Authenticate Google Sheets

### Step 1: Initiate OAuth Flow
```bash
curl -X POST "http://localhost:8000/api/v1/auth/oauth/initiate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "connector_name": "google_sheets",
    "redirect_uri": "http://localhost:3000/auth/oauth/callback"
  }'
```

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random-state-string",
  "redirect_uri": "http://localhost:3000/auth/oauth/callback"
}
```

### Step 2: User Authorization
1. User visits the `authorization_url`
2. Google shows consent screen for Sheets permissions
3. User approves access
4. Google redirects to callback with authorization code

### Step 3: Complete OAuth Flow
```bash
curl -X POST "http://localhost:8000/api/v1/auth/oauth/callback" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "AUTHORIZATION_CODE_FROM_CALLBACK",
    "state": "STATE_FROM_STEP_1",
    "connector_name": "google_sheets"
  }'
```

## Workflow Configuration

### Example Workflow with Google Sheets
```json
{
  "name": "Daily AI News to Sheets",
  "nodes": [
    {
      "connector_name": "perplexity_search",
      "parameters": {
        "action": "search",
        "query": "trending AI news today"
      }
    },
    {
      "connector_name": "google_sheets",
      "parameters": {
        "action": "append",
        "spreadsheet_id": "YOUR_ACTUAL_SPREADSHEET_ID",
        "sheet_name": "Sheet1",
        "values": [["{{perplexity_search.result}}"]]
      },
      "dependencies": ["perplexity_search"]
    }
  ]
}
```

### Important: Replace Placeholder Values

❌ **Current Issue**: Your workflow uses placeholder values:
```json
"spreadsheet_id": "YOUR_SPREADSHEET_ID"
```

✅ **Fix**: Use your actual Google Sheets ID:
```json
"spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
```

## How to Get Your Spreadsheet ID

1. Open your Google Sheet in browser
2. Look at the URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
3. Copy the `SPREADSHEET_ID` part
4. Use it in your workflow parameters

## Testing Authentication

Run the test script to verify setup:
```bash
cd backend
python test_google_sheets_auth.py
```

## Common Issues & Solutions

### Issue 1: "Google Sheets access token not found"
**Cause**: User hasn't completed OAuth flow for Google Sheets
**Solution**: Complete the OAuth authentication steps above

### Issue 2: "Failed to append data: 403 Forbidden"
**Cause**: Insufficient permissions or wrong spreadsheet ID
**Solution**: 
- Verify spreadsheet ID is correct
- Ensure user has edit access to the sheet
- Check OAuth scopes include spreadsheets permission

### Issue 3: "Spreadsheet not found"
**Cause**: Invalid spreadsheet ID or no access
**Solution**:
- Double-check the spreadsheet ID from URL
- Ensure the sheet is shared with the authenticated user
- Make sure the sheet exists and isn't deleted

### Issue 4: Placeholder values in workflow
**Cause**: Using `"YOUR_SPREADSHEET_ID"` instead of actual ID
**Solution**: Replace with real spreadsheet ID from your Google Sheet URL

## Frontend Integration

The frontend should handle the OAuth flow:

1. **Detect Missing Auth**: Check if user has Google Sheets tokens
2. **Show Auth Button**: Display "Connect Google Sheets" button
3. **Handle OAuth Flow**: Open popup/redirect for OAuth
4. **Store Tokens**: Backend automatically stores tokens after callback
5. **Enable Workflow**: Allow workflow execution once authenticated

## Security Notes

- Tokens are encrypted and stored securely in database
- Refresh tokens allow automatic token renewal
- OAuth state parameter prevents CSRF attacks
- Tokens are scoped to specific Google services

## Next Steps

1. **Complete OAuth Flow**: Authenticate your Google Sheets access
2. **Update Workflow**: Replace placeholder spreadsheet ID with real one
3. **Test Workflow**: Run the workflow to verify it works
4. **Frontend Integration**: Add OAuth flow to the UI

The Google Sheets connector is now properly configured for OAuth authentication!