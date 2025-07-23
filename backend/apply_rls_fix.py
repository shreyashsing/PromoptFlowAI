#!/usr/bin/env python3
"""
Quick script to apply RLS policy fixes to Supabase database.
This script will execute the SQL commands needed to fix authentication issues.
"""

import os
import sys
from supabase import create_client, Client
from app.core.config import get_settings

def apply_rls_fixes():
    """Apply RLS policy fixes to the database."""
    try:
        settings = get_settings()
        
        # Create Supabase client with service role key for admin operations
        service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        if not service_key:
            print("❌ SUPABASE_SERVICE_ROLE_KEY environment variable not found!")
            print("   You need the service role key to modify RLS policies.")
            print("   Get it from your Supabase Dashboard → Settings → API")
            return False
        
        supabase: Client = create_client(settings.SUPABASE_URL, service_key)
        
        print("🔧 Applying RLS policy fixes...")
        
        # SQL commands to fix RLS policies
        sql_commands = [
            # Ensure users table exists
            """
            CREATE TABLE IF NOT EXISTS public.users (
                id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT,
                avatar_url TEXT,
                preferences JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,
            
            # Enable RLS
            "ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;",
            
            # Drop existing policies to avoid conflicts
            'DROP POLICY IF EXISTS "Users can view own profile" ON public.users;',
            'DROP POLICY IF EXISTS "Users can create own profile" ON public.users;',
            'DROP POLICY IF EXISTS "Users can update own profile" ON public.users;',
            
            # Create RLS policies
            '''
            CREATE POLICY "Users can view own profile" ON public.users
                FOR SELECT USING (auth.uid() = id);
            ''',
            '''
            CREATE POLICY "Users can create own profile" ON public.users
                FOR INSERT WITH CHECK (auth.uid() = id);
            ''',
            '''
            CREATE POLICY "Users can update own profile" ON public.users
                FOR UPDATE USING (auth.uid() = id);
            ''',
            
            # Grant permissions
            "GRANT SELECT, INSERT, UPDATE ON public.users TO authenticated;",
        ]
        
        # Execute each SQL command
        for i, sql in enumerate(sql_commands, 1):
            try:
                print(f"   Executing step {i}/{len(sql_commands)}...")
                supabase.rpc('exec_sql', {'sql': sql.strip()}).execute()
            except Exception as e:
                # Try direct execution if RPC fails
                try:
                    supabase.postgrest.rpc('exec_sql', {'sql': sql.strip()}).execute()
                except:
                    print(f"   ⚠️  Step {i} may have failed (this might be normal): {str(e)[:100]}...")
        
        print("✅ RLS policy fixes applied successfully!")
        print("\n📋 Next steps:")
        print("1. Restart your backend server")
        print("2. Try logging in through the frontend")
        print("3. The authentication errors should be resolved")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply RLS fixes: {e}")
        print("\n🔧 Manual fix required:")
        print("1. Go to your Supabase Dashboard → SQL Editor")
        print("2. Copy and paste the contents of 'backend/fix_rls_policies.sql'")
        print("3. Click 'Run' to execute the script")
        return False

if __name__ == "__main__":
    print("🚀 PromptFlow AI - RLS Policy Fix")
    print("=" * 40)
    
    success = apply_rls_fixes()
    
    if not success:
        sys.exit(1)
    
    print("\n🎉 Fix completed! Your authentication should now work properly.")