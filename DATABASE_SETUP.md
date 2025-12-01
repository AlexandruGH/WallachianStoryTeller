# Wallachia Adventure - Database Setup Guide

## 🚀 Quick Setup

### 1. Create Supabase Project
- Go to [supabase.com](https://supabase.com) and create a new project
- Wait for the database to be ready

### 2. Run Database Schema
- Open your Supabase project dashboard
- Go to **SQL Editor** (in the left sidebar)
- Copy and paste the entire contents of `database_schema.sql`
- Click **Run** to create the tables

### 3. Get API Keys
- Go to **Settings** → **API** in your Supabase dashboard
- Copy the **Project URL** and **anon/public key**

### 4. Configure Environment
Create a `.env` file in your project root:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
OAUTH_REDIRECT_URL=http://localhost:8501
```

### 5. Test Database Connection
Run the test script:
```bash
python database_test.py
```

## 📊 Database Schema Overview

### Tables Created:
- **`user_profiles`**: Stores user character names and metadata
- **`game_sessions`**: Stores complete game state (story, inventory, stats)

### Security Features:
- **Row Level Security (RLS)** enabled on all tables
- Users can only access their own data
- Automatic timestamps with triggers

### Key Features:
- ✅ **Persistent game state** survives browser refreshes
- ✅ **Character name management** stored permanently
- ✅ **Session management** with automatic cleanup
- ✅ **Data integrity** with foreign key constraints
- ✅ **Performance optimization** with proper indexing

## 🔧 Troubleshooting

### "Auth session missing!" Error
- Make sure you've run the database schema in Supabase
- Verify your `.env` file has correct credentials
- Ensure you're logged into the app before making changes

### "Table doesn't exist" Error
- Run the SQL schema in your Supabase SQL Editor
- Check that the tables were created successfully

### Database Connection Issues
- Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct
- Check your internet connection
- Ensure Supabase project is active

## 🎮 Usage

Once setup is complete:
1. Start the app: `streamlit run app.py`
2. Log in with Google or email
3. Your game progress will be automatically saved to the database
4. Character names persist across sessions
5. Game state loads automatically when you return

## 📝 Manual Testing

You can test individual database operations:

```python
from database import Database
import os

db = Database(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

# After logging in, test operations
user_id = "your-user-id"
db.ensure_user_exists(user_id, "TestHero")
db.update_character_name(user_id, "NewHeroName")
```

## 🔒 Security Notes

- All database operations use Row Level Security
- Users can only access their own data
- Authentication is required for all operations
- Data is encrypted at rest in Supabase

## 📞 Support

If you encounter issues:
1. Check the console logs for detailed error messages
2. Run `python database_test.py` to diagnose connection issues
3. Verify your Supabase project settings
4. Check that all environment variables are set correctly
