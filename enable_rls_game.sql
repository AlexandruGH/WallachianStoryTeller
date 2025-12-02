-- Enable RLS on game_sessions table
ALTER TABLE game_sessions ENABLE ROW LEVEL SECURITY;

-- Ensure policies exist
DROP POLICY IF EXISTS "Users can view their own game sessions" ON game_sessions;
DROP POLICY IF EXISTS "Users can update their own game sessions" ON game_sessions;
DROP POLICY IF EXISTS "Users can insert their own game sessions" ON game_sessions;
DROP POLICY IF EXISTS "Users can delete their own game sessions" ON game_sessions;

-- Re-create policies
CREATE POLICY "Users can view their own game sessions" ON game_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own game sessions" ON game_sessions
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own game sessions" ON game_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own game sessions" ON game_sessions
    FOR DELETE USING (auth.uid() = user_id);
