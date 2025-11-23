# ui_components.py - UI with HIGH VISIBILITY & WIDER CONTENT
import streamlit as st
from typing import List, Dict
from typing import Optional  # ✅ ACEASTĂ LINIE LIPSEȘTE
from io import BytesIO
from PIL import Image
import io
import shutil
import base64
import json
import time
import uuid
import base64
import os
import re
import pdfkit
import requests
from elevenlabs.client import ElevenLabs


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

# Cache client pentru viteză
@st.cache_resource(show_spinner=False)
def get_eleven_client():
    key = os.getenv("ELEVEN_API_KEY")
    if not key:
        st.error("🔑 **ELEVEN_API_KEY lipsește din .env**")
        st.stop()
    return ElevenLabs(api_key=key)

def clean_text_for_tts(text: str) -> str:
    """Șterge markdown și caractere pe care le citește literal."""
    text = re.sub(r"\*\*|\*|`|\"|'|_", "", text)  # Șterge *, **, `, ", ', _
    text = re.sub(r"\n+", " ", text)              # Newlines → spațiu
    return text.strip()

def medieval_tts(text: str) -> bytes:
    """ElevenLabs: voce Adam (masculin profund) în română."""
    text = clean_text_for_tts(text)
    client = get_eleven_client()

    # Adam = JBFqnCBsd6RMkjVDRZzb (deep male)
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # Convert generator to bytes
    return b"".join(audio)

def speak(text: str):
    """Butonul apasă și vorbește."""
    mp3 = medieval_tts(text)
    if mp3:
        b64 = base64.b64encode(mp3).decode()
        html = f"""<audio autoplay style="width:100%;">
          <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>"""
        st.components.v1.html(html, height=0)

def inject_css():
    """Inject medieval CSS with HIGH VISIBILITY & WIDER LAYOUT"""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
        
        /* === WIDER STORY CONTENT === */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px !important; /* Significantly wider */
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
        
        /* === HIGH VISIBILITY STORY TEXT === */
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
            background: rgba(20, 15, 8, 0.8); /* More opaque for readability */
            border-radius: 0 8px 8px 0;
            /* === HIGH VISIBILITY === */
            font-size: 1.2rem; /* Larger font */
            line-height: 1.8; /* Better spacing */
            letter-spacing: 0.5px;
            color: #f4e4c1; /* Brighter text */
        }
        
        .ai-message {
            border-left-color: #ff6b6b;
        }
        
        .user-message {
            border-left-color: #4e9af1;
        }
        
        /* === STORY IMAGE STYLING === */
        .story-image-container {
            text-align: center;
            margin: 15px 0;
            padding: 10px;
            background: rgba(20, 15, 8, 0.6);
            border-radius: 8px;
            border: 1px solid #5a3921;
        }
        
        /* === HIGH VISIBILITY INPUT LABEL === */
        .stTextInput label {
            font-family: 'Cinzel', serif !important;
            color: #d4af37 !important;
            font-weight: 700 !important; /* Bold */
            font-size: 1.3rem !important; /* Larger */
            margin-bottom: 10px !important;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
        }
        
        /* === HIGH VISIBILITY BUTTON === */
        .stButton>button {
            background: linear-gradient(135deg, #5a3921 0%, #7a4f2a 100%) !important;
            color: #ffffff !important;  /* PURE WHITE for maximum contrast */
            border: 2px solid #d4af37 !important;
            border-radius: 10px;  /* Slightly more rounded */
            padding: 16px 32px !important;  /* Increased padding */
            font-family: 'Crimson Text', serif !important;  /* MORE READABLE font */
            font-weight: 600 !important;  /* Slightly less heavy */
            font-size: 1.3rem !important;  /* LARGER text */
            line-height: 1.4 !important;  /* ADDED: Better vertical spacing */
            letter-spacing: 0.5px !important;  /* ADDED: Improve legibility */
            min-height: 60px !important;  /* ADDED: Prevent text clipping */
            box-sizing: border-box !important;  /* ADDED: Proper padding calculation */
            transition: all 0.3s ease;
            width: 100%;
            /* REMOVED blurry text-shadow */
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);  /* Softer shadow */
        }

        .stButton>button:hover {
            background: linear-gradient(135deg, #7a4f2a 0%, #9a6f3a 100%) !important;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.6) !important;
            transform: translateY(-3px);
        }
        
        .stTextInput>div>input {
            background: rgba(20, 15, 8, 0.95); /* More opaque */
            color: #e8d8c3;
            border: 2px solid #5a3921;
            border-radius: 8px;
            padding: 14px; /* Larger padding */
            font-size: 1.2rem; /* Larger input text */
            line-height: 1.6;
        }
        
        .stSlider > label {
            font-family: 'Cinzel', serif;
            color: #d4af37;
            font-weight: 600;
            font-size: 1.1rem; /* Larger slider label */
        }
        
        /* === HIGH VISIBILITY SIDEBAR === */
        .sidebar-section {
            background: rgba(30, 20, 10, 0.9) !important; /* More opaque */
            padding: 18px; /* More padding */
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid #d4af37; /* Gold border */
        }
        
        /* === FIX: Make ALL sidebar text readable === */
        .stSidebar .stMarkdown p,
        .stSidebar .stMarkdown span,
        .stSidebar .stMarkdown div,
        .stSidebar .stText p,
        .stSidebar .stText span {
            color: #f4e4c1 !important; /* Brighter text */
            font-size: 1.1rem !important; /* Larger */
            line-height: 1.7 !important; /* Better spacing */
            font-weight: 500 !important; /* Medium weight */
        }
        
        .inventory-item {
            background: rgba(90, 57, 33, 0.6); /* More opaque */
            padding: 10px 14px; /* Larger padding */
            margin: 6px 0;
            border-radius: 5px;
            border-left: 3px solid #d4af37;
            font-size: 1rem; /* Larger inventory text */
            color: #f4e4c1 !important; /* Brighter */
        }
        
        .sidebar-section h3 {
            color: #d4af37 !important; /* Gold headers */
            font-family: 'Cinzel', serif !important;
            font-size: 1.3rem !important; /* Larger */
            margin-bottom: 12px !important;
            font-weight: 700 !important;
        }
        
        .progress-text {
            font-family: 'Cinzel', serif;
            color: #d4af37;
            font-size: 1.3rem; /* Larger progress text */
            text-align: center;
            margin: 10px 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
            font-weight: 600;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Toast notifications */
        .stToast {
            background: rgba(30, 20, 10, 0.95) !important;
            border: 2px solid #d4af37 !important;
            font-size: 1.1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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
        # ------- TTS button for AI messages only -------
        if msg["role"] == "ai":
            # Butonul de ascultat
            if st.button("🔊 Ascultă", key=f"tts_{msg.get('turn', 0)}_{hash(msg['text'][:20])}"):
                speak(msg["text"])
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
    st.markdown('<p class="subtitle">Aventura în Secolul XV al lui Vlad Țepeș</p>', unsafe_allow_html=True)

def render_sidebar(character: Dict) -> int:
    """
    Render sidebar with controls, character sheet, and save/load
    Returns legend_scale value
    """
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
    health_pct = character["health"] / 100
    st.sidebar.text(f"❤️ Viață: {character['health']}/100")
    st.sidebar.markdown(
        f'<div class="stat-bar"><div class="stat-fill health-fill" style="width:{health_pct*100}%"></div></div>',
        unsafe_allow_html=True
    )
    
    # Reputation Bar
    rep_pct = character["reputation"] / 100
    st.sidebar.text(f"👑 Reputație: {character['reputation']}/100")
    st.sidebar.markdown(
        f'<div class="stat-bar"><div class="stat-fill reputation-fill" style="width:{rep_pct*100}%"></div></div>',
        unsafe_allow_html=True
    )
    
    # Location
    st.sidebar.text(f"📍 Locație: {character['location']}")
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # INVENTORY
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.subheader("🎒 Inventar")
    for item in character["inventory"]:
        st.sidebar.markdown(f'<div class="inventory-item">{item}</div>', unsafe_allow_html=True)
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # SAVE / LOAD STORY
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.subheader("💾 Salvează Aventura")
    
    # === FIX: Exclude images from JSON to avoid serialization error ===
    json_friendly_story = [
        {k: v for k, v in msg.items() if k != "image"}
        for msg in st.session_state.story
    ]
    
    story_data = {
        "story": json_friendly_story,
        "character": st.session_state.character,
        "turn": st.session_state.turn,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    json_str = json.dumps(story_data, ensure_ascii=False, indent=2)
    
    st.sidebar.download_button(
        "📥 Descarcă JSON",
        data=json_str.encode("utf-8"),
        file_name=f"aventura_wallachia_{int(time.time())}.json",
        mime="application/json",
        use_container_width=True
    )
    
    st.sidebar.markdown("---")
    
    # JSON Load
    uploaded = st.sidebar.file_uploader(
        "📂 Încarcă Aventură (JSON)",
        type=["json"],
        key="load_story"
    )
    if uploaded:
        try:
            data = json.load(uploaded)
            if "story" in data:
                st.session_state.story = [
                    {**msg, "image": None} for msg in data["story"]
                ]
                st.session_state.character = data.get("character", character)
                st.session_state.turn = data.get("turn", 0)
                st.sidebar.success("✅ Aventură încărcată!")
                time.sleep(0.5)
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ Eroare încărcare: {e}")
    
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # PDF SAVE
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.subheader("🧾 Export PDF")
    
    if st.sidebar.button("⚡ Generează PDF", use_container_width=True):
        with st.spinner("Se creează documentul..."):
            html = generate_pdf_html(st.session_state.story)
            try:
                tmp_path = f"/tmp/aventura_{uuid.uuid4().hex}.pdf"
                pdfkit.from_string(html, tmp_path)
                with open(tmp_path, 'rb') as f:
                    st.sidebar.download_button(
                        "📄 Descarcă PDF",
                        f.read(),
                        "aventura_wallachia.pdf",
                        "application/pdf",
                        use_container_width=True
                    )
                os.unlink(tmp_path)
            except Exception as e:
                st.sidebar.error(f"❌ Eroare PDF: {e}")
    
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
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
