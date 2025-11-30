#!/usr/bin/env python3
"""
Database Connection Test Script
Run this to verify database setup and connection
"""

import os
from dotenv import load_dotenv
load_dotenv()

from database import Database

def test_database():
    """Test database connection and basic operations"""

    print("🧪 Testing Database Connection...")

    # Get credentials
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env file")
        return

    print(f"📡 Connecting to: {url[:30]}...")

    try:
        # Create database instance
        db = Database(url, key)
        print("✅ Database client created successfully")

        # Test basic connection
        if db.client:
            print("✅ Supabase client is valid")
        else:
            print("❌ Supabase client is None")
            return

        # Test auth
        try:
            user = db.client.auth.get_user()
            if user and user.user:
                print(f"✅ Authenticated as user: {user.user.id}")
                user_id = user.user.id
            else:
                print("❌ No authenticated user found")
                print("Please log in to the app first, then run this test")
                return
        except Exception as e:
            print(f"❌ Auth error: {e}")
            return

        # Test user profile operations
        print("\n📋 Testing User Profile Operations...")

        # Get current profile
        profile = db.get_user_profile(user_id)
        if profile:
            print(f"✅ Found user profile: {profile}")
        else:
            print("⚠️ No user profile found, creating one...")

        # Ensure user exists
        success = db.ensure_user_exists(user_id, "TestUser")
        if success:
            print("✅ User profile ensured/created")
        else:
            print("❌ Failed to ensure user profile")
            return

        # Update character name
        success = db.update_character_name(user_id, "TestHero")
        if success:
            print("✅ Character name updated successfully")
        else:
            print("❌ Failed to update character name")

        # Get updated name
        name = db.get_user_character_name(user_id)
        print(f"📝 Current character name: {name}")

        # Test game session operations
        print("\n🎮 Testing Game Session Operations...")

        from models import GameState, CharacterStats, InventoryItem, ItemType

        # Create test game state
        test_game_state = GameState(
            character=CharacterStats(health=85, gold=25, reputation=70, location="TestCity"),
            inventory=[
                InventoryItem(name="Test Sword", type=ItemType.weapon, value=10, quantity=1),
                InventoryItem(name="Test Shield", type=ItemType.weapon, value=8, quantity=1),
            ],
            story=[
                {"role": "ai", "text": "Test story message", "turn": 0, "image": None}
            ],
            turn=1,
            last_image_turn=-5
        )

        # Save game state
        session_id = db.save_game_state(user_id, test_game_state)
        if session_id:
            print(f"✅ Game session saved with ID: {session_id}")
        else:
            print("❌ Failed to save game session")
            return

        # Load game state
        loaded_state, loaded_session_id = db.load_user_game(user_id)
        if loaded_state and loaded_session_id:
            print(f"✅ Game session loaded: {loaded_session_id}")
            print(f"📊 Character health: {loaded_state.character.health}")
            print(f"💰 Character gold: {loaded_state.character.gold}")
            print(f"📦 Inventory items: {len(loaded_state.inventory)}")
        else:
            print("❌ Failed to load game session")

        print("\n🎉 All database tests passed!")
        print("Your database is properly configured and working.")

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database()
