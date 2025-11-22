import streamlit as st
from typing import Optional, Dict, Any, List
import time
import random
import json
import uuid
import os
import re
import requests
import threading

# Import secure modules
from config import Config, ModelRouter
from llm_handler import generate_story_text_with_progress
from character import CharacterSheet, roll_dice, update_stats
from ui_components import inject_css, render_header, render_sidebar, display_story

# =========================
# — Session State Initialization
# =========================
def init_session():
    """Initialize all session state variables"""
    if "story" not in st.session_state:
        intro = Config.make_intro_text(5)
        st.session_state.story = [{"role": "ai", "text": intro, "turn": 0, "image": None}]
    if "turn" not in st.session_state:
        st.session_state.turn = 0
    if "character" not in st.session_state:
        st.session_state.character = CharacterSheet().to_dict()
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False
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

# =========================
# — Main Application
# =========================
def main():
    """Main app logic with modern LLM routing"""
    st.set_page_config(
        page_title="Wallachia - D&D Adventure",
        page_icon="⚔️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_css()
    init_session()

    if st.session_state.settings.get("api_fail_count", 0) > 3:
        st.warning("⚠️ API a eșuat de 3+ ori. Se trece în modul local automat.")
        st.session_state.settings["use_api_fallback"] = False

    render_header()
    legend_scale = render_sidebar(st.session_state.character)

    col_left, col_center, col_right = st.columns([0.5, 4, 0.5])
    with col_center:
        display_story(st.session_state.story)

    handle_player_input()

def handle_player_input():
    """Process actions, queue images, show suggestions"""
    import re

    if st.session_state.turn == 0 and len(st.session_state.story) == 1:
        st.markdown(
            '<div class="suggestions-box">'
            '<b>🕯️  Câteva idei ca să începi:</b><br/>'
            '1. Intră în cetate și caută un loc de odihnă la hanul “La Trei Coroane”.<br/>'
            '2. Strigă după straja de la poartă să afli știri despre Vlad.<br/>'
            '3. Explorezi drumul comercial către Rucăr în noapte.'
            '</div>',
            unsafe_allow_html=True
        )

    with st.form(key="action_form", clear_on_submit=True):
        user_action = st.text_input(
            "🗡️ Ce vrei să faci?",
            placeholder="Scrie acțiunea ta...",
            key="input_action"
        )
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            submitted = st.form_submit_button("⚔️ Continuă Aventura", use_container_width=True)
        with col2:
            dice_clicked = st.form_submit_button("🎲 Aruncă Zaruri", use_container_width=True)
        with col3:
            heal_clicked = st.form_submit_button("🏥 Vindecă", use_container_width=True)

    if submitted and user_action and user_action.strip():
        if st.session_state.is_generating:
            st.warning("⏳ Așteaptă finalizarea generării...")
            return
        st.session_state.is_generating = True
        try:
            st.session_state.story.append({"role": "user", "text": user_action, "turn": st.session_state.turn, "image": None})
            prompt = Config.build_dnd_prompt(st.session_state.story, st.session_state.character)
            use_api = st.session_state.settings.get("use_api_fallback", True)
            ai_text = generate_story_text_with_progress(prompt, use_api=use_api)
            if "api_rate_limit_hit" in ai_text:
                st.session_state.settings["use_api_fallback"] = False
                st.session_state.settings["api_fail_count"] = st.session_state.settings.get("api_fail_count", 0) + 1
                ai_text = generate_story_text_with_progress(prompt, use_api=False)
            else:
                st.session_state.settings["api_fail_count"] = 0
            update_stats(st.session_state.character, user_action, ai_text)
            st.session_state.story.append({"role": "ai", "text": ai_text, "turn": st.session_state.turn, "image": None})
            if (st.session_state.turn - st.session_state.last_image_turn) >= Config.IMAGE_INTERVAL:
                st.session_state.image_queue.append((ai_text, st.session_state.turn))
                st.session_state.last_image_turn = st.session_state.turn
            st.session_state.turn += 1
        except Exception as e:
            st.error(f"❌ Eroare: {e}")
        finally:
            st.session_state.is_generating = False
        st.rerun()

    elif dice_clicked:
        result = roll_dice()
        st.toast(f"🎲 Ai dat: {result}!", icon="⚔️")
        time.sleep(0.5)

    elif heal_clicked:
        char = CharacterSheet.from_dict(st.session_state.character)
        heal = roll_dice(8) + 5
        char.heal(heal)
        st.session_state.character = char.to_dict()
        st.toast(f"❤️ Te-ai vindecat cu {heal} puncte!", icon="✨")
        time.sleep(0.5)

        # ---------- declanșare IMAGINE ----------
    if st.session_state.image_queue and not st.session_state.get("image_worker_active"):
        st.session_state.image_worker_active = True
        ctx = st.runtime.scriptrunner.add_script_run_ctx
        t = threading.Thread(target=background_image_gen, daemon=True)
        ctx(t)                       # atașăm context Streamlit
        t.start()
        
def background_image_gen():
    from image_handler import generate_scene_image
    try:
        text, turn = st.session_state.image_queue.pop(0)
        location = st.session_state.character.get("location", "Târgoviște")
        img_bytes = generate_scene_image(text, is_initial=False)
        if img_bytes:
            for msg in st.session_state.story:
                if msg.get("turn") == turn and msg["role"] == "ai":
                    msg["image"] = img_bytes
                    break
    except Exception as e:
        print("BG image error:", e)
    finally:
        st.session_state.image_worker_active = False

if __name__ == "__main__":
    main()