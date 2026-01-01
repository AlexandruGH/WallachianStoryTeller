"""
Wallachia Adventure - Main Application
Uses database persistence for game state management
"""

import os, sys, shutil
# If ffmpeg is NOT in PATH, then try local folder
#if not shutil.which("ffmpeg"):
#    local_ffmpeg = os.path.abspath("ffmpeg/bin")
#    if os.path.isfile(os.path.join(local_ffmpeg, "ffmpeg.exe")):
#        os.environ["PATH"] = local_ffmpeg + os.pathsep + os.environ["PATH"]
from dotenv import load_dotenv
load_dotenv(override=True)
import streamlit as st
from typing import Optional, Dict, Any, List
import time
import urllib.parse
import traceback
import random
import json
import uuid
import base64
import hashlib
import secrets
import re
import requests
import threading
from datetime import datetime, timedelta
from streamlit.runtime.scriptrunner import add_script_run_ctx
try:
    import extra_streamlit_components as stx
except ImportError:
    stx = None

# Import local modules
from config import Config, ModelRouter
from character import CharacterSheet, roll_dice, update_stats
from ui_components import inject_css, render_header, render_sidebar_header_controls, render_sidebar_stats, render_sidebar_footer, display_story, render_loading_screen, scroll_to_top
from llm_handler import fix_romanian_grammar, generate_narrative_with_progress
from models import GameState, CharacterStats, InventoryItem, ItemType, NarrativeResponse
from database import Database
from character_creation import render_character_creation
from audio_manager import get_audio_manager
# Import team_manager at startup
try:
    from team_manager import TeamManager
    TEAM_MANAGER_AVAILABLE = True
except ImportError:
    TEAM_MANAGER_AVAILABLE = False
    print("Warning: team_manager module not available")

# =========================
# — Helper Classes
# =========================
class ManualUser:
    def __init__(self, id, email, user_metadata=None, app_metadata=None):
        self.id = id
        self.email = email
        self.user_metadata = user_metadata or {}
        self.app_metadata = app_metadata or {}
        self.raw_user_meta_data = self.user_metadata # Alias

class ManualSession:
    def __init__(self, access_token, refresh_token, user_data):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user = ManualUser(
            id=user_data.get('id'),
            email=user_data.get('email'),
            user_metadata=user_data.get('user_metadata'),
            app_metadata=user_data.get('app_metadata')
        )

# =========================
# — Database Configuration
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
db = Database(SUPABASE_URL, SUPABASE_ANON_KEY)

# =========================
# — Game Configuration
# =========================
# Available factions for team mode (can be easily modified)
AVAILABLE_FACTIONS = {
    "Drăculești": "🐉 Casa lui Vlad Țepeș - disciplină, război și ordine"
}

# Available character classes for team mode
AVAILABLE_CHARACTER_CLASSES = [
    "Aventurier",
    "Străjer",
    "Spion",
    "Negustor"
]

def get_cookie_manager():
    # Do NOT cache the manager instance. It needs to be re-instantiated on every run
    # to pick up the latest cookie values from the frontend widget state.
    return stx.CookieManager(key="auth_cookie_manager") if stx else None

# =========================
# — Session State Initialization
# =========================
def init_session():
    """Initialize all session state variables with database-loaded data"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]

    # CRITICAL: Only load user data if we have a valid authenticated user
    if "user" in st.session_state and st.session_state.user and st.session_state.user.user:
        user_id = st.session_state.user.user.id
        print(f"[INIT] Loading game data for authenticated user: {user_id}")

        # Ensure character name is loaded if missing
        if "character_name" not in st.session_state:
            try:
                name = db.get_user_character_name(user_id)
                st.session_state.character_name = name
                print(f"[INIT] Loaded character name: {name}")
            except Exception as e:
                print(f"[INIT] Failed to load character name: {e}")
                st.session_state.character_name = "Aventurier"

        # Check if we forced a new game from UI
        if st.session_state.get("force_new_game"):
            print(f"[INIT] 🆕 Force new game requested")
            create_new_game_state()
            
            # CRITICAL: Clear DB session ID to ensure a NEW session row is created
            if "db_session_id" in st.session_state:
                del st.session_state.db_session_id
                
            # Clean up old autosaves from DB to maintain "One Autosave" rule
            # New session ID is in st.session_state.session_id (set in ui or init)
            # We pass it to spare it (though it's not in DB yet so it doesn't matter)
            db.delete_old_autosaves(user_id, st.session_state.session_id)
            
            # Clear flag
            del st.session_state.force_new_game
            
        # Normal load - ONLY if game_state is missing (first load)
        elif "game_state" not in st.session_state:
            game_state, session_id = db.load_user_game(user_id)

            if game_state and session_id:
                st.session_state.game_state = game_state
                st.session_state.db_session_id = session_id
                print(f"[INIT] ✅ Loaded existing game session: {session_id}")
            else:
                # Create new game state
                create_new_game_state()
                print(f"[INIT] Created new game state for user: {user_id}")
                
                # CRITICAL: Save immediately to ensure persistence if session state is unstable
                try:
                    saved_sid = db.save_game_state(user_id, st.session_state.game_state, None)
                    if saved_sid:
                        st.session_state.db_session_id = saved_sid
                        print(f"[INIT] Saved initial game state to DB: {saved_sid}")
                except Exception as e:
                    print(f"[INIT] Failed to save initial state: {e}")

    else:
        print(f"[INIT] ❌ No authenticated user - creating default state")
        # No user logged in, create default game state
        create_new_game_state()

    # Initialize other session variables
    if "story" not in st.session_state:
        st.session_state.story = st.session_state.game_state.story
    if "turn" not in st.session_state:
        st.session_state.turn = st.session_state.game_state.turn
    if "character" not in st.session_state:
        st.session_state.character = st.session_state.game_state.character.model_dump()
    if "story_history" not in st.session_state:
        st.session_state.story_history = []

    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False
    if "prompt_cache" not in st.session_state:
        st.session_state.prompt_cache = ""
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "use_api_fallback": True,
            "image_interval": Config.IMAGE_INTERVAL,
            "api_fail_count": 0
        }
    if "image_queue" not in st.session_state:
        st.session_state.image_queue = []
    if "last_image_turn" not in st.session_state:
        st.session_state.last_image_turn = -10
    if "image_worker_active" not in st.session_state:
        st.session_state.image_worker_active = False
    if "user_input_buffer" not in st.session_state:
        st.session_state.user_input_buffer = ""
    if "legend_scale" not in st.session_state:
        st.session_state.legend_scale = 5
    if "is_game_over" not in st.session_state:
        st.session_state.is_game_over = False
    if "game_mode_selected" not in st.session_state:
        st.session_state.game_mode_selected = None
    if "team_id" not in st.session_state:
        st.session_state.team_id = None

def create_new_game_state():
    """Create a fresh game state"""
    italic_flavour = (
        "*Personaj (TU)*: Ești un aventurier aflat în anul 1456. Te afli la marginea cetății Târgoviște, pe o noapte rece de toamnă. "
        "Flăcările torțelor dansează în vânt, proiectând umbre lungi pe zidurile masive. "
        "Porțile de stejar se ridică încet, cu un scârțâit apăsat, iar aerul miroase "
        "a fum, fier și pământ ud. În depărtare se aud cai și voci ale străjerilor. "
        "Fiecare decizie poate naște o legendă sau poate rămâne doar o filă de cronică...*\n\n"
    )

    st.session_state.game_state = GameState(
        character=CharacterStats(),
        inventory=[
            InventoryItem(name="Pumnal", type=ItemType.weapon, value=3, quantity=1),
            InventoryItem(name="Hartă ruptă", type=ItemType.misc, value=0, quantity=1),
        ],
        story=[{
            "role": "ai",
            "text": f"{Config.make_intro_text(5)}{italic_flavour}**Ce vrei să faci?**",
            "turn": 0,
            "image": None
        }],
        turn=0,
        last_image_turn=-10
    )
    # Ensure db_session_id exists (even if None) to prevent AttributeError later
    if "db_session_id" not in st.session_state:
        st.session_state.db_session_id = None
    print(f"[INIT] Created new game state: {st.session_state.session_id}")

# =========================
# — Authentication Handlers
# =========================
def handle_email_login(email: str, password: str):
    """Handle email login"""
    try:
        user = db.client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if user.user:
            st.session_state.user = user
            # Get character name from database
            character_name = db.get_user_character_name(user.user.id)
            st.session_state.character_name = character_name
            st.success(f"✅ Bine ai venit, {character_name}!")
            time.sleep(1.5)
            st.rerun()
    except Exception as e:
        st.error(f"❌ Email sau parolă incorecte!")

def handle_email_register(email: str, password: str, character_name: str):
    """Handle email registration"""
    try:
        user = db.client.auth.sign_up({
            "email": email,
            "password": password
        })
        if user.user:
            # Create user profile in database
            db.ensure_user_exists(user.user.id, character_name)
            st.session_state.user = user
            st.session_state.character_name = character_name
            st.success(f"✅ Cont creat! Bine ai venit, {character_name}!")
            time.sleep(2)
            st.rerun()
    except Exception as e:
        st.error(f"❌ Eroare la crearea contului: {str(e)}")

def refresh_session_via_http(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Refresh session using direct HTTP request to bypass client state issues"""
    try:
        if not refresh_token:
            return None
            
        token_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "refresh_token": refresh_token
        }
        
        resp = requests.post(token_url, headers=headers, json=data)
        
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[AUTH] ❌ HTTP Refresh failed: {resp.text}")
            return None
    except Exception as e:
        print(f"[AUTH] ❌ HTTP Refresh error: {e}")
        return None

def get_oauth_redirect_url():
    """Get OAuth redirect URL"""
    env_url = os.getenv("OAUTH_REDIRECT_URL")
    if env_url:
        return env_url.rstrip('/')

    # For Streamlit Cloud
    try:
        if os.getenv("STREAMLIT_SERVER_HEADLESS") == "true":
            base_url = st.get_option("server.baseUrlPath")
            if base_url:
                return base_url.rstrip('/')
    except:
        pass

    # Try secrets
    try:
        if "OAUTH_REDIRECT_URL" in st.secrets:
            return st.secrets["OAUTH_REDIRECT_URL"].rstrip('/')
    except:
        pass

    return "http://localhost:8501"

def generate_pkce_verifier():
    """Generate PKCE code verifier"""
    token = secrets.token_urlsafe(32)
    return token[:128]

def generate_pkce_challenge(verifier):
    """Generate PKCE code challenge"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

def handle_oauth_callback(cookie_manager=None):
    """Handle OAuth callback with PKCE verification"""
    try:
        query_params = dict(st.query_params)

        if "error" in query_params:
            error_msg = query_params.get("error", "Unknown error")
            st.error(f"❌ Eroare autentificare: {error_msg}")
            st.query_params.clear()
            time.sleep(2)
            st.rerun()
            return False

        if "code" in query_params:
            code = query_params["code"]

            if "pkce_verifier" not in query_params:
                st.error("❌ Eroare de securitate: Verificatorul PKCE lipsește!")
                st.query_params.clear()
                return False

            code_verifier = query_params["pkce_verifier"]

            # Exchange code for session using direct HTTP to avoid library state issues
            print(f"[OAUTH] Exchanging code: {code[:10]}... with verifier: {code_verifier[:10]}...")
            
            # 1. Try direct HTTP exchange (Most robust)
            session_response = None
            try:
                # Use grant_type=pkce as expected by Supabase
                token_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=pkce"
                headers = {
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json"
                }
                
                # Reconstruct the exact redirect_uri used in the authorization request
                redirect_base = get_oauth_redirect_url()
                redirect_uri = f"{redirect_base}?pkce_verifier={code_verifier}"
                
                data = {
                    "auth_code": code,
                    "code_verifier": code_verifier,
                    "redirect_uri": redirect_uri
                }
                
                resp = requests.post(token_url, headers=headers, json=data)
                
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"[OAUTH] Response data keys: {list(data.keys())}")
                    
                    # Manually set the session on the Supabase client
                    try:
                        db.client.auth.set_session(data.get('access_token'), data.get('refresh_token', ''))
                    except Exception as set_err:
                        print(f"[OAUTH] Warning: set_session failed: {set_err}")
                    
                    # Retrieve the session object to match expected format
                    session_response = db.client.auth.get_session()
                    
                    # If get_session fails but we have the data, construct a session-like object
                    if not session_response:
                        if 'user' in data:
                            print("[OAUTH] ⚠️ get_session() returned None, constructing manual session object")
                            session_response = ManualSession(
                                access_token=data.get('access_token'),
                                refresh_token=data.get('refresh_token'),
                                user_data=data['user']
                            )
                        else:
                            print("[OAUTH] ❌ Response missing 'user' object despite 200 OK")
                        
                    print(f"[OAUTH] ✅ Direct HTTP exchange successful. Session object: {session_response is not None}")
                    if session_response:
                         print(f"[OAUTH] Session user: {session_response.user}")
                else:
                    error_details = resp.text
                    print(f"[OAUTH] ❌ Direct exchange failed: {error_details}")
                    
                    # Save error for final check
                    st.session_state.last_oauth_error = error_details

                    # Fallback to library method
                    # Pass arguments as a dictionary/object as required by newer versions
                    session_response = db.client.auth.exchange_code_for_session({
                        "auth_code": code,
                        "code_verifier": code_verifier,
                        "redirect_uri": redirect_uri
                    })
            except Exception as e:
                print(f"[OAUTH] ❌ Exchange error: {e}")
                st.session_state.last_oauth_error = str(e)
                
                # Last ditch effort: try library method if not tried yet or if HTTP failed with exception
                if not session_response:
                    try:
                        session_response = db.client.auth.exchange_code_for_session({
                            "auth_code": code,
                            "code_verifier": code_verifier,
                            "redirect_uri": redirect_uri
                        })
                    except Exception as lib_e:
                        print(f"[OAUTH] ❌ Library fallback error: {lib_e}")

            if session_response and session_response.user:
                user = session_response.user
                print(f"[OAUTH] Processing success for user: {user.id}")

                # Clear logout flag as we are successfully logging in
                if 'logging_out' in st.session_state:
                    del st.session_state['logging_out']

                # Store session with database persistence
                st.session_state.user = session_response

                # 1. Store session in database (CRITICAL: Do this BEFORE cookies to ensure persistence if script is killed)
                try:
                    print("[OAUTH] Preparing DB upsert...")
                    session_data = {
                        'user_id': user.id,
                        'session_token': session_response.access_token if hasattr(session_response, 'access_token') else None,
                        'refresh_token': session_response.refresh_token if hasattr(session_response, 'refresh_token') else None,
                        'user_agent': 'streamlit_app',
                        'created_at': str(datetime.now())
                    }
                    
                    # Check if db client is ready
                    if db.client:
                        print("[OAUTH] Executing DB upsert...")
                        # Store session in our custom sessions table for persistence
                        db.client.table('user_sessions').upsert({
                            'user_id': user.id,
                            'session_data': json.dumps(session_data),
                            'last_active': 'now()'
                        }).execute()
                        print(f"[OAUTH] Created persistent session record for user: {user.id}")
                    else:
                        print("[OAUTH] DB client is missing!")

                except Exception as session_error:
                    print(f"[OAUTH] Failed to create session record: {session_error}")
                    # Fallback: just store in session state
                    if hasattr(session_response, 'access_token'):
                        st.session_state.supabase_session_token = session_response.access_token
                
                # 2. Clear params BEFORE cookies to avoid double-submit loop
                st.query_params.clear()

                # 3. SET COOKIES FOR PERSISTENCE (Primary Method)
                # This might trigger a rerun, so it must be last
                # Initialize cookie_manager here if not provided, to avoid race condition at start of script
                if not cookie_manager:
                    cookie_manager = get_cookie_manager()

                if cookie_manager and hasattr(session_response, 'access_token'):
                    try:
                        expires = datetime.now() + timedelta(days=30)
                        # Use unique keys to avoid Streamlit duplicate key errors
                        cookie_manager.set('sb_access_token', session_response.access_token, expires_at=expires, key="set_access_token")
                        if hasattr(session_response, 'refresh_token') and session_response.refresh_token:
                            cookie_manager.set('sb_refresh_token', session_response.refresh_token, expires_at=expires, key="set_refresh_token")
                        
                        # Give time for cookies to be written before rerun
                        time.sleep(1)
                        print("[OAUTH] ✅ Auth cookies set successfully")
                    except Exception as cookie_error:
                        print(f"[OAUTH] ❌ Failed to set cookies: {cookie_error}")

                # Get or create character name
                suggested_name = 'Aventurier'
                if hasattr(user, 'raw_user_meta_data') and user.raw_user_meta_data:
                    if 'full_name' in user.raw_user_meta_data:
                        suggested_name = user.raw_user_meta_data['full_name']
                    elif 'name' in user.raw_user_meta_data:
                        suggested_name = user.raw_user_meta_data['name']
                    elif 'given_name' in user.raw_user_meta_data:
                        given_name = user.raw_user_meta_data['given_name']
                        family_name = user.raw_user_meta_data.get('family_name', '')
                        suggested_name = f"{given_name} {family_name}".strip()

                # Check if user has custom name
                has_custom_name = False
                if hasattr(user, 'user_metadata') and user.user_metadata:
                    if 'character_name' in user.user_metadata and user.user_metadata['character_name']:
                        character_name = user.user_metadata['character_name']
                        has_custom_name = True

                if not has_custom_name or character_name == 'Aventurier':
                    # Force name selection
                    character_name = suggested_name if suggested_name != 'Aventurier' else 'Aventurier'
                    st.session_state.pending_character_name = character_name

                st.session_state.character_name = character_name
                st.query_params.clear()

                st.success("✅ Autentificat cu succes!")

                # Show name selection if needed
                if 'pending_character_name' in st.session_state:
                    st.info("🎭 **Alege numele eroului tău:**")
                    with st.form("character_name_form"):
                        custom_name = st.text_input(
                            "Nume Personaj",
                            value=st.session_state.pending_character_name,
                            placeholder="Introdu numele eroului tău..."
                        )
                        if st.form_submit_button("🚀 Confirmă Numele", type="primary"):
                            # Save to database immediately
                            try:
                                db.client.table('user_profiles').upsert({
                                    'user_id': user.id,
                                    'character_name': custom_name
                                }).execute()
                                print(f"[OAUTH] Character name '{custom_name}' saved to database")
                            except Exception as db_error:
                                print(f"[OAUTH] Failed to save character name: {db_error}")

                            # Update session state
                            st.session_state.pending_name_change = custom_name
                            st.session_state.character_name = custom_name
                            if 'pending_character_name' in st.session_state:
                                del st.session_state.pending_character_name
                            st.success(f"✅ Nume erou salvat: {custom_name}")
                            time.sleep(1)
                            st.rerun()
                    return True  # Stay on auth page

                st.success(f"👋 Bine ai venit, {character_name}!")
                time.sleep(1)
                st.rerun()
                return True

            else:
                # If we have a user in session state already (from previous run), ignore this error
                if "user" in st.session_state and st.session_state.user:
                     return True

                if not st.session_state.get('reported_error'):
                    # Check if this might be a refresh (code reused) based on captured error
                    last_error = st.session_state.get('last_oauth_error', '')
                    is_refresh_error = "flow_state_not_found" in last_error or "invalid flow state" in last_error
                    
                    if is_refresh_error:
                         pass # Silent fail on refresh
                    else:
                        st.error("❌ Nu s-a putut obține sesiunea!")
                st.query_params.clear()
                return False

        return False

    except Exception as e:
        st.error(f"❌ Eroare neașteptată: {str(e)}")
        st.query_params.clear()
        return False

# =========================
# — UI Functions
# =========================
def render_auth_page(cookie_manager):
    """Authentication page with persistent session handling"""
    # Note: st.set_page_config moved to main to ensure it runs first
    inject_css()

    # Handle OAuth callback FIRST
    if "code" in st.query_params:
        with st.spinner("Procesăm autentificarea..."):
            if handle_oauth_callback():
                return
            else:
                # Only show error if it's not a refresh/stale code issue
                last_error = st.session_state.get('last_oauth_error', '')
                is_flow_error = "flow_state_not_found" in last_error or "invalid flow state" in last_error
                
                if not is_flow_error:
                    st.error("❌ Autentificarea a eșuat!")
    
    # JS Hack to handle Hash Fragments (Implicit Flow / Email Links)
    # Converts #access_token=... to ?access_token=... so Streamlit can see it
    st.components.v1.html("""
    <script>
        if (window.location.hash) {
            const params = new URLSearchParams(window.location.hash.substring(1));
            if (params.has('access_token') || params.has('error') || params.has('error_code')) {
                const newUrl = window.location.origin + window.location.pathname + '?' + window.location.hash.substring(1);
                window.location.href = newUrl;
            }
        }
    </script>
    """, height=0)

    # Handle Auth Errors (e.g. Email Link Expired)
    if "error" in st.query_params:
        error_code = st.query_params.get("error_code", "unknown_error")
        error_desc = st.query_params.get("error_description", "A apărut o eroare la autentificare.")
        
        st.error(f"⚠️ Eroare Autentificare: {error_code}")
        st.warning(f"{error_desc}")
        
        if error_code == "otp_expired":
            st.info("📧 Link-ul de verificare a expirat. Te rugăm să încerci din nou autentificarea pentru a primi un nou link.")
        
        if st.button("🔄 Încearcă din nou"):
            st.query_params.clear()
            st.rerun()

    # Check for existing session - MULTIPLE RECOVERY METHODS
    try:
        import os
        is_localhost = "localhost" in os.getenv("OAUTH_REDIRECT_URL", "") or not os.getenv("STREAMLIT_SERVER_HEADLESS")

        # Method 1: Check Cookies (Best for Cloud Persistence)
        # cookie_manager passed from main
        
        # Check logout flag to prevent auto-login loop
        is_logging_out = st.session_state.get('logging_out', False)
        
        if cookie_manager and not is_logging_out:
            # We need to give time for cookies to load
            time.sleep(0.1)
            access_token = cookie_manager.get('sb_access_token')
            refresh_token = cookie_manager.get('sb_refresh_token')

            if access_token:
                print("[AUTH] 🍪 Found session cookies")
                try:
                    # Try to restore Supabase session from cookies
                    db.client.auth.set_session(access_token, refresh_token or '')

                    # Verify restoration
                    session = db.client.auth.get_session()
                    if session and session.user:
                        st.session_state.user = session
                        character_name = db.get_user_character_name(session.user.id)
                        st.session_state.character_name = character_name
                        print(f"[AUTH] ✅ Session restored from cookies for: {character_name}")
                        # No need to rerun, main will handle it
                        return
                    else:
                        print("[AUTH] ❌ Session verification failed after cookie restore")
                        # Try to refresh the session
                        try:
                            if refresh_token:
                                print("[AUTH] 🔄 Attempting to refresh session with refresh token")
                                
                                # Try HTTP refresh first (more robust)
                                data = refresh_session_via_http(refresh_token)
                                if data:
                                    # Update client with new tokens
                                    try:
                                        db.client.auth.set_session(data['access_token'], data['refresh_token'])
                                    except:
                                        pass
                                        
                                    # Get session object (or mock it if needed, but get_session should work now)
                                    session = db.client.auth.get_session()
                                    
                                    if session and session.user:
                                        st.session_state.user = session
                                        character_name = db.get_user_character_name(session.user.id)
                                        st.session_state.character_name = character_name

                                        # Update cookies
                                        expires = datetime.now() + timedelta(days=30)
                                        cookie_manager.set('sb_access_token', data['access_token'], expires_at=expires, key="refresh_set_access")
                                        if data.get('refresh_token'):
                                            cookie_manager.set('sb_refresh_token', data['refresh_token'], expires_at=expires, key="refresh_set_refresh")
                                            
                                        print(f"[AUTH] ✅ Session refreshed via HTTP for: {character_name}")
                                        return

                                # Fallback to standard refresh
                                refresh_response = db.client.auth.refresh_session()
                                if refresh_response and refresh_response.user:
                                    st.session_state.user = refresh_response
                                    character_name = db.get_user_character_name(refresh_response.user.id)
                                    st.session_state.character_name = character_name

                                    # Update cookies with new tokens
                                    if hasattr(refresh_response, 'access_token'):
                                        expires = datetime.now() + timedelta(days=30)
                                        cookie_manager.set('sb_access_token', refresh_response.access_token, expires_at=expires, key="refresh_lib_set_access")
                                        if hasattr(refresh_response, 'refresh_token') and refresh_response.refresh_token:
                                            cookie_manager.set('sb_refresh_token', refresh_response.refresh_token, expires_at=expires, key="refresh_lib_set_refresh")

                                    print(f"[AUTH] ✅ Session refreshed from cookies for: {character_name}")
                                    return
                        except Exception as refresh_error:
                            print(f"[AUTH] ❌ Failed to refresh session: {refresh_error}")

                except Exception as cookie_restore_error:
                    print(f"[AUTH] ❌ Failed to restore from cookies: {cookie_restore_error}")
                    # Check if it's an "invalid flow state" error - if so, try refresh
                    if "invalid flow state" in str(cookie_restore_error).lower() or "flow state" in str(cookie_restore_error).lower():
                        print("[AUTH] 🔄 Detected invalid flow state, attempting HTTP refresh")
                        try:
                            if refresh_token:
                                # Try HTTP refresh first
                                data = refresh_session_via_http(refresh_token)
                                if data:
                                    # Update client with new tokens
                                    try:
                                        db.client.auth.set_session(data['access_token'], data['refresh_token'])
                                    except:
                                        pass
                                    
                                    session = db.client.auth.get_session()
                                    if session and session.user:
                                        st.session_state.user = session
                                        character_name = db.get_user_character_name(session.user.id)
                                        st.session_state.character_name = character_name

                                        # Update cookies with new tokens
                                        expires = datetime.now() + timedelta(days=30)
                                        cookie_manager.set('sb_access_token', data['access_token'], expires_at=expires, key="recover_set_access")
                                        if data.get('refresh_token'):
                                            cookie_manager.set('sb_refresh_token', data['refresh_token'], expires_at=expires, key="recover_set_refresh")

                                        print(f"[AUTH] ✅ Session recovered via HTTP refresh for: {character_name}")
                                        return
                                
                                # Fallback to standard
                                refresh_response = db.client.auth.refresh_session()
                                if refresh_response and refresh_response.user:
                                    st.session_state.user = refresh_response
                                    character_name = db.get_user_character_name(refresh_response.user.id)
                                    st.session_state.character_name = character_name

                                    # Update cookies with new tokens
                                    if hasattr(refresh_response, 'access_token'):
                                        expires = datetime.now() + timedelta(days=30)
                                        cookie_manager.set('sb_access_token', refresh_response.access_token, expires_at=expires, key="recover_lib_set_access")
                                        if hasattr(refresh_response, 'refresh_token') and refresh_response.refresh_token:
                                            cookie_manager.set('sb_refresh_token', refresh_response.refresh_token, expires_at=expires, key="recover_lib_set_refresh")

                                    print(f"[AUTH] ✅ Session recovered via refresh for: {character_name}")
                                    return
                        except Exception as refresh_error:
                            print(f"[AUTH] ❌ Refresh also failed: {refresh_error}")

                    # CRITICAL: Delete bad cookies to prevent loop
                    try:
                        cookie_manager.delete('sb_access_token')
                        cookie_manager.delete('sb_refresh_token')
                    except:
                        pass

        # Method 2: Check Streamlit session state (works on localhost)
        if "user" in st.session_state and st.session_state.user:
            print(f"[AUTH] ✅ Found user in Streamlit session: {st.session_state.user.user.id}")
            # Ensure character name is loaded
            if "character_name" not in st.session_state:
                try:
                    character_name = db.get_user_character_name(st.session_state.user.user.id)
                    st.session_state.character_name = character_name
                except Exception as name_error:
                    print(f"[AUTH] Could not load character name: {name_error}")
                    st.session_state.character_name = "Aventurier"  # fallback
            print(f"[AUTH] ✅ Session restored from Streamlit for: {st.session_state.character_name}")
            return

        # Method 3: Check database for persistent sessions (Last resort)
        # Re-enabled but guarded by logging_out flag to prevent loops
        if not is_logging_out:
            try:
                # Look for recent sessions in our custom table
                recent_sessions = db.client.table('user_sessions').select('*').order('last_active', desc=True).limit(10).execute()

                if recent_sessions.data:
                    # Try to restore from the most recent valid session
                    for session_record in recent_sessions.data:
                        try:
                            session_data = json.loads(session_record['session_data'])
                            user_id = session_record['user_id']
                            access_token = session_data.get('session_token')
                            refresh_token = session_data.get('refresh_token')

                            if access_token:
                                # Try to set the session
                                db.client.auth.set_session(access_token, refresh_token or '')

                                # Verify it worked
                                restored_session = db.client.auth.get_session()
                                if restored_session and restored_session.user:
                                    st.session_state.user = restored_session
                                    character_name = db.get_user_character_name(restored_session.user.id)
                                    st.session_state.character_name = character_name

                                    # Update last active
                                    db.client.table('user_sessions').update({
                                        'last_active': 'now()'
                                    }).eq('user_id', user_id).execute()

                                    # CRITICAL: Set cookies to prevent loop on next run
                                    if cookie_manager:
                                        try:
                                            expires = datetime.now() + timedelta(days=30)
                                            cookie_manager.set('sb_access_token', access_token, expires_at=expires, key="db_restore_set_access")
                                            if refresh_token:
                                                cookie_manager.set('sb_refresh_token', refresh_token, expires_at=expires, key="db_restore_set_refresh")
                                            print(f"[AUTH] 🍪 Cookies synchronized from database session")
                                        except Exception as cookie_err:
                                            print(f"[AUTH] Warning: Failed to sync cookies: {cookie_err}")

                                    print(f"[AUTH] ✅ Session restored from database for: {character_name}")
                                    return

                        except Exception as session_restore_error:
                            print(f"[AUTH] ❌ Failed to restore session from database record: {session_restore_error}")
                            continue

            except Exception as db_check_error:
                print(f"[AUTH] Database session check failed: {db_check_error}")

        # Method 4: Standard Supabase session check
        session = db.client.auth.get_session()
        user_response = db.client.auth.get_user()

        print(f"[AUTH] Session check - session: {session is not None}, user: {user_response is not None}")

        if session and session.user:
            print(f"[AUTH] ✅ Found active Supabase session for user: {session.user.id}")
            # Always restore session state on refresh
            st.session_state.user = session
            # Load character name from database
            character_name = db.get_user_character_name(session.user.id)
            st.session_state.character_name = character_name
            print(f"[AUTH] ✅ Session restored for: {character_name}")
            return
        elif user_response and user_response.user:
            print(f"[AUTH] ✅ Found user (no active session) for user: {user_response.user.id}")
            # Restore user but session might need refresh
            st.session_state.user = user_response
            character_name = db.get_user_character_name(user_response.user.id)
            st.session_state.character_name = character_name
            print(f"[AUTH] ✅ User restored for: {character_name}")
            return
        else:
            print("[AUTH] ❌ No session found - login required")
    except Exception as e:
        print(f"[AUTH] ❌ Session check error: {e}")
        import traceback
        traceback.print_exc()

    # If we get here, no valid session was found
    print("[AUTH] 🔄 No valid session - showing login page")

    # Clear logging_out flag if we reached the login page (user is now cleanly logged out)
    if st.session_state.get('logging_out'):
        del st.session_state['logging_out']

    # Clear any stale session state if no valid session
    if "user" in st.session_state:
        print("[AUTH] Clearing stale session state")
        del st.session_state.user
    if "character_name" in st.session_state:
        del st.session_state.character_name

    # UI
    st.markdown("""
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background: linear-gradient(135deg, #0a0805 0%, #1a0f0b 50%, #0d0704 100%);
                    z-index: -1;"></div>
    """, unsafe_allow_html=True)

    col_spacer_left, col_center, col_spacer_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown("""
            <div style="text-align: center; padding: 0 0 20px 0;">
                <h1 style="font-family: 'Cinzel', serif; font-size: 3.2rem; color: #d4af37; margin: 0;">WALLACHIA</h1>
                <p style="color: #8b6b6b; font-size: 1rem;">Aventura în Secolul XV</p>
            </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("""
                <div style="background: rgba(20, 15, 8, 0.95); border: 2px solid #5a3921;
                            border-radius: 16px; padding: 32px; max-width: 420px; margin: 0 auto;">
            """, unsafe_allow_html=True)

            # Google OAuth
            redirect_url = get_oauth_redirect_url()
            if redirect_url:
                code_verifier = generate_pkce_verifier()
                code_challenge = generate_pkce_challenge(code_verifier)
                final_redirect_url = f"{redirect_url}?pkce_verifier={code_verifier}"

                auth_url = (
                    f"{SUPABASE_URL}/auth/v1/authorize?"
                    f"provider=google&"
                    f"redirect_to={urllib.parse.quote(final_redirect_url)}&"
                    f"code_challenge={code_challenge}&"
                    f"code_challenge_method=S256&"
                    f"response_type=code&"
                    f"scope=email+profile"
                )

                st.markdown(f"""
                <div style="text-align: center;">
                    <a href="{auth_url}" target="_self" style="
                        display: inline-block;
                        background: linear-gradient(135deg, #4285f4 0%, #3367d6 100%);
                        color: white;
                        text-decoration: none;
                        padding: 16px 32px;
                        border-radius: 10px;
                        border: 2px solid #3367d6;
                        font-family: 'Crimson Text', serif;
                        font-weight: 600;
                        font-size: 1.2rem;
                        width: 100%;
                        max-width: 300px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        transition: all 0.3s ease;
                    ">
                        🔵 Continuă cu Google
                    </a>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("❌ URL de redirecționare OAuth neconfigurat!")

            st.markdown("""
                <div style="display: flex; align-items: center; margin: 25px 0;">
                    <div style="flex: 1; height: 1px; background: #5a3921;"></div>
                    <div style="margin: 0 15px; color: #8b6b6b; font-size: 0.9rem;">SAU</div>
                    <div style="flex: 1; height: 1px; background: #5a3921;"></div>
                </div>
            """, unsafe_allow_html=True)

            # Email tabs
            login_tab, register_tab = st.tabs(["🔐 LOGIN", "📝 CREAZĂ CONT"])

            with login_tab:
                with st.form("login_form", clear_on_submit=False):
                    email = st.text_input("Email", placeholder="adventurer@wallachia.ro")
                    password = st.text_input("Parolă", type="password")
                    if st.form_submit_button("⚔️ Intră în Aventură", type="primary", use_container_width=True):
                        handle_email_login(email, password)

            with register_tab:
                with st.form("register_form", clear_on_submit=False):
                    new_email = st.text_input("Email", placeholder="adventurer@wallachia.ro")
                    new_pass = st.text_input("Parolă", type="password")
                    char_name = st.text_input("Nume Personaj")
                    if st.form_submit_button("🚀 Crează Cont", type="primary", use_container_width=True):
                        handle_email_register(new_email, new_pass, char_name)

            st.markdown('</div>', unsafe_allow_html=True)

# =========================
# — Main Application
# =========================
def main():
    """Main app logic"""
    print(f"[DEBUG] Main started. User in session: {'user' in st.session_state}. Game mode: {st.session_state.get('game_mode_selected')}")

    # Set consistent page config FIRST - before any other logic to prevent reruns
    st.set_page_config(
        page_title="Wallachia - D&D Adventure",
        page_icon="⚔️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Force scroll to top on page load/rerun
    scroll_to_top()

    # 1. IMMEDIATE LOADING OVERLAY
    # Inject CSS globally first so it persists even when we clear the loading placeholder
    inject_css()
    
    # Inject smooth transitions to reduce flickering
    try:
        from ui_components import inject_smooth_transitions
        inject_smooth_transitions()
    except ImportError:
        pass

    # Render loading screen immediately to mask any processing/latency
    # We use a placeholder so we can remove it once the UI is ready
    loading_placeholder = st.empty()
    
    # Conditional Loading Screen to avoid flicker on small interactions
    # Only show on initial load, skip on reruns (like dice rolls or interactions)
    if not st.session_state.get("loading_cleared"):
        with loading_placeholder:
            render_loading_screen()

    # Check for OAuth callback FIRST (Race condition fix)
    # Do this BEFORE initializing cookie_manager to prevent component-triggered reloads from killing the OAuth flow
    if "code" in st.query_params:
         with st.spinner("Procesăm autentificarea..."):
             # Handle OAuth - pass None for cookie_manager to delay its init
             if handle_oauth_callback(None):
                 return # Rerun happened inside

    # Handle character creation polling updates (Removed)

    # Initialize cookie manager ONCE per run at the top level (Normal flow)
    cookie_manager = get_cookie_manager()

    # Check authentication
    if not db.client:
        loading_placeholder.empty() # Clear loading
        st.error("🔧 Sistemul de autentificare nu este configurat!")
        st.info("Adaugă SUPABASE_URL și SUPABASE_ANON_KEY în fișierul .env")
        return

    # Handle authentication FIRST - before any other logic
    user_authenticated = "user" in st.session_state and st.session_state.user is not None

    if user_authenticated:
        # Clear loading screen immediately if authenticated to prevent "frozen" look during background ops
        if loading_placeholder:
            loading_placeholder.empty()

    # CRITICAL FIX: Ensure db.client has the session if we are authenticated in state
    # This is necessary because db is re-initialized on every rerun
    if user_authenticated:
        try:
            current_session = db.client.auth.get_session()
            if not current_session:
                user_obj = st.session_state.user
                if hasattr(user_obj, 'access_token') and user_obj.access_token:
                    print(f"[MAIN] Restoring session to DB client for user: {user_obj.user.id}")
                    # Use refresh token if available, otherwise empty string
                    refresh_token = getattr(user_obj, 'refresh_token', '') or ''
                    db.client.auth.set_session(user_obj.access_token, refresh_token)
        except Exception as e:
            print(f"[MAIN] Warning: Failed to restore DB session: {e}")

    if not user_authenticated:
        loading_placeholder.empty() # Clear loading before showing auth page
        # Pass the single cookie_manager instance
        render_auth_page(cookie_manager)
        
        # Check again if authentication succeeded during render_auth_page (e.g. via cookies)
        # preventing an unnecessary rerun
        if "user" in st.session_state and st.session_state.user:
            user_authenticated = True
        else:
            return

    # User is authenticated - start game
    # inject_css() was already called above

    # Set up Firebase authentication for team features
    if hasattr(st.session_state.user, 'access_token'):
        try:
            from team_manager import TeamManager
            team_manager = TeamManager.get_instance()
            # Use Supabase JWT token for Firebase authentication
            team_manager.set_auth_token(st.session_state.user.access_token)
            print(f"[FIREBASE] Set Supabase JWT token for Firebase authentication")
        except Exception as e:
            print(f"[FIREBASE] Failed to set auth token: {e}")

    # Alternative: If Firebase requires separate authentication
    # You can set Firebase security rules to allow unauthenticated access for teams
    # OR create Firebase accounts programmatically when users register with Supabase

    # Initialize session AFTER authentication is confirmed
    init_session()

    # Handle pending name change - Legacy check for safety
    if "pending_name_change" in st.session_state:
        handle_name_change(st.session_state.pending_name_change)

    # Check API fallback
    if st.session_state.settings.get("api_fail_count", 0) > 3:
        st.warning("⚠️ API a eșuat de 3+ ori. Se trece în modul local automat.")
        st.session_state.settings["use_api_fallback"] = False

    # Callback functions for mode selection
    def select_solo_mode():
        st.session_state.game_mode_selected = "solo"

    def select_team_mode():
        st.session_state.game_mode_selected = "team"

    # Game Mode Selection
    if st.session_state.game_mode_selected is None:
        if loading_placeholder:
            loading_placeholder.empty()

        st.markdown("<h1 style='text-align: center; color: #D4AF37;'>🎮 Alege Modul de Joc</h1>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div style="background: rgba(20, 15, 8, 0.95); border: 2px solid #5a3921; border-radius: 16px; padding: 32px; text-align: center; min-height: 300px;">
                <h1 style="font-size: 4rem;">⚔️</h1>
                <h2 style="color: #D4AF37;">Joc Solo</h2>
                <p>O experiență personală în lumea Valahiei. Tu controlezi povestea complet.</p>
                <p><i>Perfect pentru aventuri individuale.</i></p>
            </div>
            """, unsafe_allow_html=True)

            st.button("🎯 Joacă Solo", key="solo_mode", use_container_width=True, type="primary", on_click=select_solo_mode)

        with col2:
            st.markdown("""
            <div style="background: rgba(20, 15, 8, 0.95); border: 2px solid #5a3921; border-radius: 16px; padding: 32px; text-align: center; min-height: 300px;">
                <h1 style="font-size: 4rem;">🏰</h1>
                <h2 style="color: #D4AF37;">Joc în Echipă</h2>
                <p>Colaborează cu 2-4 prieteni. Votați împreună alegerile și împărtășiți povestea.</p>
                <p><i>Împărtășește aventura cu alții!</i></p>
            </div>
            """, unsafe_allow_html=True)

            st.button("🤝 Joacă în Echipă", key="team_mode", use_container_width=True, type="primary", on_click=select_team_mode)

        return

    # Team Mode: Show team lobby or creation
    if st.session_state.game_mode_selected == "team":
        if loading_placeholder:
            loading_placeholder.empty()

        render_team_lobby()
        return

    # Character Creation Flow (Solo Mode)
    # If character class or faction is missing, show the creation wizard and STOP
    user_id = st.session_state.user.user.id
    db_session_id = getattr(st.session_state, 'db_session_id', None)

    # Pass db and user_id so wizard can save state immediately to avoid reset on rerun
    # Pass loading_placeholder so wizard can clear it ONLY when it's ready to render its own UI
    try:
        if not render_character_creation(st.session_state.game_state, db, user_id, db_session_id, loading_placeholder):
            return
    except Exception as e:
        print(f"❌ Error in character creation: {e}")
        st.error(f"Eroare la inițializarea caracterului: {e}")
        if loading_placeholder:
            loading_placeholder.empty()
        return

    # If wizard returns True, it means character creation is complete.
    # We defer clearing the loading screen to the game interface to prevent black screen flashes.
    
    # Story pack loading moved to lazy loading in llm_handler when needed
    # to improve startup performance
    # CSS is now cached to avoid recomputation
    # Team manager imported at startup but instantiated lazily

    render_header()

    # Render Sidebar Layout (Static/Widgets in Main, Stats in Fragment)
    with st.sidebar:
        # 1. Header & Controls (Widgets - must be in main thread)
        def on_name_change_callback(new_name):
            handle_name_change(new_name)
        
        legend_scale = render_sidebar_header_controls(on_name_change_callback)
        st.session_state.legend_scale = legend_scale

        # 2. Stats Placeholder (Updatable and Clearable)
        # We use st.empty() so we can replace the content entirely on updates, preventing duplication
        sidebar_stats_container = st.empty()

        # 3. Footer (Game Management Widgets - must be in main thread)
        render_sidebar_footer(st.session_state.game_state, db, cookie_manager)

    # Render game interface (sidebar stats + main game loop) in a single fragment
    # This ensures no flickering while updating game content and stats
    render_game_interface(cookie_manager, db, sidebar_stats_container, loading_placeholder)

    # Start ambient music automatically when game interface loads
    audio_manager = get_audio_manager()
    if not audio_manager.current_music:
        audio_manager.play_music("calm_ambient")

    # Auto-save game state to database after each interaction
    user_id = st.session_state.user.user.id
    db_session_id = getattr(st.session_state, 'db_session_id', None)
    saved_session_id = db.save_game_state(user_id, st.session_state.game_state, db_session_id)

    if saved_session_id and not db_session_id:
        st.session_state.db_session_id = saved_session_id
        print(f"[SAVE] Created new session: {saved_session_id}")

    # Start image worker
    start_image_worker()

@st.fragment
def render_game_interface(cookie_manager, db, sidebar_stats_container, loading_placeholder):
    """
    Main interface fragment.
    Updates the Game Loop (Main Area) and Sidebar Stats (via passed container).
    """
    # 1. Update Sidebar Stats (Initial Render in Fragment)
    # Use .container() context on the placeholder to group elements and replace previous content
    with sidebar_stats_container.container():
        render_sidebar_stats(st.session_state.game_state)
        
    # 2. Render Main Game Loop (Passing sidebar container for updates)
    game_loop_logic(sidebar_stats_container)

    # Clear loading screen smoothly ONLY if it was shown (initial load)
    if not st.session_state.get("loading_cleared"):
        time.sleep(1.0) 
        loading_placeholder.empty()
        st.session_state.loading_cleared = True
    else:
        # Ensure it's empty on reruns without delay
        loading_placeholder.empty()

def game_loop_logic(sidebar_stats_container):
    """Main game loop rendering logic"""
    # Main layout
    col_left, col_center, col_right = st.columns([0.5, 4, 0.5])
    
    with col_center:
        # Create placeholders for dynamic updates without rerun
        story_placeholder = st.empty()
        input_placeholder = st.empty()
        
        # Initial render of the story
        with story_placeholder.container():
            display_story(st.session_state.game_state.story)

        # Handle player input
        # Pass containers to allow in-place updates of Story, Sidebar, and Inputs
        handle_player_input(
            story_placeholder=story_placeholder,
            sidebar_container=sidebar_stats_container,
            input_placeholder=input_placeholder
        )

def start_image_worker():
    """Start image generation worker"""
    print(f"[IMAGE] start_image_worker called. Queue: {len(st.session_state.image_queue) if st.session_state.image_queue else 0}, Active: {st.session_state.get('image_worker_active', False)}")
    if st.session_state.image_queue and not st.session_state.get("image_worker_active"):
        print("[IMAGE] Starting image worker thread")
        st.session_state.image_worker_active = True
        t = threading.Thread(target=background_image_gen, daemon=True)
        add_script_run_ctx(t)
        t.start()
    else:
        print("[IMAGE] Image worker not started - no queue or already active")

def background_image_gen():
    """Generate images in background"""
    print(f"[IMAGE] background_image_gen started. Queue size: {len(st.session_state.image_queue) if st.session_state.image_queue else 0}")
    from image_handler import generate_scene_image
    try:
        if not st.session_state.image_queue:
            print("[IMAGE] No images in queue")
            return

        text, turn = st.session_state.image_queue.pop(0)
        print(f"[IMAGE] Processing image for turn {turn}: {text}...")
        location = st.session_state.character.get("location", "Târgoviște")
        img_bytes = generate_scene_image(text, is_initial=False)

        if img_bytes:
            print(f"[IMAGE] Image generated successfully ({len(img_bytes)} bytes)")
            # Attach image to correct story message
            for i in range(len(st.session_state.story) - 1, -1, -1):
                msg = st.session_state.story[i]
                if msg.get("turn") == turn and msg["role"] == "ai":
                    st.session_state.story[i]["image"] = img_bytes
                    print(f"✅ Imagine atașată la turul {turn}")
                    break
        else:
            print(f"[IMAGE] Image generation returned None")
    except Exception as e:
        print(f"❌ BG image error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        st.session_state.image_worker_active = False
        print("[IMAGE] background_image_gen finished")

def handle_player_input(story_placeholder=None, sidebar_container=None, input_placeholder=None):
    """Handle player input and update game state"""

    # Helper to render the input form logic (Reused for initial render and updates)
    def render_input_form():
        if input_placeholder:
            container = input_placeholder.container()
        else:
            container = st.container()
            
        with container:
            # 1. Display Clickable Suggestions
            last_msg = st.session_state.game_state.story[-1] if st.session_state.game_state.story else None
            suggestion_clicked = None
            
            # Try to retrieve suggestions from metadata or parse
            suggestions_list = last_msg.get("suggestions", []) if last_msg else []
            
            # Fallback parsing if metadata missing
            if not suggestions_list and last_msg and "SUGESTII:" in last_msg.get("text", "").replace("**Sugestii:**", "SUGESTII:"):
                try:
                    parts = last_msg["text"].replace("**Sugestii:**", "SUGESTII:").split("SUGESTII:")
                    if len(parts) > 1:
                        raw_sugs = parts[1].strip().split("\n")
                        for s in raw_sugs:
                            clean_s = s.strip().lstrip("•").lstrip("-").strip()
                            if clean_s:
                                suggestions_list.append(clean_s)
                except:
                    pass

            if suggestions_list:
                st.markdown("##### 💡 Sugestii Rapide:")
                if len(suggestions_list) > 3:
                    suggestions_list = suggestions_list[:3]
                    
                cols = st.columns(len(suggestions_list))
                for idx, sug in enumerate(suggestions_list):
                    if cols[idx].button(sug, key=f"sug_{idx}_{st.session_state.game_state.turn}", use_container_width=True):
                        suggestion_clicked = sug

            # Input form
            with st.form(key=f"action_form_{st.session_state.game_state.turn}", clear_on_submit=True):
                user_action = st.text_input(
                    "✍️ Sau scrie propria ta acțiune...",
                    placeholder="Scrie acțiunea ta...",
                    key=f"input_action_{st.session_state.game_state.turn}",
                )
                
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    submitted = st.form_submit_button(
                        "⚔️ Continuă Aventura", use_container_width=True
                    )
                with c2:
                    dice_clicked = st.form_submit_button(
                        "🎲 Aruncă Zaruri", use_container_width=True
                    )
                with c3:
                    heal_clicked = st.form_submit_button(
                        "🏥 Vindecă", use_container_width=True
                    )
            
            return suggestion_clicked, submitted, user_action, dice_clicked, heal_clicked

    # Initial Render of the form
    suggestion_clicked, submitted, user_action, dice_clicked, heal_clicked = render_input_form()

    # Handle Action Logic
    final_action = None
    if suggestion_clicked:
        final_action = suggestion_clicked
    elif submitted and user_action and user_action.strip():
        final_action = user_action

    # Process main action
    if final_action:
        user_action = final_action # Normalize

        if st.session_state.is_generating:
            st.warning("⏳ Așteaptă finalizarea generării...")
            return

        st.session_state.is_generating = True
        try:
            # Add user action to story
            current_turn = st.session_state.game_state.turn
            st.session_state.game_state.story.append({
                "role": "user",
                "text": user_action,
                "turn": current_turn,
                "image": None
            })

            # Update UI immediately to show user input before generation
            if story_placeholder:
                with story_placeholder.container():
                    display_story(st.session_state.game_state.story)

            # Prepare data
            legend_scale = st.session_state.get("legend_scale", 5)
            gs_data = st.session_state.game_state

            if hasattr(gs_data, 'character'):
                character_data = gs_data.character.model_dump()
                story_data = gs_data.story
            else:
                character_data = gs_data['character']
                story_data = gs_data['story']

            # Generate prompt
            game_mode = gs_data.character.game_mode
            current_episode = gs_data.character.current_episode

            # IMPORTANT: use mode='json' to match generator script hash calculation
            full_prompt_text = Config.build_dnd_prompt(
                story=story_data,
                character=gs_data.character.model_dump(mode='json'),
                legend_scale=legend_scale,
                game_mode=game_mode,
                current_episode=current_episode,
                story_summary=gs_data.story_summary
            )

            # Generate narrative with lazy story pack loading
            response = generate_narrative_with_progress(
                full_prompt_text,
                character_class=gs_data.character.character_class,
                faction=gs_data.character.faction,
                episode=gs_data.character.current_episode
            )

            # Process response
            corrected_narrative = fix_romanian_grammar(response.narrative)
            corrected_suggestions = [
                fix_romanian_grammar(s) for s in response.suggestions
                if s and len(s) > 5
            ]

            # Add suggestions to narrative
            narrative_with_suggestions = corrected_narrative

            # Update game state
            gs = st.session_state.game_state
            
            # Update summary if provided
            if response.new_summary:
                gs.story_summary = response.new_summary
            elif getattr(response, 'event_summary', None):
                # Append partial summary from cache
                if gs.story_summary:
                     gs.story_summary += f"\n\n{response.event_summary}"
                else:
                     gs.story_summary = response.event_summary

            gs.character.health = max(0, min(100, gs.character.health + (response.health_change or 0)))
            gs.character.reputation = max(0, min(100, gs.character.reputation + (response.reputation_change or 0)))
            gs.character.gold = max(0, gs.character.gold + (response.gold_change or 0))

            # Update inventory
            for item in response.items_gained or []:
                existing = next((i for i in gs.inventory if i.name == item.name), None)
                if existing:
                    existing.quantity += item.quantity
                else:
                    gs.inventory.append(item)
            gs.inventory = [i for i in gs.inventory if i.name not in (response.items_lost or [])]

            # Update location
            if response.location_change:
                gs.character.location = response.location_change
                st.toast(f"📍 Locație nouă: {response.location_change}", icon="🗺️")

            # Add status effects
            if response.status_effects:
                gs.character.status_effects.extend(response.status_effects)

            # Handle Episode Progress
            next_episode_data = None
            if response.episode_progress is not None:
                gs.character.episode_progress = response.episode_progress

                # Check for episode completion
                if gs.character.episode_progress >= 1.0 and gs.character.game_mode == "Campanie: Pecetea Drăculeștilor":
                    gs.character.current_episode += 1
                    gs.character.episode_progress = 0.0
                    st.toast(f"🎉 Episod Complet! Începe Episodul {gs.character.current_episode}", icon="📜")

                    from campaign import CAMPAIGN_EPISODES
                    next_episode_data = CAMPAIGN_EPISODES.get(gs.character.current_episode)

            # Add AI response to story
            st.session_state.game_state.story.append({
                "role": "ai",
                "text": narrative_with_suggestions,
                "turn": current_turn,
                "image": None,
                "suggestions": corrected_suggestions
            })

            # Process audio context from LLM response
            audio_manager = get_audio_manager()
            audio_context = response.audio_context or []
            music_context = response.music_context

            if audio_context or music_context:
                audio_manager.process_audio_context(audio_context, music_context)
                print(f"[AUDIO] Processed audio context: SFX={audio_context}, Music={music_context}")

            # Append Episode Intro if triggered
            if next_episode_data:
                st.session_state.game_state.story.append({
                    "role": "ai",
                    "text": "", # Rendered via UI component
                    "turn": current_turn,
                    "image": None,
                    "type": "episode_intro",
                    "content_data": next_episode_data,
                    "suggestions": next_episode_data.get("initial_suggestions", [])
                })

            # Queue image generation - skip if error message or first turn
            error_message = "**🔒 Serviciul de Narare este Momentan Indisponibil**"
            if error_message not in corrected_narrative and current_turn > 0 and (current_turn - st.session_state.last_image_turn) >= Config.IMAGE_INTERVAL:
                print(f"[IMAGE] Queueing image for turn {current_turn} (last_image_turn: {st.session_state.last_image_turn})")
                st.session_state.image_queue.append((corrected_narrative, current_turn))
                st.session_state.last_image_turn = current_turn
                # Start image worker after queuing
                start_image_worker()



            # Update turn
            gs.turn += 1
            if response.game_over or gs.character.health <= 0:
                st.error("💀 **Aventura s-a încheiat.**")
                st.session_state.is_game_over = True

            # Save game state immediately to ensure persistence
            user_id = st.session_state.user.user.id
            current_sid = st.session_state.get("db_session_id")
            new_sid = db.save_game_state(user_id, gs, current_sid)
            if new_sid and new_sid != current_sid:
                st.session_state.db_session_id = new_sid

            # MANUAL UPDATE: Refresh UI without st.rerun() to avoid flicker

            # 1. Update Story with AI response
            if story_placeholder:
                with story_placeholder.container():
                    display_story(st.session_state.game_state.story)

            # 2. Update Sidebar Stats
            if sidebar_container:
                with sidebar_container.container():
                    render_sidebar_stats(st.session_state.game_state)

            # 3. Update Input Form (New Suggestions)
            # Clear previous content explicitly to avoid duplication
            if input_placeholder:
                 input_placeholder.empty()
            render_input_form()

        except Exception as e:
            st.error(f"❌ Eroare în procesare: {e}")
            import traceback
            traceback.print_exc()
        finally:
            st.session_state.is_generating = False

    # Handle suggestion clicks separately to avoid duplication issues
    if suggestion_clicked and not final_action:
        # Process suggestion click
        user_action = suggestion_clicked

        if st.session_state.is_generating:
            st.warning("⏳ Așteaptă finalizarea generării...")
            return

        st.session_state.is_generating = True
        try:
            # Add user action to story
            current_turn = st.session_state.game_state.turn
            st.session_state.game_state.story.append({
                "role": "user",
                "text": user_action,
                "turn": current_turn,
                "image": None
            })

            # Prepare data
            legend_scale = st.session_state.get("legend_scale", 5)
            gs_data = st.session_state.game_state

            # Generate prompt
            game_mode = gs_data.character.game_mode
            current_episode = gs_data.character.current_episode

            full_prompt_text = Config.build_dnd_prompt(
                story=gs_data.story,
                character=gs_data.character.model_dump(mode='json'),
                legend_scale=legend_scale,
                game_mode=game_mode,
                current_episode=current_episode,
                story_summary=gs_data.story_summary
            )

            # Generate narrative
            response = generate_narrative_with_progress(
                full_prompt_text,
                character_class=gs_data.character.character_class,
                faction=gs_data.character.faction,
                episode=gs_data.character.current_episode
            )

            # Process response (same as above)
            corrected_narrative = fix_romanian_grammar(response.narrative)
            corrected_suggestions = [
                fix_romanian_grammar(s) for s in response.suggestions
                if s and len(s) > 5
            ]

            narrative_with_suggestions = corrected_narrative

            # Update game state
            gs = st.session_state.game_state
            
            # Update summary if provided
            if response.new_summary:
                gs.story_summary = response.new_summary
            elif getattr(response, 'event_summary', None):
                # Append partial summary from cache
                if gs.story_summary:
                     gs.story_summary += f"\n\n{response.event_summary}"
                else:
                     gs.story_summary = response.event_summary

            gs.character.health = max(0, min(100, gs.character.health + (response.health_change or 0)))
            gs.character.reputation = max(0, min(100, gs.character.reputation + (response.reputation_change or 0)))
            gs.character.gold = max(0, gs.character.gold + (response.gold_change or 0))

            for item in response.items_gained or []:
                existing = next((i for i in gs.inventory if i.name == item.name), None)
                if existing:
                    existing.quantity += item.quantity
                else:
                    gs.inventory.append(item)
            gs.inventory = [i for i in gs.inventory if i.name not in (response.items_lost or [])]

            if response.location_change:
                gs.character.location = response.location_change
                st.toast(f"📍 Locație nouă: {response.location_change}", icon="🗺️")

            if response.status_effects:
                gs.character.status_effects.extend(response.status_effects)

            next_episode_data = None
            if response.episode_progress is not None:
                gs.character.episode_progress = response.episode_progress
                if gs.character.episode_progress >= 1.0 and gs.character.game_mode == "Campanie: Pecetea Drăculeștilor":
                    gs.character.current_episode += 1
                    gs.character.episode_progress = 0.0
                    st.toast(f"🎉 Episod Complet! Începe Episodul {gs.character.current_episode}", icon="📜")

                    from campaign import CAMPAIGN_EPISODES
                    next_episode_data = CAMPAIGN_EPISODES.get(gs.character.current_episode)

            st.session_state.game_state.story.append({
                "role": "ai",
                "text": narrative_with_suggestions,
                "turn": current_turn,
                "image": None,
                "suggestions": corrected_suggestions
            })

            if next_episode_data:
                st.session_state.game_state.story.append({
                    "role": "ai",
                    "text": "",
                    "turn": current_turn,
                    "image": None,
                    "type": "episode_intro",
                    "content_data": next_episode_data,
                    "suggestions": next_episode_data.get("initial_suggestions", [])
                })

            if (current_turn - st.session_state.last_image_turn) >= Config.IMAGE_INTERVAL:
                error_message = "**🔒 Serviciul de Narare este Momentan Indisponibil**"
                if error_message not in corrected_narrative and current_turn > 0:
                    st.session_state.image_queue.append((corrected_narrative, current_turn))
                    st.session_state.last_image_turn = current_turn
                    # Start image worker after queuing
                    start_image_worker()


            gs.turn += 1
            if response.game_over or gs.character.health <= 0:
                st.error("💀 **Aventura s-a încheiat.**")
                st.session_state.is_game_over = True

            user_id = st.session_state.user.user.id
            current_sid = st.session_state.get("db_session_id")
            new_sid = db.save_game_state(user_id, gs, current_sid)
            if new_sid and new_sid != current_sid:
                st.session_state.db_session_id = new_sid

        except Exception as e:
            st.error(f"❌ Eroare în procesare: {e}")
            import traceback
            traceback.print_exc()
        finally:
            st.session_state.is_generating = False

        # UI updates are handled manually above, no need for st.rerun()

    # Handle secondary actions (unchanged)
    elif dice_clicked:
        # D&D Logic: d20 + Power Level
        d20 = random.randint(1, 20)
        bonus = st.session_state.game_state.character.power_level
        total = d20 + bonus
        
        outcome_hint = "(Eșec Critic)" if d20 == 1 else "(Succes Critic)" if d20 == 20 else ""
        user_action = f"🎲 [SISTEM] Jucătorul a aruncat zarul destinului: D20({d20}) + Bonus({bonus}) = {total} {outcome_hint}. Interpretează rezultatul în contextul acțiunii curente."
        
        # Trigger generation loop with this system action via recursive call or logic duplication
        # To avoid duplication, we could structure this better, but for now we let the user re-submit manually 
        # OR we force a rerun to populate the input buffer?
        # Simpler: just rerun, as this is a quick action.
        
        # Actually, let's inject into story and rerun
        st.session_state.game_state.story.append({
            "role": "user",
            "text": user_action,
            "turn": st.session_state.game_state.turn,
            "image": None
        })
        # Note: We rely on the user to interpret this or next turn to use it? 
        # Typically this should trigger AI. 
        # For now, let's just show it.
        if story_placeholder:
             with story_placeholder.container():
                display_story(st.session_state.game_state.story)
        
        # We want the AI to react to the dice roll immediately
        # So we should ideally pass this as 'user_action' to the main block.
        # But 'final_action' logic is above.
        # We can't jump back.
        # St.rerun() is safest here for secondary actions to avoid complexity.
        st.rerun()

    elif heal_clicked:
        gs = st.session_state.game_state
        # Check for healing items
        healing_items = ["Bandaj", "Poțiune de viață", "Hrană", "Pâine", "Mâncare", "Vin"]
        found_item = None
        
        for i, item in enumerate(gs.inventory):
            if item.name in healing_items and item.quantity > 0:
                found_item = item
                break
        
        if found_item:
            # Use item
            heal_amount = random.randint(1, 8) + 4
            gs.character.health = min(100, gs.character.health + heal_amount)
            found_item.quantity -= 1
            if found_item.quantity <= 0:
                gs.inventory.remove(found_item)
            
            st.toast(f"❤️ Ai folosit {found_item.name} și te-ai vindecat cu {heal_amount} puncte!", icon="🩹")
            
            st.session_state.game_state.story.append({
                "role": "user",
                "text": f"*[SISTEM] Am folosit {found_item.name} pentru a mă vindeca.*",
                "turn": gs.turn,
                "image": None
            })
            # Save and update
            user_id = st.session_state.user.user.id
            current_sid = st.session_state.get("db_session_id")
            db.save_game_state(user_id, gs, current_sid)
            
            if story_placeholder:
                with story_placeholder.container():
                    display_story(st.session_state.game_state.story)
            if sidebar_container:
                with sidebar_container:
                    render_sidebar_stats(st.session_state.game_state)
            # No need to regenerate narrative for simple heal
            
        else:
            st.warning("Nu ai obiecte de vindecare!")

def handle_name_change(new_name):
    """Handle character name change logic efficiently"""
    try:
        if not new_name:
            return

        user_id = st.session_state.user.user.id
        print(f"[DEBUG] Attempting to update character name to '{new_name}'")

        # Use direct table operations with upsert
        try:
            db.client.table('user_profiles').upsert({
                'user_id': user_id,
                'character_name': new_name
            }).execute()
        except Exception as upsert_error:
            print(f"[DEBUG] Upsert failed: {upsert_error}")
            # Fallback not strictly needed if DB setup is correct, but safe to have
            try:
                # Check if profile exists
                existing = db.client.table('user_profiles').select('*').eq('user_id', user_id).execute()
                if existing.data:
                    db.client.table('user_profiles').update({'character_name': new_name}).eq('user_id', user_id).execute()
                else:
                    db.client.table('user_profiles').insert({'user_id': user_id, 'character_name': new_name}).execute()
            except Exception as e:
                print(f"[DEBUG] Fallback failed: {e}")

        # Success - update session state
        st.session_state.character_name = new_name
        if "pending_name_change" in st.session_state:
            del st.session_state.pending_name_change
            
        st.success(f"✅ Nume erou schimbat în: {new_name}")
        time.sleep(0.5)
        st.rerun()

    except Exception as e:
        st.error(f"❌ Eroare la schimbarea numelui: {str(e)}")
        if "pending_name_change" in st.session_state:
            del st.session_state.pending_name_change

def render_team_lobby():
    """Render team creation/joining lobby with professional UI and live team list"""
    # Check if team manager is available
    if not TEAM_MANAGER_AVAILABLE:
        st.error("❌ Sistemul de echipe nu este disponibil momentan.")
        return

    # Get team manager instance (already imported at startup)
    from team_manager import TeamManager
    team_manager = TeamManager.get_instance()

    # Get user ID for team operations (unique identifier)
    user_id = st.session_state.user.user.id if st.session_state.user else None
    # Get character name for display purposes
    character_name = db.get_user_character_name(user_id) if user_id else "Jucător"

    # Use placeholder for team list
    teams_placeholder = st.empty()
    
    # Enhanced CSS for team UI
    st.markdown("""
    <style>
    .team-header {
        text-align: center;
        background: linear-gradient(135deg, #1a0f0b 0%, #2a1a15 100%);
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 30px;
        border: 2px solid #D4AF37;
        box-shadow: 0 8px 32px rgba(212, 175, 55, 0.2);
    }
    .team-card {
        background: linear-gradient(145deg, #1E1E1E 0%, #252525 100%);
        border: 2px solid #5a3921;
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }
    .team-card:hover {
        border-color: #D4AF37;
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(212, 175, 55, 0.2);
    }
    .team-card h3 {
        color: #D4AF37 !important;
        margin-bottom: 15px;
        text-align: center;
    }
    .team-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    .team-players {
        background: rgba(212, 175, 55, 0.1);
        border: 1px solid #D4AF37;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin-bottom: 15px;
    }
    .team-status {
        padding: 8px 16px;
        border-radius: 20px;
        text-align: center;
        font-weight: bold;
        font-size: 0.9rem;
        margin-bottom: 15px;
    }
    .status-lobby {
        background: linear-gradient(135deg, #8b4513 0%, #a0522d 100%);
        color: #ffa500;
    }
    .status-full {
        background: linear-gradient(135deg, #2d5016 0%, #4a7c2a 100%);
        color: #90EE90;
    }
    .create-team-section {
        background: rgba(26, 15, 11, 0.9);
        border: 2px solid #5a3921;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 30px;
        text-align: center;
    }
    .no-teams {
        text-align: center;
        color: #8b6b6b;
        font-style: italic;
        padding: 40px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header Layout with Refresh
    col_header, col_refresh = st.columns([3, 1])
    
    with col_header:
        st.markdown("""
        <div class="team-header" style="margin-bottom: 0; padding: 20px;">
            <h1 style="color: #D4AF37; margin: 0; font-size: 2.2rem;">🏰 Sala de Așteptare</h1>
            <p style="color: #8b6b6b; font-size: 1rem; margin: 5px 0 0 0;">Aventura colectivă în Valahia</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_refresh:
        st.markdown('<div style="height: 25px;"></div>', unsafe_allow_html=True) # Vertical alignment
        if st.button("🔄 Actualizează", help="Reîncarcă lista echipelor disponibile", use_container_width=True):
            st.rerun()

    # Check if user is already in a team
    if st.session_state.team_id:
        team_data = team_manager.get_team_data(st.session_state.team_id)
        if team_data:
            # Render team interface (lobby or game)
            render_team_game_interface(team_data, team_manager)
            return
        else:
            st.session_state.team_id = None

    # Create New Team Section
    st.markdown('<div class="create-team-section">', unsafe_allow_html=True)
    st.markdown("### 🆕 Creează Echipă Nouă")

    # Disconnect button if already in a team
    if st.session_state.get('team_id'):
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🚪 Deconectare", key="disconnect_create_team", use_container_width=True, type="secondary"):
                try:
                    team_manager.leave_team(st.session_state.team_id, user_id)
                    del st.session_state.team_id
                    st.success("Ai părăsit echipa!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Eroare la deconectare: {e}")
        with col2:
            st.info("Ești deja într-o echipă. Poți crea una nouă după deconectare.")
    else:
        with st.form("create_team_form"):
            col1, col2 = st.columns([2, 1])
            with col1:
                team_name = st.text_input(
                    "Nume Echipă",
                    placeholder="Ex: Dragonii Valahiei",
                    help="Alege un nume unic pentru echipa ta"
                )
                max_players = st.selectbox(
                    "Număr Maxim Jucători",
                    [2, 3, 4],
                    index=1,
                    help="Numărul maxim de jucători în echipă"
                )
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                create_submitted = st.form_submit_button("🚀 Creează Echipă", type="primary", use_container_width=True)

        if create_submitted:
            if not team_name.strip():
                st.error("❌ Te rog introdu un nume pentru echipă!")
            else:
                try:
                    team_id = team_manager.create_team(user_id, character_name, max_players, team_name.strip())
                    st.session_state.team_id = team_id
                    st.success(f"✅ Echipă '{team_name.strip()}' creată! ID: {team_id}")

                    # Force a rerun to immediately show the created team
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Eroare la crearea echipei: {str(e)}")

    st.markdown('</div>', unsafe_allow_html=True)

    # Render teams
    with teams_placeholder.container():
        # Get all available teams (excluding teams the user is already in)
        all_teams = team_manager.get_all_teams(exclude_user_id=user_id)

        if not all_teams:
            st.markdown("""
            <div class="no-teams">
                <h3 style="color: #D4AF37; margin-bottom: 15px;">🏰 Nicio Echipă Disponibilă</h3>
                <p>Fii primul care creează o echipă pentru a începe aventura colectivă!</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("### 🎯 Echipe Disponibile")
            st.markdown(f"<p style='text-align: center; color: #8b6b6b; margin-bottom: 20px;'>S-au găsit {len(all_teams)} echipă(e) activă(e)</p>", unsafe_allow_html=True)

            # Display teams in a responsive grid
            teams_list = list(all_teams.items())
            for i in range(0, len(teams_list), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(teams_list):
                        team_id, team_data = teams_list[i + j]
                        with cols[j]:
                            render_team_card(team_id, team_data, team_manager, character_name)

    # End render

def render_team_card(team_id: str, team_data: Dict, team_manager, character_name: str):
    """Render individual team card"""
    players = team_data.get('players', {})
    max_players = team_data.get('maxPlayers', 4)
    current_players = len(players)
    team_name = team_data.get('teamName', f"Echipa {team_id}")

    # Get current user info
    user_id = st.session_state.user.user.id if st.session_state.user else None

    # Determine status
    if current_players >= max_players:
        status_class = "status-full"
        status_text = "📦 Plină"
        can_join = False
    else:
        status_class = "status-lobby"
        status_text = "⏳ În așteptare"
        can_join = True

    # Check if user is already in this team by user ID - more robust check
    user_in_team = False
    if user_id:
        # Check if user_id exists as a key in players dict (primary check)
        if user_id in players:
            user_in_team = True
        else:
            # Fallback: check if any player has matching userId (secondary check)
            user_in_team = any(player.get('userId') == user_id for player in players.values())

    # Also check if user is currently in a team (session state)
    user_current_team_id = st.session_state.get('team_id')
    if user_current_team_id == team_id:
        user_in_team = True

    st.markdown(f"""
    <div class="team-card">
        <div class="team-info">
            <h3>🏰 {team_name}</h3>
            <div class="team-status {status_class}">{status_text}</div>
        </div>
        <div class="team-players">
            <strong>👥 Jucători: {current_players}/{max_players}</strong>
        </div>
    """, unsafe_allow_html=True)

    # Show team ID for reference
    st.markdown(f"<small style='color: #666;'>ID: {team_id}</small>", unsafe_allow_html=True)

    # Show player list with character names - prioritize database lookup
    if players:
        player_names = []
        for player in players.values():
            player_user_id = player.get('userId')
            display_name = 'Necunoscut'

            # Always try database lookup first for fresh names
            if player_user_id:
                try:
                    db_name = db.get_user_character_name(player_user_id)
                    if db_name and db_name not in [None, 'Aventurier']:
                        display_name = db_name
                        # Update Firebase with correct name for future use
                        current_firebase_name = player.get('username', '')
                        if current_firebase_name != display_name:
                            try:
                                team_manager.update_player_name(team_id, player_user_id, display_name)
                            except Exception as e:
                                print(f"[TEAM] Failed to update Firebase name: {e}")
                    else:
                        # Database failed, use Firebase as fallback
                        display_name = player.get('username', 'Necunoscut')
                except Exception as e:
                    print(f"[TEAM] Database lookup failed for {player_user_id}: {e}")
                    display_name = player.get('username', 'Necunoscut')

            # If it's the current user, ensure we show the correct name
            if player_user_id == user_id:
                # For current user, prioritize session state
                if hasattr(st, 'session_state') and st.session_state.get('character_name'):
                    display_name = st.session_state.character_name
                player_names.append(f"{display_name} (Tu)")
            else:
                player_names.append(display_name)
        st.markdown(f"<small style='color: #888;'>Membri: {', '.join(player_names)}</small>", unsafe_allow_html=True)

    # Join button
    if user_in_team:
        st.success("✅ Ești deja în această echipă!")
    elif can_join:
        if st.button(f"🤝 Alătură-te", key=f"join_{team_id}", use_container_width=True):
            try:
                success = team_manager.join_team(team_id, user_id, character_name)
                if success:
                    st.session_state.team_id = team_id
                    st.success("✅ Te-ai alăturat echipei!")
                    # No rerun needed - UI will update automatically
                else:
                    st.error("❌ Nu s-a putut alătura echipei.")
            except Exception as e:
                st.error(f"❌ Eroare: {str(e)}")
    else:
        st.info("⚠️ Echipa este plină")

    st.markdown('</div>', unsafe_allow_html=True)

def render_team_game_interface(team_data, team_manager):
    """Render team game interface"""
    team_name = team_data.get('teamName', f"Echipa {team_data['teamId']}")
    st.markdown(f"<h2 style='text-align: center;'>🎮 Joc în Echipă: {team_name}</h2>", unsafe_allow_html=True)

    phase = team_data.get('metadata', {}).get('phase', 'lobby')

    if phase == 'lobby':
        render_team_lobby_interface(team_data, team_manager)
    elif phase in ['in_progress', 'waiting_vote']:
        render_team_gameplay_interface(team_data, team_manager)
    elif phase == 'ai_generating':
        st.info("🤖 AI-ul generează povestea... Așteptați.")
        st.button("🔄 Reîmprospătează", on_click=st.rerun)

@st.fragment(run_every=5)
def render_team_lobby_interface(team_data, team_manager):
    """Render team lobby where players select characters with professional UI"""
    # Fetch fresh data for auto-refresh
    fresh_data = team_manager.get_team_data(team_data['teamId'])
    if fresh_data:
        team_data = fresh_data
        
    players = team_data.get('players', {})

    # Get current user info
    current_user_id = st.session_state.user.user.id if st.session_state.user else None
    current_username = db.get_user_character_name(current_user_id) if current_user_id else "Jucător"

    # Enhanced player display
    st.markdown("### 👥 Membrii Echipei")
    cols = st.columns(min(len(players), 4))

    all_ready = True
    for i, (player_id, player) in enumerate(players.items()):
        with cols[i % len(cols)]:
            # Player card with enhanced styling
            status_class = "status-ready" if player.get('ready') else "status-waiting"
            status_text = "✅ Gata" if player.get('ready') else "⏳ Se pregătește"
            status_emoji = "🛡️" if player.get('ready') else "⚔️"

            # Show character name and "(Tu)" indicator for current user
            display_name = player['username']
            if player.get('userId') == current_user_id:
                display_name += " (Tu)"

            st.markdown(f"""
            <div class="team-card">
                <div class="player-avatar">
                    <div class="avatar">{status_emoji}</div>
                    <h4 style="color: #D4AF37; margin: 10px 0;">{display_name}</h4>
                </div>
                <div class="player-status {status_class}">
                    {status_text}
                </div>
                {"<p style='color: #888; margin-top: 10px;'>Clasă: " + player.get('characterType', 'Neselectat') + "</p>" if player.get('characterType') else ""}
                {"<p style='color: #888;'>Facțiune: " + player.get('faction', 'Neselectat') + "</p>" if player.get('faction') else ""}
            </div>
            """, unsafe_allow_html=True)

            if not player.get('ready'):
                all_ready = False

    # Character Selection Section for Current User
    if current_user_id:
        current_player = players.get(current_user_id)
        if current_player:
            has_character = bool(current_player.get('characterType'))
            has_faction = bool(current_player.get('faction'))
            is_ready = current_player.get('ready', False)

            if not has_character or not has_faction:
                st.markdown("---")
                st.markdown("### ⚔️ Alege-ți Personajul")

                if not has_character:
                    st.markdown("**Pasul 1: Alege Clasa Caracterului**")
                    from character_creation import CHARACTER_CLASSES, AVAILABLE_CLASSES

                    char_cols = st.columns(2)
                    for idx, cls_type in enumerate(AVAILABLE_CLASSES):
                        data = CHARACTER_CLASSES[cls_type]
                        with char_cols[idx % 2]:
                            with st.container():
                                st.markdown(f"""
                                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px;">
                                    <h4 style="color: #D4AF37; margin: 0;">{data['icon']} {cls_type.value}</h4>
                                    <p style="font-size: 0.9em; color: #ccc; margin: 5px 0;"><i>{data['description']}</i></p>
                                    <p style="font-size: 0.8em; color: #888;">{data['special_ability']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Use callback to avoid double reload
                                def on_select_class(tid, uid, ctype, fact):
                                    team_manager.update_player_info(tid, uid, ctype, fact)

                                st.button(
                                    f"Alege {cls_type.value}", 
                                    key=f"team_cls_{cls_type.value}", 
                                    use_container_width=True,
                                    on_click=on_select_class,
                                    args=(team_data['teamId'], current_user_id, cls_type.value, current_player.get('faction', ''))
                                )

                elif not has_faction:
                    st.markdown("**Pasul 2: Alege Facțiunea**")
                    from character_creation import FACTIONS, AVAILABLE_FACTIONS

                    for fac_type in AVAILABLE_FACTIONS:
                        data = FACTIONS[fac_type]
                        st.markdown(f"""
                        <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 15px;">
                            <h4 style="color: #D4AF37; margin: 0;">{data['icon']} {fac_type.value}</h4>
                            <p style="font-style: italic; color: #f0e68c; margin: 5px 0;"><strong>"{data.get('motto', '')}"</strong></p>
                            <p style="color: #ccc; margin: 5px 0;">📍 {data.get('location', '')}</p>
                            <p style="color: #aaa; margin: 10px 0;">{data['description'][:200]}...</p>
                            <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 5px; margin-top: 10px;">
                                <p style="color: #90ee90; margin: 2px 0;">✅ {data['bonuses']}</p>
                                <p style="color: #ffd700; margin: 2px 0;">✨ {data['passive']}</p>
                                <p style="color: #ff6b6b; margin: 2px 0;">⚠️ {data['disadvantage']}</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        def on_select_faction(tid, uid, ctype, fact):
                            team_manager.update_player_info(tid, uid, ctype, fact)

                        st.button(
                            f"🛡️ Alătură-te: {fac_type.value}", 
                            key=f"team_fac_{fac_type.value}", 
                            use_container_width=True, 
                            type="primary",
                            on_click=on_select_faction,
                            args=(team_data['teamId'], current_user_id, current_player.get('characterType', ''), fac_type.value)
                        )

                # Ready button when both selected
                if has_character and has_faction and not is_ready:
                    st.markdown("---")
                    
                    def on_ready(tid, uid):
                        team_manager.set_player_ready(tid, uid, True)

                    st.button(
                        "🚀 Sunt Gata!", 
                        key="team_ready", 
                        use_container_width=True, 
                        type="primary",
                        on_click=on_ready,
                        args=(team_data['teamId'], current_user_id)
                    )

                elif is_ready:
                    st.success("✅ Ești gata! Poți să te răzgândești apăsând butonul de mai jos.")
                    
                    def on_unready(tid, uid):
                        team_manager.set_player_ready(tid, uid, False)

                    st.button(
                        "🔄 Nu sunt gata încă", 
                        key="team_unready", 
                        use_container_width=True,
                        on_click=on_unready,
                        args=(team_data['teamId'], current_user_id)
                    )



    # Disconnect button for team lobby
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🚪 Deconectare", key="disconnect_team_lobby", use_container_width=True, type="secondary"):
            try:
                team_manager.leave_team(team_data['teamId'], current_user_id)
                del st.session_state.team_id
                st.success("Ai părăsit echipa!")
                st.rerun()
            except Exception as e:
                st.error(f"Eroare la deconectare: {e}")

    # Ready check message
    if all_ready and len(players) >= 2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #2d5016 0%, #4a7c2a 100%);
                    border: 2px solid #6bb343; border-radius: 15px; padding: 20px;
                    text-align: center; margin-top: 30px; box-shadow: 0 8px 32px rgba(75, 181, 67, 0.3);">
            <h3 style="color: #90EE90; margin: 0;">🚀 Toți jucătorii sunt gata!</h3>
            <p style="color: #e0ffe0; margin: 10px 0 0 0;">Jocul va începe automat în curând...</p>
        </div>
        """, unsafe_allow_html=True)
    elif len(players) < 2:
        st.warning("👥 Mai ai nevoie de cel puțin încă un jucător pentru a începe aventura!")
    else:
        ready_count = sum(1 for p in players.values() if p.get('ready'))
        st.info(f"⏳ Așteptăm ca toți jucătorii să fie gata... ({ready_count}/{len(players)})")

@st.fragment(run_every=5)
def render_team_gameplay_interface(team_data, team_manager):
    """Render team gameplay with shared story and voting with professional UI"""
    # Fetch fresh data
    fresh_data = team_manager.get_team_data(team_data['teamId'])
    if fresh_data:
        team_data = fresh_data
        
    game_state = team_data.get('gameState', {})

    # Enhanced CSS for gameplay UI
    st.markdown("""
    <style>
    .story-container {
        background: linear-gradient(145deg, #1a0f0b 0%, #2a1a15 100%);
        border: 2px solid #D4AF37;
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 30px;
        box-shadow: 0 8px 32px rgba(212, 175, 55, 0.2);
    }
    .story-header {
        color: #D4AF37;
        font-size: 1.8rem;
        margin-bottom: 20px;
        text-align: center;
        border-bottom: 1px solid #5a3921;
        padding-bottom: 10px;
    }
    .story-text {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        line-height: 1.6;
        color: #e0e0e0;
        border: 1px solid #5a3921;
    }
    .voting-container {
        background: linear-gradient(145deg, #1E1E1E 0%, #252525 100%);
        border: 2px solid #8b4513;
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 16px rgba(139, 69, 19, 0.3);
    }
    .voting-header {
        color: #ff6b35;
        font-size: 1.6rem;
        margin-bottom: 20px;
        text-align: center;
        border-bottom: 1px solid #8b4513;
        padding-bottom: 10px;
    }
    .vote-button {
        background: linear-gradient(135deg, #2d5016 0%, #4a7c2a 100%);
        color: white;
        border: 2px solid #4a7c2a;
        border-radius: 12px;
        padding: 15px 25px;
        margin: 10px;
        font-size: 1.1rem;
        font-weight: bold;
        transition: all 0.3s ease;
        cursor: pointer;
        min-height: 60px;
        display: inline-block;
        text-align: center;
        box-shadow: 0 4px 12px rgba(74, 124, 42, 0.3);
    }
    .vote-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(74, 124, 42, 0.4);
        background: linear-gradient(135deg, #4a7c2a 0%, #6bb343 100%);
    }
    .vote-result {
        background: linear-gradient(135deg, #8b4513 0%, #a0522d 100%);
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
        text-align: center;
        font-weight: bold;
        color: #ffe4b5;
        border: 1px solid #daa520;
    }
    .vote-count {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 8px 16px;
        margin: 5px;
        display: inline-block;
        border: 1px solid #5a3921;
    }
    .refresh-button {
        background: linear-gradient(135deg, #4169e1 0%, #6495ed 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-size: 1rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(65, 105, 225, 0.3);
    }
    .refresh-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(65, 105, 225, 0.4);
    }
    .team-info {
        background: rgba(212, 175, 55, 0.1);
        border: 1px solid #D4AF37;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # Team info header
    players = team_data.get('players', {})
    total_players = len(players)
    ready_count = sum(1 for p in players.values() if p.get('ready'))
    team_name = team_data.get('teamName', f"Echipa {team_data['teamId']}")
    st.markdown(f"""
    <div class="team-info">
        <h3 style="color: #D4AF37; margin: 0;">🎮 Joc în Echipă: {team_name}</h3>
        <p style="margin: 5px 0 0 0; color: #b8860b;">{total_players} jucători • {ready_count} gata</p>
    </div>
    """, unsafe_allow_html=True)

    # Display shared story
    if game_state.get('aiResponse'):
        st.markdown('<div class="story-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="story-header">📖 Povestea Comună</h3>', unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f'<div class="story-text">{game_state["aiResponse"]}</div>', unsafe_allow_html=True)

        with col2:
            if game_state.get('aiImageUrl'):
                st.image(game_state['aiImageUrl'], caption="Imaginea scenei", use_column_width=True)
            else:
                st.markdown("""
                <div style="text-align: center; padding: 20px; color: #888;">
                    <div style="font-size: 3rem;">🎨</div>
                    <p>Imaginea se încarcă...</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Voting interface
    choices = game_state.get('choices', {})
    if choices:
        st.markdown('<div class="voting-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="voting-header">🗳️ Votare Colectivă</h3>', unsafe_allow_html=True)

        username = st.session_state.character_name
        votes = game_state.get('votes', {})

        if username not in votes:
            st.markdown('<p style="text-align: center; color: #ffe4b5; margin-bottom: 20px;">**Alege o opțiune pentru echipă:**</p>', unsafe_allow_html=True)

            # Create voting buttons in a grid
            cols = st.columns(min(len(choices), 2))
            choice_items = list(choices.items())

            for i, (choice_id, choice_data) in enumerate(choice_items):
                col_idx = i % len(cols)
                with cols[col_idx]:
                    if st.button(
                        f"🗳️ {choice_data['label']}",
                        key=f"vote_{choice_id}",
                        help=f"Votează pentru: {choice_data['label']}",
                        use_container_width=True
                    ):
                        team_manager.vote_choice(st.session_state.team_id, username, choice_id)
                        st.rerun()
        else:
            voted_choice = votes[username]
            choice_label = choices.get(voted_choice, {}).get('label', 'Necunoscut')
            st.markdown(f'<div class="vote-result">✅ Ai votat pentru: <strong>{choice_label}</strong></div>', unsafe_allow_html=True)

        # Show vote counts with progress bars
        st.markdown('<h4 style="text-align: center; color: #daa520; margin: 25px 0 15px 0;">📊 Rezultate Votare</h4>', unsafe_allow_html=True)

        vote_counts = {}
        for vote in votes.values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1

        total_votes = len(votes)

        for choice_id, choice_data in choices.items():
            count = vote_counts.get(choice_id, 0)
            percentage = (count / max(total_votes, 1)) * 100

            st.markdown(f"""
            <div style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="color: #e0e0e0; font-weight: bold;">{choice_data['label']}</span>
                    <span style="color: #daa520; font-weight: bold;">{count}/{total_votes} voturi</span>
                </div>
                <div style="background: rgba(255,255,255,0.1); border-radius: 10px; height: 20px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #4a7c2a 0%, #6bb343 100%);
                               width: {percentage}%; height: 100%; border-radius: 10px; transition: width 0.5s ease;">
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Waiting message
        if total_votes < total_players:
            st.markdown(f"""
            <div style="text-align: center; color: #ffa500; margin-top: 20px; padding: 15px; background: rgba(255,165,0,0.1); border-radius: 10px; border: 1px solid #ffa500;">
                ⏳ Așteptăm voturile tuturor jucătorilor... ({total_votes}/{total_players})
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Disconnect and Refresh buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🚪 Deconectare", key="disconnect_team", use_container_width=True, type="secondary"):
            try:
                team_manager.leave_team(st.session_state.team_id, st.session_state.user.user.id)
                del st.session_state.team_id
                st.success("Ai părăsit echipa!")
                st.rerun()
            except Exception as e:
                st.error(f"Eroare la deconectare: {e}")
    with col2:
        if st.button("🔄 Reîmprospătează", key="refresh_team", use_container_width=True):
            st.rerun()

if __name__ == "__main__":
    main()
