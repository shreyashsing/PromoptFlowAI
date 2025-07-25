# Service Role Key Setup

## 📋 **Instructions**

1. **Get your service role key**:
   - Go to https://supabase.com/dashboard
   - Select project: "PromptFlow AI"
   - Go to Settings → API
   - Copy the **service_role** key (starts with `eyJ...`)

2. **Add to your backend/.env file**:
   ```env
   # Add this line to backend/.env
   SUPABASE_SERVICE_ROLE_KEY=eyJ... (paste your actual service role key here)
   ```

3. **Restart backend server**:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

4. **Test the fix**:
   - Create a conversation
   - Refresh the page
   - Conversation should restore properly

## ✅ **Expected Result**
Backend logs should show:
```
Using service role key for database operations (bypasses RLS)
```

And conversation persistence should work without 404 errors. 