# IMMEDIATE FIX for Authentication Issues

## Problem
Users are getting logged out immediately due to RLS policy violations and Pydantic validation errors.

## Quick Fix (2 minutes)

### Step 1: Apply Database Fix
1. **Go to your Supabase Dashboard**
2. **Navigate to SQL Editor**
3. **Copy and paste this SQL code**:

```sql
-- Fix RLS policies for users table
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
DROP POLICY IF EXISTS "Users can create own profile" ON public.users;
DROP POLICY IF EXISTS "Users can update own profile" ON public.users;

-- Create proper RLS policies
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can create own profile" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE ON public.users TO authenticated;
```

4. **Click "Run" to execute**

### Step 2: Restart Backend
```bash
# Stop your current backend server (Ctrl+C)
# Then restart it:
cd backend
python -m uvicorn app.main:app --reload
```

### Step 3: Test
- Try logging in through your frontend
- Submit a prompt in the chat
- You should no longer get logged out

## What This Fixes
- ✅ RLS policy violations when creating user profiles
- ✅ Pydantic validation errors for datetime fields
- ✅ Authentication failures on API calls
- ✅ Users getting logged out when submitting prompts

## If It Still Doesn't Work
1. Check your Supabase logs for any remaining errors
2. Verify the SQL executed successfully (no red error messages)
3. Make sure you restarted the backend server
4. Try with a fresh browser session (clear cookies)

## Alternative: Use the Full Fix Script
If you have your Supabase service role key, you can run:
```bash
cd backend
python apply_rls_fix.py
```

But the manual SQL approach above is simpler and more reliable.