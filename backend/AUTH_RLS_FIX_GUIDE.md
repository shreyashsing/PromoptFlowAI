# Authentication RLS Policy Fix Guide

## Problem
Users are getting logged out immediately when submitting prompts due to RLS (Row Level Security) policy violations when trying to create user profiles in the database.

**Error Message:**
```
"Failed to create/update user profile: {'message': 'new row violates row-level security policy for table \"users\"', 'code': '42501'}"
```

## Root Cause
The Supabase database is missing the proper RLS policies that allow users to create their own profiles in the `users` table. When a user logs in, the backend tries to create/update their profile but gets blocked by RLS.

## Solution

### Step 1: Apply Database Fixes
Run the `fix_rls_policies.sql` script in your Supabase SQL Editor:

1. Go to your Supabase Dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `backend/fix_rls_policies.sql`
4. Click "Run" to execute the script

This script will:
- Create proper RLS policies for all tables
- Add a trigger to automatically create user profiles on signup
- Grant necessary permissions to authenticated users
- Handle edge cases and conflicts

### Step 2: Backend Code Updates
The backend code has been updated to handle RLS policy failures gracefully:

- **Fallback Profile Creation**: If database insertion fails, creates an in-memory profile
- **Graceful Error Handling**: Prevents authentication failures due to profile creation issues
- **Logging**: Better error logging to help debug issues

### Step 3: Verify the Fix

1. **Restart your backend server**:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. **Test the authentication flow**:
   ```bash
   cd backend
   python test_auth_fix.py
   ```

3. **Try logging in through the frontend**

## What the Fix Does

### Database Level
- **RLS Policies**: Ensures users can create, read, and update their own data
- **Auto Profile Creation**: Trigger automatically creates user profiles when users sign up
- **Permissions**: Grants proper permissions to authenticated users

### Backend Level
- **Resilient Auth**: Authentication continues to work even if profile creation fails
- **Fallback Profiles**: Creates temporary profiles when database operations fail
- **Better Logging**: Improved error messages for debugging

## Testing the Fix

### Expected Behavior After Fix
1. Users can log in successfully
2. User profiles are created automatically
3. No more 401 Unauthorized errors on API calls
4. Chat interface works without logging users out

### If Issues Persist

1. **Check Supabase Logs**:
   - Go to Supabase Dashboard → Logs
   - Look for any RLS policy violations

2. **Check Backend Logs**:
   - Look for authentication errors in your backend console
   - Check for any remaining RLS policy issues

3. **Verify Database Schema**:
   - Ensure the `users` table exists with correct structure
   - Verify RLS policies are applied correctly

4. **Test with Fresh User**:
   - Try creating a new user account
   - Check if the profile is created automatically

## Manual Verification

You can manually verify the RLS policies in Supabase:

```sql
-- Check if RLS is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND tablename = 'users';

-- Check existing policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'public' AND tablename = 'users';
```

## Rollback Plan

If you need to rollback the changes:

```sql
-- Disable RLS temporarily (NOT recommended for production)
ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;

-- Or remove specific policies
DROP POLICY IF EXISTS "Users can create own profile" ON public.users;
```

## Prevention

To prevent this issue in the future:
1. Always test RLS policies with actual user authentication
2. Include RLS policy creation in your database migration scripts
3. Test authentication flows end-to-end before deploying
4. Monitor Supabase logs for RLS violations

## Support

If you continue to experience issues:
1. Check the backend logs for specific error messages
2. Verify your Supabase project settings
3. Ensure your environment variables are correct
4. Test with a fresh user account