# OAuth 404 Debug Guide

## Issue
When clicking "Reconnect Account" in the Gmail connector configuration, you're getting a 404 page instead of being redirected to Google OAuth.

## Debugging Steps

### Step 1: Check Backend Server
Make sure your backend server is running:
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Verify Endpoint Exists
Test the OAuth endpoint directly:
```bash
curl -X POST http://localhost:8000/api/v1/auth/oauth/initiate \
  -H "Content-Type: application/json" \
  -d '{"connector_name": "gmail_connector"}'
```

Expected response: 401 Unauthorized (this is normal without proper auth token)

### Step 3: Check Browser Network Tab
1. Open browser Developer Tools (F12)
2. Go to Network tab
3. Click "Reconnect Account" button
4. Look for the request to `/api/v1/auth/oauth/initiate`
5. Check if it's:
   - Getting a 404 (endpoint not found)
   - Getting a CORS error
   - Getting a different error

### Step 4: Check Frontend URL
The frontend should be calling:
```
http://localhost:8000/api/v1/auth/oauth/initiate
```

### Step 5: Common Issues

**Issue 1: Backend not running**
- Solution: Start the backend server

**Issue 2: Wrong port**
- Frontend expects backend on port 8000
- Check if backend is running on different port

**Issue 3: CORS issues**
- Check browser console for CORS errors
- Backend allows localhost:3000 and localhost:8000

**Issue 4: Authentication issues**
- Make sure you're logged into the frontend
- Check if Supabase session is valid

### Step 6: Manual Test
Try this in browser console while on the app:
```javascript
// Check if you have a valid session
const { data: { session } } = await supabase.auth.getSession()
console.log('Session:', session)

// Test the OAuth endpoint
fetch('http://localhost:8000/api/v1/auth/oauth/initiate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`
  },
  body: JSON.stringify({
    connector_name: 'gmail_connector',
    redirect_uri: window.location.origin + '/auth/oauth/callback'
  })
})
.then(response => {
  console.log('Status:', response.status)
  return response.json()
})
.then(data => console.log('Response:', data))
.catch(error => console.error('Error:', error))
```

## Quick Fix Attempts

### Fix 1: Restart Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Fix 2: Check Frontend Environment
Make sure frontend is running on localhost:3000:
```bash
cd frontend
npm run dev
```

### Fix 3: Clear Browser Cache
- Clear browser cache and cookies
- Try in incognito/private mode

## Expected Flow
1. Click "Reconnect Account"
2. Frontend calls `/api/v1/auth/oauth/initiate`
3. Backend returns Google OAuth URL
4. Browser redirects to Google OAuth
5. User grants permissions
6. Google redirects back to `/auth/oauth/callback`
7. Frontend processes the callback

If you're getting 404 at step 2, the backend endpoint isn't accessible.