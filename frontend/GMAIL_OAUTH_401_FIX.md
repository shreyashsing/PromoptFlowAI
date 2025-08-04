# Gmail OAuth 401 Unauthorized Error Fix

## 🐛 **Issue Identified**

When trying to authenticate Gmail connector, users were getting a **401 Unauthorized** error:

```
Failed to load resource: the server responded with a status of 401 (Unauthorized)
OAuth error: Error: Failed to initiate OAuth
```

---

## 🔍 **Root Cause Analysis**

The Gmail connector's OAuth implementation was missing critical authentication components that the working Google Drive connector has:

### **❌ Gmail Modal Issues:**
1. **Missing Authorization Header** - No Bearer token sent to backend
2. **Wrong API Endpoint** - Using `/api/auth/oauth/initiate` instead of `/api/v1/auth/oauth/initiate`
3. **Missing Base URL** - Not using proper API base URL
4. **Missing Redirect URI** - No redirect URI specified
5. **Incomplete Session Usage** - Only using `user` from `useAuth()`, not `session`

### **✅ Google Drive Modal (Working):**
1. **Authorization Header** - `Authorization: Bearer ${session?.access_token}`
2. **Correct API Endpoint** - `/api/v1/auth/oauth/initiate`
3. **Full Base URL** - `${baseUrl}/api/v1/auth/oauth/initiate`
4. **Redirect URI** - `redirect_uri: 'http://localhost:3000/auth/oauth/callback'`
5. **Complete Session Usage** - Uses both `user` and `session`

---

## ✅ **Fix Applied**

### **1. Fixed Auth Context Usage**
```typescript
// Before
const { user } = useAuth();

// After
const { user, session } = useAuth();
```

### **2. Fixed OAuth Initiation Function**
```typescript
const handleGoogleOAuth = async () => {
    try {
        setIsLoading(true);
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/api/v1/auth/oauth/initiate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session?.access_token}`, // ← ADDED
            },
            body: JSON.stringify({
                connector_name: 'gmail_connector',
                redirect_uri: 'http://localhost:3000/auth/oauth/callback' // ← ADDED
            })
        });

        if (!response.ok) {
            throw new Error(`OAuth initiate failed: ${response.status}`);
        }

        const oauthData = await response.json();

        // Popup-based OAuth flow (same as Google Drive)
        localStorage.setItem('oauth_state', oauthData.state);
        localStorage.setItem('oauth_connector', 'gmail_connector');

        const popup = window.open(oauthData.authorization_url, 'oauth-popup', 'width=600,height=600');

        const checkClosed = setInterval(() => {
            if (popup?.closed) {
                clearInterval(checkClosed);
                // Check if OAuth was successful
                const tokens = localStorage.getItem('oauth_tokens');
                if (tokens) {
                    const parsedTokens = JSON.parse(tokens);
                    setConfig(prev => ({
                        ...prev,
                        auth_config: {
                            ...prev.auth_config,
                            access_token: parsedTokens.access_token,
                            refresh_token: parsedTokens.refresh_token
                        }
                    }));
                    setAuthStatus('authenticated');
                    localStorage.removeItem('oauth_tokens');
                }
                setIsLoading(false);
            }
        }, 1000);

    } catch (error) {
        console.error('OAuth error:', error);
        setAuthStatus('error');
        setIsLoading(false);
    }
};
```

### **3. Fixed Test Connection Function**
```typescript
const handleTestConnection = async () => {
    // ... validation code ...
    
    setIsLoading(true);
    try {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/api/v1/connectors/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session?.access_token}`, // ← ADDED
            },
            body: JSON.stringify({
                connector_name: 'gmail_connector',
                auth_tokens: config.auth_config
            })
        });
        
        // ... rest of function
    } catch (error) {
        // ... error handling
    }
};
```

---

## 🎯 **Key Changes Made**

1. **✅ Added Authorization Header** - Now sends Bearer token for authentication
2. **✅ Fixed API Endpoints** - Using correct `/api/v1/` endpoints
3. **✅ Added Base URL** - Proper API base URL construction
4. **✅ Added Redirect URI** - OAuth callback URL specified
5. **✅ Popup OAuth Flow** - Same popup-based flow as Google Drive
6. **✅ Token Management** - Proper token storage and retrieval
7. **✅ Session Usage** - Complete session object access

---

## 🧪 **Expected Behavior After Fix**

When clicking "Connect Gmail" button:

1. **✅ No 401 Error** - Proper authentication with Bearer token
2. **✅ OAuth Popup Opens** - Google OAuth consent screen appears
3. **✅ Successful Redirect** - After granting permissions, popup closes
4. **✅ Tokens Stored** - Access and refresh tokens saved to config
5. **✅ Status Updated** - Authentication status shows "Authenticated"
6. **✅ Test Connection Works** - Connection test passes

---

## 🔄 **Consistency Achieved**

The Gmail connector now has **identical OAuth implementation** to the working Google Drive connector:

- ✅ **Same API endpoints**
- ✅ **Same authentication headers**
- ✅ **Same popup flow**
- ✅ **Same token management**
- ✅ **Same error handling**

---

## 🎉 **Result**

The Gmail connector OAuth authentication should now work seamlessly, providing the same reliable authentication experience as Google Drive and other working connectors!

---

**🎯 Gmail OAuth 401 error is now fixed and authentication should work properly!**