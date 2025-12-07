#!/usr/bin/env python3
"""
Script to provide RLS disable instructions
"""

print("🚨 WALLACHIA DATABASE - RLS FIX REQUIRED")
print("=" * 50)

print("❌ You're still getting RLS (Row Level Security) errors.")
print("📋 You need to run this SQL in your Supabase SQL Editor:")
print()

print("SQL TO RUN:")
print("-" * 20)
print("""
-- Temporarily disable RLS for testing
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE game_sessions DISABLE ROW LEVEL SECURITY;
""")
print("-" * 20)

print()
print("📍 WHERE TO RUN IT:")
print("1. Go to https://supabase.com/dashboard")
print("2. Open your Wallachia project")
print("3. Click 'SQL Editor' in the left sidebar")
print("4. Paste the SQL above")
print("5. Click 'Run'")

print()
print("✅ AFTER RUNNING THE SQL:")
print("- Character name changes will work")
print("- Game state will save to database")
print("- All persistence features will work")

print()
print("🔒 RE-ENABLE LATER (for production):")
print("""
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_sessions ENABLE ROW LEVEL SECURITY;
""")

print()
print("🎯 CURRENT ERROR:")
print("The policies use auth.uid() but authentication context isn't working.")
print("Disabling RLS temporarily will let you test all database features.")

print()
print("🚀 RUN THE SQL NOW AND TRY AGAIN!")
