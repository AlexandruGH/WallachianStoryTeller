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
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Import local modules
from config import Config, ModelRouter
from character import CharacterSheet, roll_dice, update_stats
from ui_components import inject_css, render_header, render_sidebar, display_story
from llm_handler import fix_romanian_grammar, generate_narrative_with_progress
from models import GameState, CharacterStats, InventoryItem, ItemType, NarrativeResponse
from database import Database

# =========================
# — Database Configuration
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
db = Database(SUPABASE_URL, SUPABASE_ANON_KEY)

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
        "*Personaj (TU): Ești un aventurier aflat în anul 1456. Te afli la marginea cetății Târgoviște, pe o noapte rece de toamnă. "
        "Flăcările torțelor dansează în vânt, proiectând umbre lungi pe zidurile masive. "
        "Porțile de stejar se ridică încet, cu un scârțâit apăsat, iar aerul miroase "
        "a fum, fier și pământ ud. În depărtare se aud cai și voci ale străjerilor. "
        "Fiecare decizie poate naște o legendă sau poate rămâne doar o filă de cronică...*\n\n"
    )

    st.session_state.game_state = GameState(
        character=CharacterStats(),
        inventory=[
            InventoryItem(name="Pumnal valah", type=ItemType.weapon, value=3, quantity=1),
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

def handle_oauth_callback():
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

            # Exchange code for session
            session_response = db.client.auth.exchange_code_for_session({
                "auth_code": code,
                "code_verifier": code_verifier
            })

            if session_response and session_response.user:
                user = session_response.user
                st.session_state.user = session_response

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
                            # Use the same approach as sidebar name change
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
def render_auth_page():
    """Authentication page with persistent session handling"""
    st.set_page_config(
        page_title="Wallachia - Intră în Aventură",
        page_icon="⚔️",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    inject_css()

    # Handle OAuth callback FIRST
    if "code" in st.query_params:
        with st.spinner("Procesăm autentificarea..."):
            if handle_oauth_callback():
                return
            else:
                st.error("❌ Autentificarea a eșuat!")

    # Check for existing Supabase session - PERSISTENT ACROSS REFRESHES
    try:
        # For localhost development, we need special handling
        import os
        is_localhost = "localhost" in os.getenv("OAUTH_REDIRECT_URL", "") or not os.getenv("STREAMLIT_SERVER_HEADLESS")

        if is_localhost:
            # Localhost workaround: Check Streamlit session state first
            if "user" in st.session_state and st.session_state.user:
                print(f"[AUTH] ✅ Found user in Streamlit session: {st.session_state.user.user.id}")
                # For localhost, trust Streamlit session state since Supabase localStorage doesn't work well
                # Just ensure character name is loaded
                if "character_name" not in st.session_state:
                    try:
                        character_name = db.get_user_character_name(st.session_state.user.user.id)
                        st.session_state.character_name = character_name
                    except Exception as name_error:
                        print(f"[AUTH] Could not load character name: {name_error}")
                        st.session_state.character_name = "Aventurier"  # fallback
                print(f"[AUTH] ✅ Localhost session restored for: {st.session_state.character_name}")
                st.rerun()
                return

        # Standard Supabase session check
        session = db.client.auth.get_session()
        user_response = db.client.auth.get_user()

        print(f"[AUTH] Session check - session: {session is not None}, user: {user_response is not None}")

        if session and session.user:
            print(f"[AUTH] ✅ Found active session for user: {session.user.id}")
            # Always restore session state on refresh
            st.session_state.user = session
            # Load character name from database
            character_name = db.get_user_character_name(session.user.id)
            st.session_state.character_name = character_name
            print(f"[AUTH] ✅ Session restored for: {character_name}")
            st.rerun()
            return
        elif user_response and user_response.user:
            print(f"[AUTH] ✅ Found user (no active session) for user: {user_response.user.id}")
            # Restore user but session might need refresh
            st.session_state.user = user_response
            character_name = db.get_user_character_name(user_response.user.id)
            st.session_state.character_name = character_name
            print(f"[AUTH] ✅ User restored for: {character_name}")
            st.rerun()
            return
        else:
            print("[AUTH] ❌ No session or user found - login required")
    except Exception as e:
        print(f"[AUTH] ❌ Session check error: {e}")
        import traceback
        traceback.print_exc()

    # If we get here, no valid session was found
    print("[AUTH] 🔄 No valid session - showing login page")

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

    # Check authentication
    if not db.client:
        st.set_page_config(page_title="Wallachia - Config Error", layout="centered")
        st.error("🔧 Sistemul de autentificare nu este configurat!")
        st.info("Adaugă SUPABASE_URL și SUPABASE_ANON_KEY în fișierul .env")
        return

    # Handle authentication FIRST - before any other logic
    user_authenticated = "user" in st.session_state and st.session_state.user is not None

    if not user_authenticated:
        render_auth_page()
        return

    # User is authenticated - start game
    st.set_page_config(
        page_title="Wallachia - D&D Adventure",
        page_icon="⚔️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_css()

    # Initialize session AFTER authentication is confirmed
    init_session()

    # Handle pending name change
    if "pending_name_change" in st.session_state:
        try:
            new_name = st.session_state.pending_name_change
            user_id = st.session_state.user.user.id
            print(f"[DEBUG] Attempting to update character name for user {user_id} to '{new_name}'")

            # Use direct table operations with upsert
            try:
                # Try upsert (insert or update on conflict)
                upsert_result = db.client.table('user_profiles').upsert({
                    'user_id': user_id,
                    'character_name': new_name
                }).execute()
                print(f"[DEBUG] Upsert result: {upsert_result}")

            except Exception as upsert_error:
                print(f"[DEBUG] Upsert failed: {upsert_error}")
                # Fallback: manual check and update/insert
                try:
                    # Check if profile exists
                    existing = db.client.table('user_profiles').select('*').eq('user_id', user_id).execute()

                    if existing.data and len(existing.data) > 0:
                        # Update existing
                        update_result = db.client.table('user_profiles').update({
                            'character_name': new_name
                        }).eq('user_id', user_id).execute()
                        print(f"[DEBUG] Updated existing profile: {len(update_result.data) if update_result.data else 0} rows")
                    else:
                        # Insert new
                        insert_result = db.client.table('user_profiles').insert({
                            'user_id': user_id,
                            'character_name': new_name
                        }).execute()
                        print(f"[DEBUG] Inserted new profile: {len(insert_result.data) if insert_result.data else 0} rows")

                except Exception as table_error:
                    print(f"[DEBUG] Table operation failed: {table_error}")
                    # Final fallback: service role approach
                    try:
                        from supabase import create_client, Client
                        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                        if service_key:
                            service_client = create_client(SUPABASE_URL, service_key)
                            service_client.table('user_profiles').upsert({
                                'user_id': user_id,
                                'character_name': new_name
                            }).execute()
                            print("[DEBUG] Used service role for upsert - SUCCESS")
                        else:
                            raise Exception("No service role key available")
                    except Exception as service_error:
                        print(f"[DEBUG] Service role approach failed: {service_error}")
                        raise Exception(f"All database approaches failed: upsert={upsert_error}, table={table_error}, service={service_error}")

            # Success - update session state
            st.session_state.character_name = new_name
            if "pending_name_change" in st.session_state:
                del st.session_state.pending_name_change
            st.success(f"✅ Nume erou schimbat în: {new_name}")
            print(f"[DEBUG] Character name updated successfully to '{new_name}'")
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Eroare la schimbarea numelui: {str(e)}")
            print(f"[DEBUG] Exception during name change: {e}")
            import traceback
            traceback.print_exc()
            if "pending_name_change" in st.session_state:
                del st.session_state.pending_name_change

    # Check API fallback
    if st.session_state.settings.get("api_fail_count", 0) > 3:
        st.warning("⚠️ API a eșuat de 3+ ori. Se trece în modul local automat.")
        st.session_state.settings["use_api_fallback"] = False

    render_header()

    # Render sidebar and save game state
    legend_scale = render_sidebar(st.session_state.game_state)
    st.session_state.legend_scale = legend_scale

    # Auto-save game state to database after each interaction
    user_id = st.session_state.user.user.id
    db_session_id = getattr(st.session_state, 'db_session_id', None)
    saved_session_id = db.save_game_state(user_id, st.session_state.game_state, db_session_id)

    if saved_session_id and not db_session_id:
        st.session_state.db_session_id = saved_session_id
        print(f"[SAVE] Created new session: {saved_session_id}")

    # Start image worker
    start_image_worker()

    # Main layout
    col_left, col_center, col_right = st.columns([0.5, 4, 0.5])
    with col_center:
        display_story(st.session_state.game_state.story)

    # Handle player input
    handle_player_input()

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

def handle_player_input():
    """Handle player input and update game state"""

    # Game over check
    if st.session_state.game_state.character.health <= 0:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.error("💀 **Ești mort! Aventura s-a încheiat.**")
            if st.button("🔄 Începe o nouă aventură", use_container_width=True):
                # Create fresh game state
                create_new_game_state()
                # Save to database
                user_id = st.session_state.user.user.id
                db_session_id = db.save_game_state(user_id, st.session_state.game_state)
                if db_session_id:
                    st.session_state.db_session_id = db_session_id
                st.rerun()
        return

    col_left, col_centre, col_right = st.columns([0.5, 4, 0.5])
    with col_centre:
        # Input form
        with st.form(key="action_form", clear_on_submit=True):
            user_action = st.text_input(
                "🗡️ Ce vrei să faci?",
                placeholder="Scrie acțiunea ta...",
                key="input_action",
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

        # Process main action
        if submitted and user_action and user_action.strip():
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

                if hasattr(gs_data, 'character'):
                    character_data = gs_data.character.model_dump()
                    story_data = gs_data.story
                else:
                    character_data = gs_data['character']
                    story_data = gs_data['story']

                # Generate prompt
                full_prompt_text = Config.build_dnd_prompt(
                    story=story_data,
                    character=character_data,
                    legend_scale=legend_scale
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
                if corrected_suggestions:
                    narrative_with_suggestions += "\n\n**Sugestii:**"
                    narrative_with_suggestions += "\n".join([f"• {s}" for s in corrected_suggestions])

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

                # Add AI response to story
                st.session_state.game_state.story.append({
                    "role": "ai",
                    "text": narrative_with_suggestions,
                    "turn": current_turn,
                    "image": None
                })

                # Queue image generation
                if (current_turn - st.session_state.last_image_turn) >= Config.IMAGE_INTERVAL:
                    st.session_state.image_queue.append((corrected_narrative, current_turn))
                    st.session_state.last_image_turn = current_turn

                # Update turn
                gs.turn += 1
                if response.game_over or gs.character.health <= 0:
                    st.error("💀 **Aventura s-a încheiat.**")
                    st.session_state.is_game_over = True

                st.rerun()

            except Exception as e:
                st.error(f"❌ Eroare în procesare: {e}")
                import traceback
                traceback.print_exc()
            finally:
                st.session_state.is_generating = False

        # Handle secondary actions
        elif dice_clicked:
            result = roll_dice()
            st.toast(f"🎲 Ai dat: {result}!", icon="⚔️")
            time.sleep(0.5)

        elif heal_clicked:
            gs = st.session_state.game_state
            heal = roll_dice(8) + 5
            gs.character.health = min(100, gs.character.health + heal)
            st.toast(f"❤️ Te-ai vindecat cu {heal} puncte!", icon="✨")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
