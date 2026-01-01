"""
Database Module for Wallachia Adventure
Clean database access with proper table organization
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
from models import GameState, CharacterStats, InventoryItem, ItemType


class Database:
    """Clean database access class with proper table organization"""

    def __init__(self, url: str, key: str):
        """Initialize Supabase client"""
        self.client: Optional[Client] = None
        if url and key:
            self.client = create_client(url, key)
        else:
            raise ValueError("Database URL and key are required")

    # ===============================
    # — USER PROFILE OPERATIONS
    # ===============================

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID"""
        try:
            response = self.client.table('user_profiles').select('*').eq('user_id', user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error getting user profile: {e}")
            return None

    def create_user_profile(self, user_id: str, character_name: str = 'Aventurier') -> bool:
        """Create new user profile"""
        try:
            data = {
                'user_id': user_id,
                'character_name': character_name,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            response = self.client.table('user_profiles').insert(data).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ Error creating user profile: {e}")
            return False

    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()
            response = self.client.table('user_profiles').update(updates).eq('user_id', user_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ Error updating user profile: {e}")
            return False

    def update_character_name(self, user_id: str, character_name: str) -> bool:
        """Update character name for user"""
        return self.update_user_profile(user_id, {'character_name': character_name})

    # ===============================
    # — GAME SESSION OPERATIONS
    # ===============================

    def get_active_game_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent active game session for user"""
        try:
            print(f"[DB] Fetching active session for {user_id}...")
            response = self.client.table('game_sessions').select('*').eq('user_id', user_id).eq('is_active', True).order('updated_at', desc=True).limit(1).execute()
            if response.data:
                print(f"[DB] Found active session: {response.data[0].get('session_id')}")
                return response.data[0]
            print(f"[DB] No active session found for {user_id}")
            return None
        except Exception as e:
            print(f"❌ Error getting active game session: {e}")
            return None

    def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """List all game sessions for a user"""
        try:
            response = self.client.table('game_sessions').select('session_id, created_at, updated_at, current_turn, is_active').eq('user_id', user_id).order('updated_at', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Error listing user sessions: {e}")
            return []

    def set_active_session(self, user_id: str, session_id: str) -> bool:
        """Set a specific session as active and others as inactive"""
        try:
            # Deactivate all
            self.client.table('game_sessions').update({'is_active': False}).eq('user_id', user_id).execute()
            # Activate specific one
            self.client.table('game_sessions').update({'is_active': True}).eq('session_id', session_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error setting active session: {e}")
            return False

    def _sanitize_story_data(self, story: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize story data to ensure JSON serialization (handle bytes)"""
        import base64
        sanitized_story = []
        for msg in story:
            new_msg = msg.copy()
            # Convert bytes images to Base64 Data URIs
            if "image" in new_msg and isinstance(new_msg["image"], bytes):
                try:
                    b64 = base64.b64encode(new_msg["image"]).decode('utf-8')
                    new_msg["image"] = f"data:image/png;base64,{b64}"
                except Exception as e:
                    print(f"⚠️ Failed to encode image for DB: {e}")
                    new_msg["image"] = None
            sanitized_story.append(new_msg)
        return sanitized_story

    def create_game_session(self, user_id: str, game_state: GameState) -> Optional[str]:
        """Create new game session and return session ID"""
        try:
            # Use UUID to ensure uniqueness and prevent collisions/deletions
            import uuid
            session_id = f"{user_id}_{uuid.uuid4().hex[:12]}"

            # Convert game state to database format
            session_data = {
                'session_id': session_id,
                'user_id': user_id,
                'story_data': self._sanitize_story_data(game_state.story),
                'character_stats': game_state.character.model_dump(mode='json'),
                'inventory': [item.model_dump(mode='json') for item in game_state.inventory],
                'current_turn': game_state.turn,
                'last_image_turn': game_state.last_image_turn,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            response = self.client.table('game_sessions').insert(session_data).execute()
            return session_id if len(response.data) > 0 else None
        except Exception as e:
            print(f"❌ Error creating game session: {e}")
            return None

    def update_game_session(self, session_id: str, game_state: GameState) -> bool:
        """Update existing game session"""
        try:
            session_data = {
                'story_data': self._sanitize_story_data(game_state.story),
                'character_stats': game_state.character.model_dump(mode='json'),
                'inventory': [item.model_dump(mode='json') for item in game_state.inventory],
                'current_turn': game_state.turn,
                'last_image_turn': game_state.last_image_turn,
                'updated_at': datetime.utcnow().isoformat()
            }

            response = self.client.table('game_sessions').update(session_data).eq('session_id', session_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ Error updating game session: {e}")
            return False

    def load_game_session(self, session_id: str) -> Optional[GameState]:
        """Load game session and convert to GameState"""
        try:
            response = self.client.table('game_sessions').select('*').eq('session_id', session_id).execute()
            if not response.data:
                return None

            session_data = response.data[0]

            # Convert inventory back to InventoryItem objects
            inventory = []
            for item_data in session_data.get('inventory', []):
                try:
                    # Handle both dict and InventoryItem formats
                    if isinstance(item_data, dict):
                        inventory.append(InventoryItem(**item_data))
                    else:
                        inventory.append(item_data)
                except Exception as e:
                    print(f"⚠️ Error parsing inventory item: {e}")
                    continue

            # Create GameState from database data
            game_state = GameState(
                character=CharacterStats(**session_data.get('character_stats', {})),
                inventory=inventory,
                story=session_data.get('story_data', []),
                turn=session_data.get('current_turn', 0),
                last_image_turn=session_data.get('last_image_turn', -10)
            )

            return game_state
        except Exception as e:
            print(f"❌ Error loading game session: {e}")
            return None

    def deactivate_old_sessions(self, user_id: str) -> bool:
        """Deactivate all old sessions for user (keep only latest)"""
        try:
            # Get all active sessions for user
            response = self.client.table('game_sessions').select('session_id').eq('user_id', user_id).eq('is_active', True).order('updated_at', desc=True).execute()

            if len(response.data) > 1:
                # Keep only the most recent, deactivate others
                sessions_to_deactivate = response.data[1:]  # Skip first (most recent)
                session_ids = [s['session_id'] for s in sessions_to_deactivate]

                self.client.table('game_sessions').update({'is_active': False}).in_('session_id', session_ids).execute()

            return True
        except Exception as e:
            print(f"❌ Error deactivating old sessions: {e}")
            return False

    def delete_old_autosaves(self, user_id: str, current_session_id: str) -> bool:
        """
        Delete all auto-saved sessions (non-manual) except the current active one.
        This ensures only one autosave exists per user.
        """
        try:
            # Fetch all sessions
            response = self.client.table('game_sessions').select('session_id').eq('user_id', user_id).execute()
            all_sessions = response.data if response.data else []
            
            ids_to_delete = []
            for s in all_sessions:
                sid = s['session_id']
                # If it's NOT the current one AND NOT a manual save
                if sid != current_session_id and "_manual" not in sid:
                    ids_to_delete.append(sid)
            
            if ids_to_delete:
                print(f"[DB] Cleaning up {len(ids_to_delete)} old autosaves...")
                self.client.table('game_sessions').delete().in_('session_id', ids_to_delete).execute()
                
            return True
        except Exception as e:
            print(f"❌ Error deleting old autosaves: {e}")
            return False

    # ===============================
    # — UTILITY METHODS
    # ===============================

    def ensure_user_exists(self, user_id: str, character_name: str = 'Aventurier') -> bool:
        """Ensure user profile exists, create if not"""
        profile = self.get_user_profile(user_id)
        if not profile:
            success = self.create_user_profile(user_id, character_name)
            if not success:
                print(f"⚠️ Could not create user profile for {user_id}, continuing without profile")
                return False  # Don't fail the entire flow
        return True

    def save_game_state(self, user_id: str, game_state: GameState, session_id: Optional[str] = None) -> Optional[str]:
        """Save game state - create new session if none exists"""
        try:
            if session_id:
                # Update existing session
                success = self.update_game_session(session_id, game_state)
                return session_id if success else None
            else:
                # Create new session
                return self.create_game_session(user_id, game_state)
        except Exception as e:
            print(f"❌ Error saving game state: {e}")
            return None

    def load_user_game(self, user_id: str) -> tuple[Optional[GameState], Optional[str]]:
        """Load user's active game session"""
        try:
            print(f"[DB] Loading user game for {user_id}...")
            # Ensure user profile exists
            self.ensure_user_exists(user_id)

            # Get active session
            session = self.get_active_game_session(user_id)
            if session:
                print(f"[DB] Loading session data for {session['session_id']}...")
                game_state = self.load_game_session(session['session_id'])
                if game_state:
                    print(f"[DB] Game state loaded successfully")
                    return game_state, session['session_id']
                else:
                    print(f"[DB] Failed to parse game state from session")

            print("[DB] No loadable game found")
            return None, None
        except Exception as e:
            print(f"❌ Error loading user game: {e}")
            return None, None

    def get_user_character_name(self, user_id: str) -> str:
        """Get user's character name"""
        try:
            profile = self.get_user_profile(user_id)
            return profile.get('character_name', 'Aventurier') if profile else 'Aventurier'
        except Exception as e:
            print(f"❌ Error getting character name: {e}")
            return 'Aventurier'

    def get_last_campaign_inventory(self, user_id: str) -> Optional[List[InventoryItem]]:
        """Get inventory from the last active campaign session"""
        try:
            # We search for sessions where game_mode inside character_stats is 'Campanie: Pecetea Drăculeștilor'
            # Note: JSON filtering syntax depends on Supabase/PostgREST version.
            # We fetch recent sessions and filter in python to be safe and avoid complex query issues if schema varies.
            
            response = self.client.table('game_sessions').select('inventory, character_stats').eq('user_id', user_id).order('updated_at', desc=True).limit(10).execute()
            
            if response.data:
                for session in response.data:
                    stats = session.get('character_stats', {})
                    if stats and stats.get('game_mode') == "Campanie: Pecetea Drăculeștilor":
                        # Found a campaign session!
                        raw_inv = session.get('inventory', [])
                        inventory = []
                        for item_data in raw_inv:
                            if isinstance(item_data, dict):
                                inventory.append(InventoryItem(**item_data))
                        return inventory
            return None
        except Exception as e:
            print(f"❌ Error getting last campaign inventory: {e}")
            return None
