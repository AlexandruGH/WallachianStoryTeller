-- Wallachia Adventure Database Schema
-- Run this SQL in your Supabase SQL editor to create the necessary tables

-- Enable Row Level Security (RLS) for all tables
-- This ensures users can only access their own data

-- ===============================
-- USER PROFILES TABLE
-- ===============================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    character_name TEXT NOT NULL DEFAULT 'Aventurier',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Enable RLS
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Create policies (allowing authenticated users to manage their profiles)
CREATE POLICY "Users can view their own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- TEMPORARILY DISABLE RLS for testing character name saving
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;

-- Alternative policies (uncomment when ready to secure):
-- CREATE POLICY "Allow all operations for authenticated users" ON user_profiles
--     FOR ALL USING (auth.role() = 'authenticated');

-- ===============================
-- GAME SESSIONS TABLE
-- ===============================
CREATE TABLE IF NOT EXISTS game_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    story_data JSONB NOT NULL DEFAULT '[]'::jsonb,
    character_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    inventory JSONB NOT NULL DEFAULT '[]'::jsonb,
    current_turn INTEGER NOT NULL DEFAULT 0,
    last_image_turn INTEGER NOT NULL DEFAULT -10,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,

    -- Foreign key constraint
    CONSTRAINT fk_game_sessions_user_id
        FOREIGN KEY (user_id)
        REFERENCES auth.users(id)
        ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON game_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_active ON game_sessions(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_game_sessions_updated ON game_sessions(updated_at DESC);

-- Enable RLS
ALTER TABLE game_sessions ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view their own game sessions" ON game_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own game sessions" ON game_sessions
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own game sessions" ON game_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own game sessions" ON game_sessions
    FOR DELETE USING (auth.uid() = user_id);

-- ===============================
-- USER SESSIONS TABLE (for session persistence)
-- ===============================
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    session_data JSONB,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,

    -- Foreign key constraint
    CONSTRAINT fk_user_sessions_user_id
        FOREIGN KEY (user_id)
        REFERENCES auth.users(id)
        ON DELETE CASCADE
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(last_active DESC);

-- TEMPORARILY DISABLE RLS for testing (enable later with proper policies)
ALTER TABLE user_sessions DISABLE ROW LEVEL SECURITY;

-- Alternative policies (uncomment when ready to secure):
-- CREATE POLICY "Users can view their own sessions" ON user_sessions
--     FOR SELECT USING (auth.uid() = user_id);
--
-- CREATE POLICY "Users can manage their own sessions" ON user_sessions
--     FOR ALL USING (auth.uid() = user_id);

-- ===============================
-- FUNCTIONS
-- ===============================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_game_sessions_updated_at
    BEFORE UPDATE ON game_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===============================
-- INITIAL DATA (Optional)
-- ===============================

-- You can uncomment and run this to create a sample user profile
-- INSERT INTO user_profiles (user_id, character_name)
-- VALUES ('your-user-id-here', 'Vlad Dracul')
-- ON CONFLICT (user_id) DO NOTHING;
