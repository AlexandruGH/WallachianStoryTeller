import streamlit as st
from typing import List, Dict, Optional
from io import BytesIO
from PIL import Image
import io
import shutil
import base64
import uuid
import json
import time
from datetime import datetime
import os
import re
import pdfkit
import requests
from models import GameState, CharacterStats, InventoryItem, GameMode
from campaign import get_current_episode
from character_creation import FACTIONS

# Import Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    Client = None

def get_api_token() -> Optional[str]:
    """Obține token-ul din mediu sau Secrets (cloud)."""
    token = os.getenv("HF_TOKEN")
    if token:
        return token
    try:
        if "HF_TOKEN" in st.secrets:
            token = st.secrets["HF_TOKEN"]
            os.environ["HF_TOKEN"] = token
            return token
    except:
        pass
    return None

# =========================
# — CSS Îmbunătățit - Adaugă în ui_components.py
# =========================
def scroll_to_top():
    """Injects JS to scroll to the top of the page"""
    st.components.v1.html(
        "<script>window.scrollTo(0, 0);</script>",
        height=0,
        width=0
    )

def inject_css():
    """CSS medieval - VERSIUNE FINALĂ PENTRU UI/UX PROFESIONAL"""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
        
        /* ================== GLOBAL & SCROLLBAR ================== */
        .stApp {
            background-color: #0d0704;
            background-image: 
                radial-gradient(circle at 50% 0%, #1a0f0b 0%, transparent 70%),
                linear-gradient(135deg, #0a0805 0%, #140b08 100%);
            color: #e8d8c3;
            font-family: 'Crimson Text', serif;
        }

        /* Scrollbar customizat */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #1a0f0b; 
            border-left: 1px solid #3a2516;
        }
        ::-webkit-scrollbar-thumb {
            background: #5a3921; 
            border-radius: 2px;
            border: 1px solid #3a2516;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #7a4f2a; 
        }

        /* ================== HEADER & TITLES ================== */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Cinzel', serif !important;
            color: #d4af37 !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.8);
            letter-spacing: 0.05em;
        }
        
        .main-header {
            font-size: 3.5rem !important;
            background: linear-gradient(to bottom, #ffd700, #b8860b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 0.2em !important;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));
        }
        
        @media (max-width: 600px) {
            .main-header { font-size: 1.8rem !important; }
        }
        
        .subtitle {
            text-align: center;
            color: #8b6b6b !important;
            font-style: italic;
            font-size: 1.2rem;
            margin-bottom: 2rem !important;
            border-bottom: 1px solid rgba(212, 175, 55, 0.3);
            padding-bottom: 1rem;
        }

        /* ================== MESSAGE BOXES (Story) ================== */
        .message-box {
            padding: 18px 24px;
            border-radius: 12px;
            margin-bottom: 20px;
            line-height: 1.7;
            font-size: 1.15rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            position: relative;
            overflow: hidden;
        }
        
        .ai-message {
            background: linear-gradient(145deg, rgba(30, 15, 10, 0.95), rgba(20, 10, 5, 0.98));
            border-left: 4px solid #8a0303; /* Blood Red */
            border-right: 1px solid rgba(138, 3, 3, 0.2);
        }
        
        .user-message {
            background: linear-gradient(145deg, rgba(20, 25, 35, 0.95), rgba(10, 15, 25, 0.98));
            border-left: 4px solid #4682b4; /* Steel Blue */
            border-right: 1px solid rgba(70, 130, 180, 0.2);
        }

        .message-box strong {
            font-family: 'Cinzel', serif;
            font-size: 0.95rem;
            color: #d4af37; /* Gold */
            text-transform: uppercase;
            display: block;
            margin-bottom: 8px;
            letter-spacing: 0.05em;
            opacity: 0.9;
        }

        /* ================== SIDEBAR ================== */
        [data-testid="stSidebar"] {
            background-color: #080403;
            border-right: 2px solid #3a2516;
        }
        
        /* Sidebar Text Visibility Fix */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] label {
            color: #e8d8c3 !important; /* Light text for contrast */
            text-shadow: 1px 1px 2px rgba(0,0,0,0.9); /* Shadow for readability */
        }
        
        /* Highlight specific values */
        [data-testid="stSidebar"] .stMarkdown strong {
            color: #d4af37 !important; /* Gold for values */
        }

        .sidebar-section {
            background: rgba(255, 255, 255, 0.05); /* Slightly brighter bg */
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 15px;
            border: 1px solid rgba(212, 175, 55, 0.2);
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
        }
        
        .inventory-item {
            padding: 8px 12px;
            background: rgba(0,0,0,0.3);
            border-radius: 6px;
            margin-bottom: 6px;
            border-left: 3px solid #d4af37;
            font-size: 0.95rem;
            color: #dcdcdc;
            transition: transform 0.2s;
        }
        .inventory-item:hover {
            transform: translateX(3px);
            background: rgba(212, 175, 55, 0.1);
        }

        /* ================== INPUTS & FORMS ================== */
        /* Label styling (Ce vrei să faci?) */
        .stTextInput label {
            color: #d4af37 !important;
            font-size: 1.3rem !important;
            font-family: 'Cinzel', serif !important;
            text-shadow: 0 2px 4px rgba(0,0,0,1);
            margin-bottom: 8px;
        }

        .stTextInput > div > div > input {
            background: rgba(10, 5, 5, 0.9);
            color: #fff;
            border: 1px solid #5a3921;
            border-bottom: 2px solid #d4af37; /* Gold bottom */
            border-radius: 6px;
            padding: 12px 16px;
            font-family: 'Crimson Text', serif;
            font-size: 1.2rem;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #ff4500; /* Bright red focus */
            background: rgba(30, 10, 10, 1);
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.2);
        }

        /* ================== BUTTONS ================== */
        .stButton > button {
            background: linear-gradient(to bottom, #5a3921, #3e2718) !important;
            color: #ffffff !important; /* Pure white text */
            border: 1px solid #8b6b6b !important;
            border-bottom: 3px solid #2a1a10 !important;
            border-radius: 8px !important;
            font-family: 'Cinzel', serif !important;
            font-weight: 700 !important; /* Bolder */
            letter-spacing: 0.05em !important;
            padding: 0.6rem 1.2rem !important;
            transition: all 0.2s ease !important;
            text-transform: uppercase;
            text-shadow: 0px 2px 3px rgba(0,0,0,1); /* Strong shadow */
        }
        
        /* Fix for inner text elements in buttons */
        .stButton > button p {
             color: #ffffff !important;
             font-weight: 700 !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(to bottom, #7a4f2a, #5a3921) !important;
            color: #fff !important;
            border-color: #d4af37 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(212, 175, 55, 0.2);
        }
        
        .stButton > button:active {
            border-bottom-width: 1px !important;
            transform: translateY(2px);
        }

        /* Primary Button (Action) */
        button[kind="primary"] {
            background: linear-gradient(to bottom, #8a0303, #5a0202) !important;
            border-color: #b22222 !important;
            border-bottom-color: #300000 !important;
        }
        
        button[kind="primary"]:hover {
            background: linear-gradient(to bottom, #a50404, #7a0303) !important;
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.3);
        }

        /* ================== TABS ================== */
        .stTabs [data-baseweb="tab-list"] {
            background-color: rgba(0,0,0,0.2);
            border-bottom: 2px solid #5a3921;
            gap: 0 !important;
            padding: 0 !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border: none;
            color: #8b6b6b;
            border-radius: 0;
            padding: 10px 20px;
            font-family: 'Cinzel', serif;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(to top, rgba(212, 175, 55, 0.1), transparent);
            color: #d4af37;
            border-bottom: 2px solid #d4af37;
            font-weight: bold;
        }

        /* ================== ALERTS & PROGRESS ================== */
        .stAlert {
            background-color: rgba(40, 10, 10, 0.9);
            border: 1px solid #8a0303;
            color: #ffcccc;
        }
        
        .stProgress > div > div > div > div {
            background: linear-gradient(to right, #8a0303, #d4af37);
        }
        
        /* Loading Text */
        .progress-text {
            font-family: 'Cinzel', serif;
            color: #d4af37;
            font-size: 1.2rem;
            text-align: center;
            margin-top: 10px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; text-shadow: 0 0 10px rgba(212, 175, 55, 0.5); }
            100% { opacity: 0.6; }
        }

        /* ================== EPISODE CARD ================== */
        .episode-card {
            background: linear-gradient(135deg, #1a0f0b 0%, #0d0704 100%);
            border: 2px solid #D4AF37;
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
            text-align: center;
            box-shadow: 0 0 20px rgba(212, 175, 55, 0.1);
            position: relative;
            overflow: hidden;
        }
        
        .episode-card::before {
            content: "✦";
            display: block;
            font-size: 2rem;
            color: #D4AF37;
            margin-bottom: 10px;
        }

        .episode-title {
            font-family: 'Cinzel', serif;
            font-size: 1.8rem;
            color: #D4AF37;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            text-shadow: 0 2px 4px rgba(0,0,0,0.8);
        }

        .episode-desc {
            color: #ccc;
            font-style: italic;
            margin-bottom: 20px;
            font-size: 1.1rem;
        }

        .episode-section-title {
            color: #8a0303; /* Blood Red */
            font-family: 'Cinzel', serif;
            font-weight: bold;
            font-size: 1.2rem;
            margin-top: 15px;
            margin-bottom: 8px;
            border-bottom: 1px solid #3a2516;
            display: inline-block;
            padding-bottom: 2px;
        }

        .episode-list {
            list-style-type: none;
            padding: 0;
            text-align: left;
            margin: 0 auto;
            max-width: 80%;
        }

        .episode-list li {
            padding: 5px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #e8d8c3;
        }
        
        .episode-list li::before {
            content: "⚔️ ";
            color: #D4AF37;
        }
        
        .episode-hints li::before {
            content: "💡 ";
            color: #ffd700;
        }

        /* ================== KO-FI BUTTON ================== */
        .kofi-button {
            display: inline-block;
            background: linear-gradient(to bottom, #2c1e16, #1a0f0b);
            color: #d4af37 !important;
            font-family: 'Cinzel', serif;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 6px;
            text-decoration: none !important;
            border: 1px solid #5a3921;
            box-shadow: inset 0 0 5px rgba(0,0,0,0.5);
            transition: all 0.3s ease;
            letter-spacing: 0.05em;
        }
        .kofi-button:hover {
            background: linear-gradient(to bottom, #3a2516, #2c1e16);
            border-color: #d4af37;
            color: #fff !important;
            box-shadow: 0 0 10px rgba(212, 175, 55, 0.2);
            transform: translateY(-1px);
        }
        .kofi-icon {
            margin-right: 5px;
        }

        </style>
    """, unsafe_allow_html=True)


def display_story(story: List[Dict]):
    """Render story messages as a single HTML block to prevent flickering"""
    html_content = '<div class="story-container">'
    
    for msg in story:
        # Check for special Episode Intro type
        if msg.get("type") == "episode_intro":
            data = msg.get("content_data", {})
            title = data.get("title", "Episod Nou")
            desc = data.get("description", "")
            objs = data.get("objectives", [])
            hints = data.get("hints", [])
            
            # Build HTML for objectives
            objs_html = "".join([f"<li>{o}</li>" for o in objs])
            hints_html = "".join([f"<li>{h}</li>" for h in hints])
            
            html_content += f"""
<div class="episode-card">
<div class="episode-title">{title}</div>
<div class="episode-desc">{desc}</div>
<div class="episode-section-title">OBIECTIVE</div>
<ul class="episode-list">
{objs_html}
</ul>
{f'<div class="episode-section-title">INDICII</div><ul class="episode-list episode-hints">{hints_html}</ul>' if hints else ''}
</div>
"""
            continue

        role_class = "ai-message" if msg["role"] == "ai" else "user-message"
        role_icon = "🧙" if msg["role"] == "ai" else "🎭"
        
        if msg["role"] == "ai":
            role_name = "NARATOR"
        else:
            # Use character name from session, uppercase for style
            char_name = st.session_state.get("character_name", "TU")
            role_name = char_name.upper() if char_name else "TU"
        
        # Format text content
        text_content = msg["text"].replace('\n', '<br>')
        
        # Style "Sugestii:" to match the header style (Gold, Cinzel)
        # We look for bolded "Sugestii:" and replace it with a strong tag that triggers the CSS
        text_content = text_content.replace('**Sugestii:**', '<br><strong>SUGESTII:</strong>')
        text_content = text_content.replace('**Suggestions:**', '<br><strong>SUGESTII:</strong>')
        
        html_content += f"""
<div class="message-box {role_class}">
<strong>{role_icon} {role_name}:</strong><br/>
{text_content}
"""
        
        # Embed image if present (convert bytes to base64 for inline HTML)
        if msg["role"] == "ai" and msg.get("image") is not None:
            try:
                if isinstance(msg["image"], bytes):
                    b64_img = base64.b64encode(msg["image"]).decode('utf-8')
                    img_src = f"data:image/png;base64,{b64_img}"
                else:
                    # Assume it's already a URL or base64 string? 
                    # If it's bytes, the above handles it.
                    img_src = str(msg["image"])
                
                html_content += f"""
<div style="text-align: center; margin-top: 15px;">
<img src="{img_src}" style="max-width: 100%; border-radius: 8px; border: 2px solid #5a3921; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
</div>
"""
            except Exception as e:
                print(f"Error encoding image: {e}")
        
        html_content += "</div>"
    
    html_content += '</div>'
    
    # Render the entire story in one go
    st.markdown(html_content, unsafe_allow_html=True)

def render_header():
    """Render main title header with support button"""
    # Use symmetrical columns to keep title perfectly centered
    c1, c2, c3 = st.columns([2, 6, 2]) 
    with c2:
        st.markdown('<h1 class="main-header">WALLACHIA</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Aventura în Secolul XV pe timpul domniei lui Vlad Țepeș</p>', unsafe_allow_html=True)
    with c3:
        st.markdown(
            """
            <div style="text-align: right; padding-top: 10px;">
            <a href="https://ko-fi.com/wallachiastory" target="_blank" class="kofi-button">
                Susține Cronicarul
            </a>
            </div>
            """, 
            unsafe_allow_html=True
        )

def render_loading_screen():
    """Display a medieval loading screen animation"""
    st.markdown("""
        <style>
        .loading-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: #0d0704;
            color: #d4af37;
            font-family: 'Cinzel', serif;
            z-index: 999999;
            text-align: center;
        }
        .spinner-sword {
            font-size: 4rem;
            animation: spin 2s infinite linear;
            margin-bottom: 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
        <div class="loading-container">
            <div class="spinner-sword">⚔️</div>
            <h2 style="text-align: center; width: 100%;">Se pregătește tărâmul...</h2>
        </div>
    """, unsafe_allow_html=True)

def render_sidebar_header_controls(on_name_change=None) -> int:
    """
    Render top sidebar section with User Info and Controls.
    Contains WIDGETS (Inputs, Sliders). Must be called from main logic (not fragment).
    Returns legend_scale.
    """
    # Inițializăm flag-ul pentru tracking-ul fișierelor încărcate
    if "_loaded_file_hash" not in st.session_state:
        st.session_state._loaded_file_hash = None

    # USER INFO - Display authenticated user's character name
    if "character_name" in st.session_state and st.session_state.character_name:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown(f"**👤 {st.session_state.character_name}**")

        # Character name change option
        with st.expander("⚙️ Schimbă nume erou"):
            with st.form("change_name_form"):
                new_name = st.text_input(
                    "Nume nou erou",
                    value=st.session_state.character_name,
                    placeholder="Introdu noul nume..."
                )
                if st.form_submit_button("💾 Salvează", type="secondary"):
                    if on_name_change:
                        on_name_change(new_name)
                    else:
                        # Fallback
                        st.session_state.pending_name_change = new_name
                        st.success("🔄 Procesăm schimbarea numelui...")
                        time.sleep(0.5)
                        st.rerun()

        st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)

    # CONTROLS
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.title("⚔️ Controale")

    legend_scale = st.slider(
        "Adevăr Istoric vs Legendă",
        min_value=0,
        max_value=10,
        value=0,
        help="0 = Strict istoric, 10 = Legendă vampirică",
        key="legend_slider"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    return legend_scale

def render_sidebar_stats(game_state: "GameState"):
    """
    Render sidebar statistics (Stats, Inventory, Campaign).
    Contains NO WIDGETS (only markdown/progress). Safe for fragments.
    """
    # CAMPAIGN PROGRESS (if applicable)
    if game_state.character.game_mode == GameMode.CAMPAIGN:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        # Use persisted episode number or calculate
        ep_num = game_state.character.current_episode
        if ep_num == 0: ep_num = 1
        
        from campaign import CAMPAIGN_EPISODES
        episode = CAMPAIGN_EPISODES.get(ep_num, CAMPAIGN_EPISODES[1])
        
        st.subheader(f"🌑 Campania: Pecetea Drăculeștilor")
        st.markdown(f"**Episodul {ep_num}: {episode['title']}**")
        
        # Use explicit progress or fallback to turns
        progress = getattr(game_state.character, 'episode_progress', 0.0)
        
        st.text(f"⏳ Progres Episod: {int(progress * 100)}%")
        st.progress(progress)
        
        st.caption(f"📍 {episode['location']}")
        st.markdown('</div>', unsafe_allow_html=True)

    # CHARACTER SHEET
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    with st.expander("📜 Foaie de Personaj", expanded=True):
        # Class & Faction
        if game_state.character.character_class:
            st.markdown(f"**⚔️ Clasă:** {game_state.character.character_class.value}")
        if game_state.character.faction:
            st.markdown(f"**🚩 Facțiune:** {game_state.character.faction.value}")
            # Show Faction Details
            if game_state.character.faction in FACTIONS:
                f_data = FACTIONS[game_state.character.faction]
                st.markdown(f"<small>✨ {f_data['bonuses']}</small>", unsafe_allow_html=True)
                st.markdown(f"<small>⚠️ {f_data['disadvantage']}</small>", unsafe_allow_html=True)
        
        # Special Ability
        if game_state.character.special_ability:
            st.markdown(f"**✨ Abilitate Specială:** {game_state.character.special_ability}")

        # Health Bar
        health_pct = max(0.0, min(1.0, game_state.character.health / 100))
        st.text(f"❤️ Viață: {game_state.character.health}/100")
        st.progress(health_pct)
        
        # Reputation Bar
        rep_pct = max(0.0, min(1.0, game_state.character.reputation / 100))
        st.text(f"👑 Reputație: {game_state.character.reputation}/100")
        st.progress(rep_pct)
        
        # Gold
        st.text(f"💰 Galbeni: {game_state.character.gold}")
        
        # Location
        st.text(f"📍 Locație: {game_state.character.location}")

    # Attributes Bar (Abilities) - Collapsed by default
    with st.expander("📊 Abilități & Statistici", expanded=False):
        # Define key stats to show
        key_stats = {
            "Forță": game_state.character.strength,
            "Agilitate": game_state.character.agility,
            "Inteligență": game_state.character.intelligence,
            "Carismă": game_state.character.charisma
        }
        
        # Create simple bars for stats (assuming max ~5-10 for visualization)
        for stat, val in key_stats.items():
            # Normalized to 5 for visual bar
            norm_val = min(1.0, val / 5.0)
            st.text(f"{stat}: {val}")
            st.progress(norm_val)
            
    st.markdown('</div>', unsafe_allow_html=True)
    
    # INVENTORY
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    with st.expander("🎒 Inventar", expanded=False):
        # ⭕ ITEREAZĂ PRIN INVENTORY DIN GAME_STATE
        if not game_state.inventory:
            st.caption("Inventar gol.")
        else:
            for item in game_state.inventory:
                # Doar afișează iteme cu quantity > 0
                if item.quantity > 0:
                    qty_str = f" x{item.quantity}" if item.quantity > 1 else ""
                    st.markdown(
                        f'<div class="inventory-item">{item.name}{qty_str}</div>',
                        unsafe_allow_html=True
                    )
    st.markdown('</div>', unsafe_allow_html=True)

def render_sidebar_footer(game_state: "GameState", db=None, cookie_manager=None):
    """
    Render bottom sidebar section (Game Management).
    Contains WIDGETS. Must be called from main logic.
    """
    # 1. START NEW GAME
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.subheader("🆕 Aventură Nouă")
    if st.button("⚔️ Începe Poveste Nouă", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())[:8]
        st.session_state.session_id = new_id
        
        # Set flag to force new game creation in app.py logic
        st.session_state.force_new_game = True

        # Clear state to force init
        if "game_state" in st.session_state:
            del st.session_state.game_state
        if "story" in st.session_state:
            del st.session_state.story
            
        st.success("O nouă filă de cronică începe...")
        time.sleep(1)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if db and db.client and "user" in st.session_state and st.session_state.user:
        user_id = st.session_state.user.user.id

        # 2. SAVE GAME (Manual Checkpoint)
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("💾 Salvează Progres")
        
        save_name = st.text_input("Etichetă Salvare (Opțional)", placeholder="Ex: Înainte de bătălie")
        
        if st.button("💾 Creează Punct de Salvare", use_container_width=True):
            try:
                # Create a NEW session entry as a snapshot
                # We encode the save name into the session_id to avoid schema changes
                timestamp_part = int(time.time())
                
                if save_name:
                    # Sanitize name: keep alphanum, spaces, hyphens
                    clean_name = re.sub(r'[^a-zA-Z0-9 \-ăâîșțĂÂÎȘȚ]', '', save_name).strip()
                    clean_name = clean_name.replace(' ', '_')
                    if not clean_name:
                        clean_name = "Salvare"
                    new_session_id = f"{user_id}_{timestamp_part}_manual_{clean_name}"
                else:
                    new_session_id = f"{user_id}_{timestamp_part}_manual"
                
                # Prepare data
                session_data = {
                    'session_id': new_session_id,
                    'user_id': user_id,
                    'story_data': game_state.story,
                    'character_stats': game_state.character.model_dump(),
                    'inventory': [item.model_dump() for item in game_state.inventory],
                    'current_turn': game_state.turn,
                    'last_image_turn': game_state.last_image_turn,
                    'is_active': False, # Manual saves are inactive checkpoints by default
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                db.client.table('game_sessions').insert(session_data).execute()
                
                st.success(f"✅ Salvare reușită! ({time.strftime('%H:%M')})")
                time.sleep(1)
            except Exception as e:
                st.error(f"❌ Eroare la salvare: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        # 3. LOAD GAME
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("📂 Încarcă Cronica")
        
        try:
            # Fetch all sessions including inactive ones (manual saves)
            response = db.client.table('game_sessions').select('session_id, created_at, updated_at, current_turn, is_active').eq('user_id', user_id).order('updated_at', desc=True).limit(20).execute()
            sessions = response.data if response.data else []
            
            if sessions:
                # Create readable labels
                session_options = {}
                for s in sessions:
                    sid = s['session_id']
                    timestamp = s['updated_at'][:16].replace('T', ' ')
                    turn_info = f"(Tur {s['current_turn']})"
                    
                    # Parse name from session_id if present
                    # Format: user_id_timestamp_manual_SaveName
                    label = ""
                    if "_manual_" in sid:
                        try:
                            parts = sid.split("_manual_")
                            if len(parts) > 1:
                                raw_name = parts[1]
                                # Restore spaces
                                display_name = raw_name.replace('_', ' ')
                                label = f"💾 {display_name} - {timestamp} {turn_info}"
                            else:
                                label = f"💾 Salvare Manuală - {timestamp} {turn_info}"
                        except:
                            label = f"💾 Salvare - {timestamp} {turn_info}"
                    elif "_manual" in sid:
                         label = f"💾 Salvare Manuală - {timestamp} {turn_info}"
                    else:
                        # Auto save (usually active or old active)
                        status = "🟢 Activ" if s.get('is_active') else "⚪ Auto"
                        label = f"{status} - {timestamp} {turn_info}"

                    session_options[label] = sid
                
                selected_label = st.selectbox("Alege salvarea:", list(session_options.keys()))
                
                if st.button("📖 Încarcă Această Salvare", use_container_width=True):
                    selected_id = session_options[selected_label]
                    try:
                        # If loading a manual save, FORK it to a new autosave to preserve the checkpoint
                        if "_manual" in selected_id:
                            # Load data
                            loaded_state = db.load_game_session(selected_id)
                            if loaded_state:
                                # Create new Active Session ID
                                new_active_id = f"{user_id}_{int(time.time())}"
                                
                                # Save as new session
                                db.create_game_session(user_id, loaded_state)
                                # The above uses generated ID? No, create_game_session generates one based on time.
                                # Let's assume create_game_session returns the ID.
                                # Wait, create_game_session logic:
                                # session_id = f"{user_id}_{int(datetime.utcnow().timestamp())}"
                                # It ignores passed ID?
                                # Yes. So we just call create_game_session.
                                
                                new_sid = db.create_game_session(user_id, loaded_state)
                                
                                # Cleanup old autosaves
                                db.delete_old_autosaves(user_id, new_sid)
                                
                                # Set local state
                                st.session_state.db_session_id = new_sid
                                st.session_state.session_id = new_sid
                            else:
                                st.error("Eroare la citirea salvării.")
                                return
                        else:
                            # Loading an existing autosave
                            # Just make it active
                            db.client.table('game_sessions').update({'is_active': False}).eq('user_id', user_id).execute()
                            db.client.table('game_sessions').update({'is_active': True}).eq('session_id', selected_id).execute()
                            
                            # Cleanup duplicates if any
                            db.delete_old_autosaves(user_id, selected_id)
                            
                            st.session_state.db_session_id = selected_id
                            st.session_state.session_id = selected_id

                        # Reload
                        if "game_state" in st.session_state:
                            del st.session_state.game_state
                        
                        st.success("⏳ Se încarcă...")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Eroare: {e}")
            else:
                st.info("Nu ai nicio salvare.")
        except Exception as e:
            st.error(f"Eroare conexiune DB: {e}")
            
        st.markdown('</div>', unsafe_allow_html=True)
    
    # EXPORT PDF/HTML
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.subheader("🧾 Export Aventură")

    # ✅ BUTON HTML (funcționează întotdeauna)
    if st.button("📄 Generează & Descarcă HTML", use_container_width=True):
        with st.spinner("Se creează documentul..."):
            html_content = generate_pdf_html(st.session_state.story)
            
            standalone_html = f"""<!DOCTYPE html>
                                <html>
                                <head>
                                    <meta charset="UTF-8">
                                    <style>
                                        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
                                        body {{ font-family: 'Crimson Text', serif; background: #fdf6e3; padding: 40px; color: #4b3f2f; }}
                                        h1 {{ font-family: 'Cinzel', serif; color: #6b4f4f; text-align: center; margin-bottom: 30px; }}
                                        .message {{ margin-bottom: 20px; padding: 15px; border-left: 4px solid #5a3921; background: rgba(90, 57, 33, 0.05); page-break-inside: avoid; }}
                                        .ai {{ border-left-color: #ff6b6b; }}
                                        .user {{ border-left-color: #4e9af1; }}
                                        img {{ max-width: 100%; margin: 20px auto; display: block; border-radius: 8px; border: 2px solid #5a3921; }}
                                        .footer {{ text-align: center; margin-top: 40px; font-style: italic; color: #8b6b6b; }}
                                        @media print {{ body {{ background: white; }} }}
                                    </style>
                                </head>
                                <body>
                                    <h1>⚔️ Aventura în Wallachia ⚔️</h1>
                                    <p class="footer">Generat pe {time.strftime('%Y-%m-%d %H:%M')}</p>
                                    <hr>
                                    {html_content}
                                </body>
                                </html>"""
            
            st.download_button(
                "📥 Descarcă HTML",
                data=standalone_html.encode('utf-8'),
                file_name=f"aventura_wallachia_{int(time.time())}.html",
                mime="text/html",
                use_container_width=True
            )

    # 💡 Instrucțiuni pentru PDF
    with st.expander("💡 Cum faci PDF din HTML?"):
        st.markdown("""
        **3 pași simpli:**
        1. Descarcă fișierul HTML
        2. Deschide-l în Chrome/Firefox
        3. Apasă `Ctrl+P` (Windows) / `Cmd+P` (Mac) și selectează "Save as PDF"
        
        *Setări recomandate:*
        - Margini: Minimum
        - Scale: 95%
        """)

    st.markdown('</div>', unsafe_allow_html=True)
    
    # LOGOUT SECTION
    st.markdown("---")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)

    # ⭕ VERIFICĂM DACĂ USER ESTE AUTENTIFICAT
    if "user" in st.session_state and st.session_state.user:
        if st.button("🚪 Deconectare", type="secondary", use_container_width=True):
            try:
                # 1. Sign out from Supabase and invalidate DB sessions
                if db and db.client:
                    # Invalidate persistent sessions to prevent auto-login from DB
                    try:
                        user_id = st.session_state.user.user.id
                        # Delete the session record entirely as 'is_active' column might not exist
                        db.client.table('user_sessions').delete().eq('user_id', user_id).execute()
                    except Exception as db_err:
                        print(f"DB session invalidation error: {db_err}")
                    
                    db.client.auth.sign_out()

                # 2. Clear session state but keep logout flag
                # IMPORTANT: Do this BEFORE cookie operations to ensure state is cleared 
                # even if cookie component triggers an early rerun.
                st.session_state.clear()
                st.session_state['logging_out'] = True
                
                # 3. Clear cookies if manager is provided
                if cookie_manager:
                    try:
                        # Use unique keys to avoid Streamlit duplicate key errors
                        cookie_manager.delete('sb_access_token', key='delete_access_token')
                        cookie_manager.delete('sb_refresh_token', key='delete_refresh_token')
                    except Exception as cookie_err:
                        print(f"Cookie cleanup error: {cookie_err}")

                st.success("👋 Ai fost deconectat!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Eroare la logout: {e}")

def render_sidebar(game_state: "GameState", cookie_manager=None, on_name_change=None, db=None) -> int:
    """Wrapper legacy for backward compatibility"""
    l = render_sidebar_header_controls(on_name_change)
    render_sidebar_stats(game_state)
    render_sidebar_footer(game_state, db, cookie_manager)
    return l

def generate_pdf_html(story: List[Dict]) -> str:
    """Generate styled HTML for PDF export (includes images as base64)"""
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
            body {{ 
                font-family: 'Crimson Text', serif; 
                background: #fdf6e3; 
                padding: 40px;
                color: #4b3f2f;
            }}
            h1 {{ 
                font-family: 'Cinzel', serif; 
                color: #6b4f4f; 
                text-align: center;
                margin-bottom: 30px;
            }}
            .message {{ 
                margin-bottom: 20px; 
                padding: 15px; 
                border-left: 4px solid #5a3921;
                background: rgba(90, 57, 33, 0.05);
                page-break-inside: avoid;
            }}
            .ai {{ border-left-color: #ff6b6b; }}
            .user {{ border-left-color: #4e9af1; }}
            img {{ 
                max-width: 500px; 
                margin: 20px auto; 
                display: block;
                border-radius: 8px;
                border: 2px solid #5a3921;
            }}
            .footer {{ 
                text-align: center; 
                margin-top: 40px; 
                font-style: italic;
                color: #8b6b6b;
            }}
        </style>
    </head>
    <body>
        <h1>Aventura în Wallachia</h1>
        <p class="footer">Generat pe {time.strftime('%Y-%m-%d %H:%M')}</p>
    """
    
    for m in story:
        role_class = "ai" if m["role"] == "ai" else "user"
        html += f"""
        <div class="message {role_class}">
            <strong>{m['role'].capitalize()}:</strong><br/>
            {m['text']}
        </div>
        """
        if "image" in m and m["image"]:
            b64 = base64.b64encode(m["image"]).decode()
            html += f'<img src="data:image/png;base64,{b64}" />'
    
    html += "</body></html>"
    return html
