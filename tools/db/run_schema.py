#!/usr/bin/env python3
"""
Script to help run the database schema
This reads the schema file and provides clear instructions
"""

import os
import sys

# Add root directory to path to allow importing modules if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from dotenv import load_dotenv
load_dotenv()

def show_schema_setup():
    """Display clear instructions for schema setup"""

    print("🚀 WALLACHIA ADVENTURE - DATABASE SETUP")
    print("=" * 50)
    
    # Path to schema file relative to root or script
    # Assuming script is in tools/db/ and schema in sql/
    # If running from root, CWD is root.
    
    schema_path = 'sql/database_schema.sql'
    if not os.path.exists(schema_path):
        # Fallback relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(script_dir, '../../sql/database_schema.sql')

    # Check if schema file exists
    if not os.path.exists(schema_path):
        print(f"❌ {schema_path} file not found!")
        return

    # Read the schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_content = f.read()

    print("📋 DATABASE SCHEMA FOUND")
    print(f"Schema file size: {len(schema_content)} characters")
    print()

    print("🔧 SETUP INSTRUCTIONS:")
    print("1. Go to https://supabase.com/dashboard")
    print("2. Open your project")
    print("3. Click 'SQL Editor' in the left sidebar")
    print("4. Copy and paste the ENTIRE schema below:")
    print()
    print("-" * 50)
    print("SCHEMA CONTENT:")
    print("-" * 50)
    print(schema_content)
    print("-" * 50)
    print()
    print("5. Click 'Run' to execute the schema")
    print("6. Check that tables 'user_profiles' and 'game_sessions' were created")
    print("7. Run: python database_test.py")
    print()

    # Check environment
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if url and key:
        print("✅ Environment variables found:")
        print(f"   SUPABASE_URL: {url[:30]}...")
        print(f"   SUPABASE_ANON_KEY: {'*' * len(key)}")
    else:
        print("❌ Missing environment variables!")
        print("   Create .env file with:")
        print("   SUPABASE_URL=your_project_url")
        print("   SUPABASE_ANON_KEY=your_anon_key")

    print()
    print("🎯 AFTER RUNNING SCHEMA:")
    print("✅ Character name changes will work")
    print("✅ Game state will persist")
    print("✅ No more session loss issues")

if __name__ == "__main__":
    show_schema_setup()
