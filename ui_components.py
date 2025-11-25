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

def inject_css():
    """Injectează CSS medieval - VERSIUNE SIMPLIFICATĂ"""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
        
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px !important;
            margin: 0 auto;
        }
        
        .stApp {
            background: linear-gradient(135deg, #0a0805 0%, #1a0f0b 50%, #0d0704 100%);
            color: #e8d8c3;
            font-family: 'Crimson Text', serif;
        }
        
        .main-header {
            font-family: 'Cinzel', serif;
            font-size: 3.5rem;
            font-weight: 700;
            text-align: center;
            background: linear-gradient(90deg, #ff6b6b, #d4af37, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            margin-bottom: 0;
            letter-spacing: 2px;
        }
        
        .subtitle {
            font-family: 'Cinzel', serif;
            font-size: 1.2rem;
            text-align: center;
            color: #d4af37;
            margin-bottom: 30px;
            letter-spacing: 1px;
        }
        
        .story-container {
            background: rgba(30, 20, 10, 0.85);
            border: 2px solid #5a3921;
            border-radius: 12px;
            padding: 25px;
            margin: 20px auto;
            box-shadow: 0 6px 20px rgba(0,0,0,0.7);
        }
        
        .message-box {
            margin-bottom: 20px;
            padding: 20px;
            border-left: 4px solid #d4af37;
            background: rgba(20, 15, 8, 0.8);
            border-radius: 0 8px 8px 0;
            font-size: 1.2rem;
            line-height: 1.8;
            letter-spacing: 0.5px;
            color: #f4e4c1;
        }
        
        .ai-message {
            border-left-color: #ff6b6b;
        }
        
        .user-message {
            border-left-color: #4e9af1;
        }
        
        .story-image-container {
            text-align: center;
            margin: 15px 0;
            padding: 10px;
            background: rgba(20, 15, 8, 0.6);
            border-radius: 8px;
            border: 1px solid #5a3921;
        }
        
        .stTextInput label {
            font-family: 'Cinzel', serif !important;
            color: #d4af37 !important;
            font-weight: 700 !important;
            font-size: 1.3rem !important;
            margin-bottom: 10px !important;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
        }
        
        .stButton>button {
            background: linear-gradient(135deg, #5a3921 0%, #7a4f2a 100%) !important;
            color: #ffffff !important;
            border: 2px solid #d4af37 !important;
            border-radius: 10px;
            padding: 16px 32px !important;
            font-family: 'Crimson Text', serif !important;
            font-weight: 600 !important;
            font-size: 1.3rem !important;
            line-height: 1.4 !important;
            letter-spacing: 0.5px !important;
            min-height: 60px !important;
            box-sizing: border-box !important;
            transition: all 0.3s ease;
            width: 100%;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }

        .stButton>button:hover {
            background: linear-gradient(135deg, #7a4f2a 0%, #9a6f3a 100%) !important;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.6) !important;
            transform: translateY(-3px);
        }
        
        .stTextInput>div>input {
            background: rgba(20, 15, 8, 0.95);
            color: #e8d8c3;
            border: 2px solid #5a3921;
            border-radius: 8px;
            padding: 14px;
            font-size: 1.2rem;
            line-height: 1.6;
        }
        
        .sidebar-section {
            background: rgba(30, 20, 10, 0.9) !important;
            padding: 18px !important;
            border-radius: 8px !important;
            margin-bottom: 15px !important;
            border: 1px solid #d4af37 !important;
        }
        
        .stSidebar .stMarkdown p,
        .stSidebar .stMarkdown span,
        .stSidebar .stMarkdown div {
            color: #f4e4c1 !important;
            font-size: 1.1rem !important;
            line-height: 1.7 !important;
            font-weight: 500 !important;
        }
        
        .inventory-item {
            background: rgba(90, 57, 33, 0.6);
            padding: 10px 14px;
            margin: 6px 0;
            border-radius: 5px;
            border-left: 3px solid #d4af37;
            font-size: 1rem;
            color: #f4e4c1 !important;
        }
        
        .progress-text {
            font-family: 'Cinzel', serif;
            color: #d4af37;
            font-size: 1.3rem;
            text-align: center;
            margin: 10px 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
            font-weight: 600;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        .stToast {
            background: rgba(30, 20, 10, 0.95) !important;
            border: 2px solid #d4af37 !important;
            font-size: 1.1rem;
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
    
    return legend_scale  # ⭕ Returnează valoarea pentru slider


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