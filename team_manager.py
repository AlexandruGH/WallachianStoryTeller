import os
import uuid
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

class TeamManager:
    _instance = None

    def __init__(self):
        self.base_url = os.getenv('REALTIME_DATABASE_URL')
        if not self.base_url:
            raise ValueError("REALTIME_DATABASE_URL not set")
        self.auth_token = None

    def _get_url(self, path: str) -> str:
        if self.auth_token:
            return f"{self.base_url}/{path}.json?auth={self.auth_token}"
        return f"{self.base_url}/{path}.json"

    def set_auth_token(self, token: str):
        """Set Firebase authentication token"""
        self.auth_token = token

    def authenticate_with_firebase(self, id_token: str):
        """Authenticate with Firebase using a custom token or ID token"""
        # For now, we'll use the token directly
        # In production, you might need to exchange tokens
        self.auth_token = id_token

    @classmethod
    def get_instance(cls):
        """Lazy initialization of TeamManager - only loads when team mode is selected"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_team(self, creator_user_id: str, creator_username: str, max_players: int = 4, team_name: str = None) -> str:
        """Create a new team"""
        team_id = str(uuid.uuid4())[:8]
        team_data = {
            'teamId': team_id,
            'teamName': team_name or f"Echipa {team_id}",
            'createdAt': datetime.now().isoformat(),
            'maxPlayers': max_players,
            'players': {
                creator_user_id: {
                    'userId': creator_user_id,
                    'username': creator_username,
                    'characterType': '',
                    'faction': '',
                    'ready': False
                }
            },
            'gameState': {
                'episodeIndex': 1,
                'promptIndex': 0,
                'currentPrompt': '',
                'aiResponse': '',
                'aiImageUrl': '',
                'choices': {},
                'votes': {},
                'lockState': False
            },
            'metadata': {
                'isActive': True,
                'phase': 'lobby'
            }
        }

        url = self._get_url(f"teams/{team_id}")
        response = requests.put(url, json=team_data)
        response.raise_for_status()
        return team_id

    def join_team(self, team_id: str, user_id: str, username: str) -> bool:
        """Join an existing team"""
        try:
            url = self._get_url(f"teams/{team_id}")
            response = requests.get(url)

            if response.status_code != 200:
                print(f"[TEAM] Failed to get team {team_id}: {response.status_code} - {response.text}")
                return False

            team_data = response.json()

            if not team_data or not team_data.get('metadata', {}).get('isActive', True):
                print(f"[TEAM] Team {team_id} not active or doesn't exist")
                return False

            players = team_data.get('players', {})
            max_players = team_data.get('maxPlayers', 4)

            if len(players) >= max_players:
                print(f"[TEAM] Team {team_id} is full ({len(players)}/{max_players})")
                return False

            # Check if user already in team by user_id
            for player_id, player in players.items():
                if player.get('userId') == user_id:
                    print(f"[TEAM] User {user_id} ({username}) already in team {team_id}")
                    return True  # Already joined

            # Add new player using user_id as key
            players[user_id] = {
                'userId': user_id,
                'username': username,
                'characterType': '',
                'faction': '',
                'ready': False
            }

            url = self._get_url(f"teams/{team_id}/players")
            response = requests.put(url, json=players)

            if response.status_code not in [200, 201]:
                print(f"[TEAM] Failed to join team {team_id}: {response.status_code} - {response.text}")
                return False

            print(f"[TEAM] Successfully joined team {team_id} as {username} (user_id: {user_id})")
            return True

        except Exception as e:
            print(f"[TEAM] Error joining team {team_id}: {e}")
            return False

    def update_player_info(self, team_id: str, user_id: str, character_type: str, faction: str):
        """Update player character info"""
        try:
            url = self._get_url(f"teams/{team_id}/players")
            response = requests.get(url)
            if response.status_code != 200:
                print(f"[TEAM] Failed to get players for team {team_id}: {response.status_code}")
                return False
            players = response.json() or {}

            if user_id in players:
                players[user_id]['characterType'] = character_type
                players[user_id]['faction'] = faction
                response = requests.put(url, json=players)
                if response.status_code not in [200, 201]:
                    print(f"[TEAM] Failed to update player info: {response.status_code} - {response.text}")
                    return False
                print(f"[TEAM] Successfully updated player {user_id} info")
                return True
            else:
                print(f"[TEAM] Player {user_id} not found in team {team_id}")
                return False
        except Exception as e:
            print(f"[TEAM] Error updating player info: {e}")
            return False

    def update_player_name(self, team_id: str, user_id: str, new_name: str):
        """Update player display name"""
        try:
            url = self._get_url(f"teams/{team_id}/players")
            response = requests.get(url)
            if response.status_code != 200:
                return False
            players = response.json() or {}

            if user_id in players:
                players[user_id]['username'] = new_name
                response = requests.put(url, json=players)
                if response.status_code not in [200, 201]:
                    return False
                return True
            return False
        except Exception as e:
            print(f"[TEAM] Error updating player name: {e}")
            return False

    def set_player_ready(self, team_id: str, user_id: str, ready: bool):
        """Set player ready status"""
        url = self._get_url(f"teams/{team_id}/players")
        response = requests.get(url)
        if response.status_code != 200:
            return
        players = response.json() or {}

        if user_id in players:
            players[user_id]['ready'] = ready
            response = requests.put(url, json=players)
            response.raise_for_status()

            # Check if all ready to start game
            if ready and all(p.get('ready', False) for p in players.values()):
                self.start_game(team_id)

    def leave_team(self, team_id: str, user_id: str) -> bool:
        """Remove a player from the team"""
        try:
            url = self._get_url(f"teams/{team_id}/players")
            response = requests.get(url)
            if response.status_code != 200:
                print(f"[TEAM] Failed to get players for team {team_id}: {response.status_code}")
                return False
            players = response.json() or {}

            # Remove the player if they exist
            if user_id in players:
                del players[user_id]
                response = requests.put(url, json=players)
                if response.status_code not in [200, 201]:
                    print(f"[TEAM] Failed to remove player {user_id} from team {team_id}: {response.status_code}")
                    return False
                print(f"[TEAM] Successfully removed player {user_id} from team {team_id}")

                # If team becomes empty, mark it as inactive
                if not players:
                    metadata_url = self._get_url(f"teams/{team_id}/metadata")
                    metadata = {"isActive": False, "phase": "lobby"}
                    metadata_response = requests.put(metadata_url, json=metadata)
                    if metadata_response.status_code not in [200, 201]:
                        print(f"[TEAM] Failed to deactivate empty team {team_id}")
                    else:
                        print(f"[TEAM] Deactivated empty team {team_id}")

                return True
            else:
                print(f"[TEAM] Player {user_id} not found in team {team_id}")
                return False
        except Exception as e:
            print(f"[TEAM] Error removing player from team: {e}")
            return False

    def start_game(self, team_id: str):
        """Start the game for the team"""
        url = self._get_url(f"teams/{team_id}/metadata/phase")
        response = requests.put(url, json='in_progress')
        response.raise_for_status()
        # Initialize game state if needed

    def get_team_data(self, team_id: str) -> Optional[Dict]:
        """Get team data"""
        url = self._get_url(f"teams/{team_id}")
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    def get_all_teams(self) -> Dict[str, Dict]:
        """Get all active teams that are open for joining (have at least 1 player waiting)"""
        url = self._get_url("teams")
        response = requests.get(url)
        if response.status_code == 200:
            teams = response.json() or {}
            # Filter only active teams that have at least 1 player and space for more
            open_teams = {}
            for team_id, team_data in teams.items():
                if team_data and team_data.get('metadata', {}).get('isActive', True):
                    players = team_data.get('players', {})
                    max_players = team_data.get('maxPlayers', 4)
                    current_players = len(players)

                    # Only include teams that:
                    # 1. Have at least 1 player already waiting
                    # 2. Are not full (have space for more players)
                    if current_players >= 1 and current_players < max_players:
                        open_teams[team_id] = team_data
            return open_teams
        return {}

    def update_game_state(self, team_id: str, game_state: Dict):
        """Update team game state"""
        url = self._get_url(f"teams/{team_id}/gameState")
        response = requests.put(url, json=game_state)
        response.raise_for_status()

    def vote_choice(self, team_id: str, user_id: str, choice_id: str):
        """Record player vote"""
        url = self._get_url(f"teams/{team_id}/gameState/votes")
        response = requests.get(url)
        votes = response.json() if response.status_code == 200 else {}
        votes[user_id] = choice_id
        response = requests.put(url, json=votes)
        response.raise_for_status()

        # Check for majority or all votes
        players_url = self._get_url(f"teams/{team_id}/players")
        players_response = requests.get(players_url)
        if players_response.status_code == 200:
            players = players_response.json() or {}
            total_players = len(players)
            vote_counts = {}
            for vote in votes.values():
                vote_counts[vote] = vote_counts.get(vote, 0) + 1

            # Simple majority
            for choice, count in vote_counts.items():
                if count >= (total_players // 2) + 1:
                    self.finalize_choice(team_id, choice)
                    break

    def finalize_choice(self, team_id: str, choice_id: str):
        """Finalize the chosen action"""
        url = self._get_url(f"teams/{team_id}/gameState/lockState")
        response = requests.put(url, json=True)
        response.raise_for_status()
        # Proceed to AI generation

    def set_ai_response(self, team_id: str, prompt: str, response: str, image_url: str):
        """Set AI generated content"""
        url = self._get_url(f"teams/{team_id}/gameState")
        game_state_response = requests.get(url)
        game_state = game_state_response.json() if game_state_response.status_code == 200 else {}
        game_state['currentPrompt'] = prompt
        game_state['aiResponse'] = response
        game_state['aiImageUrl'] = image_url
        game_state['lockState'] = False
        game_state['votes'] = {}  # Clear votes
        game_state['episodeIndex'] = game_state.get('episodeIndex', 1) + 1  # Or promptIndex
        response = requests.put(url, json=game_state)
        response.raise_for_status()

    def set_choices(self, team_id: str, choices: Dict[str, Dict[str, str]]):
        """Set voting choices for the team"""
        url = self._get_url(f"teams/{team_id}/gameState/choices")
        response = requests.put(url, json=choices)
        response.raise_for_status()

    def get_cached_ai_response(self, team_id: str, episode_index: int, prompt_index: int) -> Optional[Dict]:
        """Check for cached AI response"""
        # For simplicity, check if gameState has currentPrompt and aiResponse
        url = self._get_url(f"teams/{team_id}/gameState")
        response = requests.get(url)
        if response.status_code == 200:
            game_state = response.json()
            if (game_state.get('episodeIndex') == episode_index and
                game_state.get('promptIndex') == prompt_index and
                game_state.get('aiResponse')):
                return game_state
        return None

    def listen_to_team_changes(self, team_id: str, callback):
        """Listen for realtime changes - Note: REST API doesn't support realtime, use WebSocket or polling"""
        # For REST API, we can't listen in realtime. This would require WebSocket or periodic polling.
        # For now, return None or implement polling if needed.
        pass

# Singleton instance
team_manager = TeamManager()
