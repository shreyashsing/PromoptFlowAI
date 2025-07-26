# Gmail Authentication Guide

## Issue
Your workflow is failing with a Gmail authentication error:
```
Gmail operation failed: Failed to send email: {"error": {"code": 401,"message": "Request had invalid authentication credentials. Expected OAuth 2 access token, login cookie or other valid authentication credential."}}
```

## Solution
The Gmail connector needs to be authenticated with OAuth before it can send emails. Here's how to fix it:

### Step 1: Access Workflow Configuration
1. Go to your workflow in the PromptFlow AI dashboard
2. Find the Gmail connector node in your workflow
3. Click on the Gmail connector node to open its configuration

### Step 2: Authenticate Gmail Connector
1. In the connector configuration modal, you'll see an "Authentication" tab
2. Click on the "Authentication" tab
3. You'll see a status showing "Authentication Required"
4. Click the "Authenticate with Gmail" button
5. This will redirect you to Google's OAuth consent screen

### Step 3: Grant Permissions
1. Sign in to your Google account (if not already signed in)
2. Review the permissions requested:
   - Read your Gmail messages
   - Send emails on your behalf
   - Modify your Gmail account
   - Manage Gmail labels
3. Click "Allow" to grant these permissions

### Step 4: Complete Authentication
1. You'll be redirected back to PromptFlow AI
2. You should see "Successfully authenticated" status
3. Close the configuration modal

### Step 5: Re-run Workflow
1. Now that Gmail is authenticated, try running your workflow again
2. The Gmail connector should now be able to send emails successfully

## Important Notes
- You need to authenticate each connector that requires OAuth (like Gmail) before using it in workflows
- The authentication is tied to your Google account, so make sure you're signed in with the correct account
- If authentication fails, try clearing your browser cache and cookies, then repeat the process

## Troubleshooting
If you continue to have issues:
1. Make sure you're signed in to PromptFlow AI
2. Check that you have the correct permissions in your Google account
3. Try refreshing the page and re-authenticating
4. Contact support if the issue persists

## Alternative: Use Perplexity for Blog Search
Note: Your original request was to find Google blogs using Perplexity, but the workflow created used Gmail to search for emails instead. Consider modifying your workflow to:
1. Use **Perplexity Search** connector to find recent Google blog posts
2. Use **Text Summarizer** to create a combined summary
3. Use **Gmail** (after authentication) to send the summary

This would be more appropriate for finding web content rather than searching emails.