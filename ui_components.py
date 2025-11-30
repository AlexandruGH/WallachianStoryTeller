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
import os
import re
import pdfkit
import requests
from models import GameState, CharacterStats, InventoryItem

# Import Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    supabase: Optional[Client] = None
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
except ImportError:
    supabase = None

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
def inject_css():
    """CSS medieval - VERSIUNE FINALĂ PENTRU AUTH"""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
        
        /* Fundal și fonturi generale */
        .stApp {
            background: linear-gradient(135deg, #0a0805 0%, #1a0f0b 50%, #0d0704 100%);
            color: #e8d8c3;
            font-family: 'Crimson Text', serif;
        }
        
        /* Tabs profesionale */
        .stTabs {
            margin-top: 20px !important;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(30, 20, 10, 0.8);
            border-radius: 12px;
            padding: 4px;
            gap: 4px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            flex: 1;
            justify-content: center;
            border-radius: 8px;
            padding: 12px 16px !important;
            font-weight: 600;
            font-size: 1rem;
            color: #8b6b6b;
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #5a3921, #7a4f2a) !important;
            color: #d4af37 !important;
            box-shadow: 0 2px 8px rgba(212, 175, 55, 0.3);
        }
        
        /* Input fields */
        .stTextInput > div > div > input {
            background: rgba(20, 15, 8, 0.95);
            color: #e8d8c3;
            border: 2px solid #5a3921;
            border-radius: 8px;
            padding: 14px 16px;
            font-size: 1.1rem;
            line-height: 1.6;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #d4af37 !important;
            box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2) !important;
        }
        
        /* Butoane */
        .stButton > button {
            background: linear-gradient(135deg, #5a3921 0%, #7a4f2a 100%) !important;
            color: #ffffff !important;
            border: 2px solid #d4af37 !important;
            border-radius: 10px !important;
            padding: 16px 24px !important;
            font-family: 'Crimson Text', serif !important;
            font-weight: 600 !important;
            font-size: 1.2rem !important;
            transition: all 0.3s ease;
            width: 100%;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #7a4f2a 0%, #9a6f3a 100%) !important;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.6) !important;
            transform: translateY(-2px);
        }
        
        /* Mesaje de eroare */
        .stAlert {
            margin-top: 10px !important;
            padding: 12px 16px !important;
            border-radius: 8px !important;
        }
        </style>
    """, unsafe_allow_html=True)


def display_story(story: List[Dict]):
    """Render story messages (FĂRĂ CAPTION, CU DEBUG)"""
    for msg in story:
        role_class = "ai-message" if msg["role"] == "ai" else "user-message"
        role_icon = "🧙" if msg["role"] == "ai" else "🎭"
        role_name = "NARATOR" if msg["role"] == "ai" else "TU"
        
        # Afisează mesajul text
        st.markdown(
            f'<div class="message-box {role_class}">'
            f'<strong>{role_icon} {role_name}:</strong><br/>{msg["text"]}'
            f'</div>',
            unsafe_allow_html=True
        )
        # Afisează imaginea (fără caption) imediat sub text
        if msg["role"] == "ai" and msg.get("image") is not None:
            col_spacer1, col_img, col_spacer2 = st.columns([1, 3, 1])
            with col_img:
                st.image(
                    msg["image"],
                    use_container_width=True  # FĂRĂ CAPTION!
                )

def render_header():
    """Render main title header"""
    st.markdown('<h1 class="main-header">WALLACHIA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Aventura în Secolul XV pe timpul domniei lui Vlad Țepeș</p>', unsafe_allow_html=True)

def render_sidebar(game_state: "GameState") -> int:
    """
    Render sidebar cu controale, character sheet, și inventory.
    Primește GameState Pydantic și returnează legend_scale.
    """

    # Inițializăm flag-ul pentru tracking-ul fișierelor încărcate
    if "_loaded_file_hash" not in st.session_state:
        st.session_state._loaded_file_hash = None

    # USER INFO - Display authenticated user's character name
    if "character_name" in st.session_state and st.session_state.character_name:
        st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.sidebar.markdown(f"**👤 {st.session_state.character_name}**")

        # Character name change option
        with st.sidebar.expander("⚙️ Schimbă nume erou"):
            with st.form("change_name_form"):
                new_name = st.text_input(
                    "Nume nou erou",
                    value=st.session_state.character_name,
                    placeholder="Introdu noul nume..."
                )
                if st.form_submit_button("💾 Salvează", type="secondary"):
                    # Store the new name request for processing in main app
                    st.session_state.pending_name_change = new_name
                    st.success("🔄 Procesăm schimbarea numelui...")
                    time.sleep(0.5)
                    st.rerun()

        st.sidebar.markdown("---")
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # CONTROLS
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.title("⚔️ Controale")

    legend_scale = st.sidebar.slider(
        "Legenda vs Adevăr Istoric",
        min_value=0,
        max_value=10,
        value=5,
        help="0 = Strict istoric, 10 = Legendă vampirică",
        key="legend_slider"
    )
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # CHARACTER SHEET
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.subheader("📜 Foaie de Personaj")
    
    # Health Bar
    health_pct = game_state.character.health / 100
    st.sidebar.text(f"❤️ Viață: {game_state.character.health}/100")
    st.sidebar.progress(health_pct)
    
    # Reputation Bar
    rep_pct = game_state.character.reputation / 100
    st.sidebar.text(f"👑 Reputație: {game_state.character.reputation}/100")
    st.sidebar.progress(rep_pct)
    
    # Gold
    st.sidebar.text(f"💰 Galbeni: {game_state.character.gold}")
    
    # Location
    st.sidebar.text(f"📍 Locație: {game_state.character.location}")
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # INVENTORY
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.subheader("🎒 Inventar")
    
    # ⭕ ITEREAZĂ PRIN INVENTORY DIN GAME_STATE
    for item in game_state.inventory:
        # Doar afișează iteme cu quantity > 0
        if item.quantity > 0:
            qty_str = f" x{item.quantity}" if item.quantity > 1 else ""
            st.sidebar.markdown(
                f'<div class="inventory-item">{item.name}{qty_str}</div>',
                unsafe_allow_html=True
            )
    
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # SAVE / LOAD STORY
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.subheader("💾 Salvează Aventura")
    
    # === FIX: Exportă game_state ca JSON compatibil (CU IMAGINI)
    def game_state_to_dict():
        # Encode imagini ca base64 pentru serializare JSON
        story_with_images = []
        for msg in st.session_state.story:
            msg_copy = msg.copy()
            if msg_copy.get("image") and isinstance(msg_copy["image"], bytes):
                msg_copy["image"] = base64.b64encode(msg_copy["image"]).decode('utf-8')
            story_with_images.append(msg_copy)
        
        return {
            "character": game_state.character.model_dump(),
            "inventory": [item.model_dump() for item in game_state.inventory],
            "story": story_with_images,  # ⭕ Acum include imagini
            "turn": game_state.turn,
            "last_image_turn": game_state.last_image_turn,
            "session_id": st.session_state.session_id  # ⭕ Salvează și session_id
        }
    
    json_str = json.dumps(game_state_to_dict(), ensure_ascii=False, indent=2)
    
    st.sidebar.download_button(
        "📥 Descarcă JSON",
        data=json_str.encode("utf-8"),
        file_name=f"aventura_wallachia_{int(time.time())}.json",
        mime="application/json",
        use_container_width=True
    )
    
    st.sidebar.markdown("---")
    
    # JSON Load - FIXED: Prevenim bucla infinită folosind hash de fișier
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.subheader("📂 Încarcă Aventură (JSON)")
    
    uploaded = st.sidebar.file_uploader(
        "📂 Încarcă Aventură (JSON)",
        type=["json"],
        key="load_story"
    )
    
    # Procesăm doar dacă avem un fișier nou (folosim hashing pentru a detecta duplicatele)
    if uploaded is not None:
        # Calculăm hash-ul fișierului pentru a detecta dacă e același
        current_file_hash = hash(uploaded.getvalue())
        
        # Procesăm doar dacă hash-ul diferă de cel din session_state
        if current_file_hash != st.session_state._loaded_file_hash:
            try:
                data = json.load(uploaded)
                if "character" in data and "inventory" in data:
                    # Decode imagini din base64 înapoi în bytes
                    story_with_images = []
                    for msg in data.get("story", []):
                        if msg.get("image") and isinstance(msg["image"], str):
                            msg["image"] = base64.b64decode(msg["image"].encode('utf-8'))
                        story_with_images.append(msg)
                    
                    st.session_state.game_state = GameState(
                        character=CharacterStats(**data["character"]),
                        inventory=[InventoryItem(**item) for item in data["inventory"]],
                        story=story_with_images,
                        turn=data.get("turn", 0),
                        last_image_turn=data.get("last_image_turn", -10)
                    )
                    st.session_state.story = story_with_images
                    st.session_state.session_id = data.get("session_id", str(uuid.uuid4())[:8])
                    # Salvăm hash-ul fișierului procesat
                    st.session_state._loaded_file_hash = current_file_hash
                    st.sidebar.success("✅ Aventură încărcată!")
                    # Reîncărcăm pentru a afișa noua stare
                    st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ Eroare încărcare: {e}")
                # Resetăm hash-ul în caz de eroare
                st.session_state._loaded_file_hash = None
    
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # EXPORT PDF/HTML
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.subheader("🧾 Export Aventură")

    # ✅ BUTON HTML (funcționează întotdeauna)
    if st.sidebar.button("📄 Generează & Descarcă HTML", use_container_width=True):
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
            
            st.sidebar.download_button(
                "📥 Descarcă HTML",
                data=standalone_html.encode('utf-8'),
                file_name=f"aventura_wallachia_{int(time.time())}.html",
                mime="text/html",
                use_container_width=True
            )

    # 💡 Instrucțiuni pentru PDF
    with st.sidebar.expander("💡 Cum faci PDF din HTML?"):
        st.markdown("""
        **3 pași simpli:**
        1. Descarcă fișierul HTML
        2. Deschide-l în Chrome/Firefox
        3. Apasă `Ctrl+P` (Windows) / `Cmd+P` (Mac) și selectează "Save as PDF"
        
        *Setări recomandate:*
        - Margini: Minimum
        - Scale: 95%
        """)

    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # LOGOUT SECTION - MODIFICAT
    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)

    # ⭕ VERIFICĂM DACĂ USER ESTE AUTENTIFICAT
    if "user" in st.session_state and st.session_state.user:
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            try:
                # Sign out from Supabase
                supabase.auth.sign_out()

                # Clear session state
                st.session_state.clear()

                st.success("👋 Ai fost deconectat cu succes!")
                time.sleep(1.5)
                st.rerun()  # ✅ FIX: API stabil
            except Exception as e:
                st.error(f"❌ Eroare la logout: {e}")

    return legend_scale

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
