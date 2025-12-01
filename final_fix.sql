-- WALLACHIA DATABASE FINAL FIX
-- Run this in Supabase SQL Editor to enable session persistence and character name saving

-- Disable RLS on tables for testing
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE game_sessions DISABLE ROW LEVEL SECURITY;

-- Verify tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('user_profiles', 'user_sessions', 'game_sessions');
