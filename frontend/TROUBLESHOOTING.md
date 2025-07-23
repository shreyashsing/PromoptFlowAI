# Authentication Troubleshooting Guide

## Common Issues and Solutions

### 1. "Failed to fetch" Error on Sign Up/Sign In

**Cause**: Environment variables not properly configured or Supabase connection issues.

**Solutions**:

1. **Check Environment Variables**:
   ```bash
   # Make sure .env.local has the correct values:
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
   ```

2. **Restart Development Server**:
   ```bash
   # Stop the server (Ctrl+C) and restart
   npm run dev
   ```

3. **Verify Supabase Project**:
   - Go to your Supabase dashboard
   - Check that the project is active
   - Verify the URL and anon key are correct

4. **Check Browser Console**:
   - Open browser dev tools (F12)
   - Look for "Supabase Config" log message
   - Should show "url: Set, key: Set"

### 2. Environment Variable Priority

Next.js loads environment variables in this order:
1. `.env.local` (highest priority)
2. `.env.development` 
3. `.env`

Make sure your `.env.local` file has the correct values, not placeholders.

### 3. Network Issues

**Check**:
- Internet connection
- Firewall settings
- Corporate proxy settings
- VPN interference

### 4. Supabase Project Issues

**Verify**:
- Project is not paused
- Authentication is enabled
- Email provider is configured
- RLS policies (if any) are correct

## Debug Steps

1. **Check Console Logs**:
   ```javascript
   // Should see in browser console:
   "Supabase Config: {url: 'Set', key: 'Set'}"
   "Testing Supabase connection..."
   "Supabase connection successful!"
   ```

2. **Test Basic Connection**:
   ```javascript
   // In browser console:
   import { supabase } from './lib/supabase'
   supabase.auth.getSession().then(console.log)
   ```

3. **Verify Environment Variables**:
   ```javascript
   // In browser console:
   console.log({
     url: process.env.NEXT_PUBLIC_SUPABASE_URL,
     key: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
   })
   ```

## Quick Fix Checklist

- [ ] Correct environment variables in `.env.local`
- [ ] Restarted development server
- [ ] Supabase project is active
- [ ] No console errors
- [ ] Network connection working
- [ ] Browser cache cleared (if needed)

## Still Having Issues?

1. Check the browser network tab for failed requests
2. Verify Supabase dashboard shows your project as active
3. Try creating a new test user directly in Supabase dashboard
4. Check if email confirmation is required
5. Verify CORS settings in Supabase if needed

## Contact Support

If issues persist:
1. Check browser console for specific error messages
2. Note the exact steps that cause the error
3. Verify environment configuration
4. Test with a fresh browser session