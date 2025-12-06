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
from llm_handler import fix_romanian_grammar, generate_narrative_with_progress, generate_with_api
from models import GameState, CharacterStats, InventoryItem, ItemType, NarrativeResponse
from database import Database
from character_creation import render_character_creation

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
            InventoryItem(name="5 galbeni", type=ItemType.currency, value=5, quantity=1),
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
            <div style="text-align: center; padding: 30px 0 20px 0;">
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

    # Initialize cookie manager ONCE per run at the top level (Normal flow)
    cookie_manager = get_cookie_manager()

    # UI Stability: Prevent login form flash on first load
    # Note: We already showed a loading screen above, so we can reduce the explicit sleep here or remove the dedicated block
    # But we keep the auth_check logic to ensure cookies sync properly on first load
    if "auth_check_complete" not in st.session_state:
        st.session_state.auth_check_complete = True
        # Allow a brief moment for cookies to be read by the component
        time.sleep(0.5) 
        st.rerun()

    # Check authentication
    if not db.client:
        loading_placeholder.empty() # Clear loading
        st.error("🔧 Sistemul de autentificare nu este configurat!")
        st.info("Adaugă SUPABASE_URL și SUPABASE_ANON_KEY în fișierul .env")
        return

    # Handle authentication FIRST - before any other logic
    user_authenticated = "user" in st.session_state and st.session_state.user is not None

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

    # Initialize session AFTER authentication is confirmed
    init_session()

    # Handle pending name change - Legacy check for safety
    if "pending_name_change" in st.session_state:
        handle_name_change(st.session_state.pending_name_change)

    # Check API fallback
    if st.session_state.settings.get("api_fail_count", 0) > 3:
        st.warning("⚠️ API a eșuat de 3+ ori. Se trece în modul local automat.")
        st.session_state.settings["use_api_fallback"] = False

    # Character Creation Flow
    # If character class or faction is missing, show the creation wizard and STOP
    user_id = st.session_state.user.user.id
    db_session_id = getattr(st.session_state, 'db_session_id', None)
    
    # Pass db and user_id so wizard can save state immediately to avoid reset on rerun
    # Pass loading_placeholder so wizard can clear it ONLY when it's ready to render its own UI
    if not render_character_creation(st.session_state.game_state, db, user_id, db_session_id, loading_placeholder):
        return

    # If wizard returns True, it means character creation is complete.
    # We defer clearing the loading screen to the game interface to prevent black screen flashes.
    
    # Check for Story Packs (Cache Pre-loading)
    try:
        from caching import CacheManager
        gs = st.session_state.game_state
        
        def normalize_name(name):
            if not name: return ""
            # Handle Enums by getting value if possible, otherwise string conversion
            val = name.value if hasattr(name, "value") else str(name)
            return val.lower().replace("ă", "a").replace("â", "a").replace("î", "i").replace("ș", "s").replace("ț", "t").replace(" ", "_").replace("/", "_")

        char_class = normalize_name(gs.character.character_class)
        faction = normalize_name(gs.character.faction)
        episode = gs.character.current_episode
        
        # Ensure we always attempt to load the correct pack for the current configuration
        # NEW STRUCTURE: story_packs/episode_X/class_faction.json
        pack_folder = f"episode_{episode}"
        pack_filename = f"{char_class}_{faction}.json"
        pack_path = os.path.join("story_packs", pack_folder, pack_filename)
        
        # Also attempt to load SOURCE pack for offline fallback (UserText -> Response)
        # Try specific faction source first, then generic class source
        source_filename_specific = f"{char_class}_{faction}_source.json"
        source_filename_generic = f"{char_class}_source.json"
        
        source_path_specific = os.path.join("story_packs", pack_folder, source_filename_specific)
        source_path_generic = os.path.join("story_packs", pack_folder, source_filename_generic)
        
        # Check if we need to switch packs (Episode changed or Class/Faction changed or First load)
        # We use the full path as identifier now
        current_loaded = st.session_state.get("loaded_pack_name")
        
        if current_loaded != pack_path:
            if os.path.exists(pack_path):
                print(f"[PACK] Loading story pack: {pack_path}")
                # Clear previous memory cache to save RAM
                CacheManager.load_pack(pack_path, clear_previous=True)
                st.session_state.loaded_pack_name = pack_path
                
                # Load Source Pack
                if os.path.exists(source_path_specific):
                    CacheManager.load_source_pack(source_path_specific)
                elif os.path.exists(source_path_generic):
                    CacheManager.load_source_pack(source_path_generic)
                    
            else:
                # If no pack exists for this new state, we should probably clear the old pack to avoid confusion?
                # Or keep it? User said "save memory". If we are in Ep 2 and no pack exists, keeping Ep 1 pack is waste.
                if current_loaded:
                    print(f"[PACK] Unloading previous pack (New context has no pack): {current_loaded}")
                    CacheManager.clear_memory()
                    st.session_state.loaded_pack_name = None

    except Exception as e:
        print(f"[PACK] Error checking packs: {e}")

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
    if st.session_state.image_queue and not st.session_state.get("image_worker_active"):
        st.session_state.image_worker_active = True
        t = threading.Thread(target=background_image_gen, daemon=True)
        add_script_run_ctx(t)
        t.start()

def background_image_gen():
    """Generate images in background"""
    from image_handler import generate_scene_image
    try:
        text, turn = st.session_state.image_queue.pop(0)
        location = st.session_state.character.get("location", "Târgoviște")
        img_bytes = generate_scene_image(text, is_initial=False)

        if img_bytes:
            # Attach image to correct story message
            for i in range(len(st.session_state.story) - 1, -1, -1):
                msg = st.session_state.story[i]
                if msg.get("turn") == turn and msg["role"] == "ai":
                    st.session_state.story[i]["image"] = img_bytes
                    print(f"✅ Imagine atașată la turul {turn}")
                    break
    except Exception as e:
        print(f"❌ BG image error: {e}")
    finally:
        st.session_state.image_worker_active = False

def prefetch_suggestions_worker(suggestions, game_state_dump, legend_scale):
    """Background worker to pre-generate responses for suggestions."""
    print(f"[PREFETCH] Starting prefetch for {len(suggestions)} suggestions...")
    
    # Reconstruct necessary data from dump
    try:
        character_data = game_state_dump['character']
        story_data = game_state_dump['story']
        game_mode = character_data.get('game_mode')
        current_episode = character_data.get('current_episode', 1)
        
        for suggestion in suggestions:
            # Simulate the user action appended to story
            simulated_story = story_data + [{
                "role": "user",
                "text": suggestion,
                "turn": game_state_dump['turn'] + 1, # hypothetical turn
                "image": None
            }]
            
            # Build prompt
            prompt = Config.build_dnd_prompt(
                story=simulated_story,
                character=character_data,
                legend_scale=legend_scale,
                game_mode=game_mode,
                current_episode=current_episode
            )
            
            # Call API (will cache result) - Sequential to avoid rate limits
            # We don't need the result here, just the side effect of caching
            print(f"[PREFETCH] Generating for: {suggestion[:30]}...")
            generate_with_api(prompt)
            time.sleep(1) # small delay to be nice to API
            
        print("[PREFETCH] Completed.")
    except Exception as e:
        print(f"[PREFETCH] Error: {e}")

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
                current_episode=current_episode
            )

            # Generate narrative
            response = generate_narrative_with_progress(full_prompt_text)

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

            # Queue image generation
            if (current_turn - st.session_state.last_image_turn) >= Config.IMAGE_INTERVAL:
                st.session_state.image_queue.append((corrected_narrative, current_turn))
                st.session_state.last_image_turn = current_turn

            # TRIGGER PREFETCHING
            if corrected_suggestions:
                try:
                    # Create a snapshot of the CURRENT state (already updated above)
                    # We need to dump it because we can't pass the pydantic object across threads safely if it changes
                    current_gs_dump = st.session_state.game_state.model_dump()

                    t_prefetch = threading.Thread(
                        target=prefetch_suggestions_worker,
                        args=(corrected_suggestions, current_gs_dump, legend_scale),
                        daemon=True
                    )
                    add_script_run_ctx(t_prefetch)
                    t_prefetch.start()
                except Exception as e:
                    print(f"[PREFETCH] Failed to start worker: {e}")

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
                current_episode=current_episode
            )

            # Generate narrative
            response = generate_narrative_with_progress(full_prompt_text)

            # Process response (same as above)
            corrected_narrative = fix_romanian_grammar(response.narrative)
            corrected_suggestions = [
                fix_romanian_grammar(s) for s in response.suggestions
                if s and len(s) > 5
            ]

            narrative_with_suggestions = corrected_narrative

            # Update game state
            gs = st.session_state.game_state
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
                st.session_state.image_queue.append((corrected_narrative, current_turn))
                st.session_state.last_image_turn = current_turn

            if corrected_suggestions:
                try:
                    current_gs_dump = st.session_state.game_state.model_dump()
                    t_prefetch = threading.Thread(
                        target=prefetch_suggestions_worker,
                        args=(corrected_suggestions, current_gs_dump, legend_scale),
                        daemon=True
                    )
                    add_script_run_ctx(t_prefetch)
                    t_prefetch.start()
                except Exception as e:
                    print(f"[PREFETCH] Failed to start worker: {e}")

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

        # For suggestions, use st.rerun() to update UI cleanly and avoid duplication
        st.rerun()

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

if __name__ == "__main__":
    main()
