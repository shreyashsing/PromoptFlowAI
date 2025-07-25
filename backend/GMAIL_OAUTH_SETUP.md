# Gmail OAuth Setup Guide

## Overview
This guide helps you set up Gmail OAuth credentials for the PromptFlow AI platform.

## 🎯 Prerequisites
- Google Cloud Platform account
- Google Cloud Console access
- Backend `.env` file ready for editing

## 📋 Step-by-Step Setup

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

### 2. Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type (for testing)
3. Fill in required fields:
   - **App name**: `PromptFlow AI`
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Add scopes (click "Add or Remove Scopes"):
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.labels`
5. Add test users (your Gmail account)

### 3. Create OAuth Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client ID"
3. Choose "Web application"
4. Configure:
   - **Name**: `PromptFlow AI - Gmail Connector`
   - **Authorized JavaScript origins**: 
     - `http://localhost:3000`
     - `http://localhost:8000`
   - **Authorized redirect URIs**:
     - `http://localhost:3000/auth/oauth/callback`
5. Click "Create"
6. **IMPORTANT**: Copy the Client ID and Client Secret

### 4. Configure Backend Environment
Add these variables to your `backend/.env` file:

```env
# Gmail OAuth Configuration
GMAIL_CLIENT_ID=your_client_id_here
GMAIL_CLIENT_SECRET=your_client_secret_here
```

**Example:**
```env
GMAIL_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz
```

### 5. Test the Configuration
1. Restart your backend server
2. Go to the frontend workflow builder
3. Add a Gmail connector node
4. Click "Configure" > "Authentication"
5. You should be redirected to Google OAuth screen

## 🚨 Troubleshooting

### "Gmail OAuth not configured" Error
- Check that `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` are set in `.env`
- Restart the backend server after adding environment variables

### "redirect_uri_mismatch" Error
- Verify the redirect URI in Google Console matches exactly:
  - `http://localhost:3000/auth/oauth/callback`
- Check for trailing slashes, http vs https, port numbers

### "access_denied" Error
- Make sure your Gmail account is added as a test user
- Ensure Gmail API is enabled in Google Cloud Console

### "Invalid state parameter" Error
- This should be fixed with the latest code changes
- Clear browser localStorage and try again

## 🔐 Security Notes

### For Development
- Current setup uses `http://localhost` which is fine for testing
- OAuth consent screen in "Testing" mode limits to added test users

### For Production
- Use HTTPS domains in redirect URIs
- Verify your app in Google Console for public access
- Use environment-specific credentials
- Store secrets securely (not in code)

## 📞 Support
If you encounter issues:
1. Check browser console for error messages
2. Check backend logs for detailed error information
3. Verify all environment variables are set correctly
4. Ensure Google Cloud APIs are enabled

## ✅ Verification Checklist
- [ ] Google Cloud project created
- [ ] Gmail API enabled
- [ ] OAuth consent screen configured
- [ ] OAuth credentials created
- [ ] Redirect URIs configured correctly
- [ ] Environment variables set in backend
- [ ] Backend server restarted
- [ ] Test user added to OAuth consent screen
- [ ] Gmail account has API access enabled