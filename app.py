import os, sys, shutil
# If ffmpeg is NOT in PATH, then try local folder
#if not shutil.which("ffmpeg"):
#    local_ffmpeg = os.path.abspath("ffmpeg/bin")
#    if os.path.isfile(os.path.join(local_ffmpeg, "ffmpeg.exe")):
#        os.environ["PATH"] = local_ffmpeg + os.pathsep + os.environ["PATH"]
from dotenv import load_dotenv
load_dotenv(override=True) # SINGURUL apel necesar
# Suppress pydub's warning
#os.environ["PYDUB_NO_WARN"] = "1"
import streamlit as st
from typing import Optional, Dict, Any, List
import time
import random
import json
import uuid
import re
import requests
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Import module
from config import Config, ModelRouter
from character import CharacterSheet, roll_dice, update_stats
from ui_components import inject_css, render_header, render_sidebar, display_story
from llm_handler import fix_romanian_grammar, generate_narrative_with_progress, generate_with_api, generate_story_text_with_progress
from models import GameState, CharacterStats, InventoryItem, ItemType, NarrativeResponse
# =========================
# — Session State Initialization
# =========================
def init_session():
    """Initialize all session state variables with Pydantic models"""
    if "game_state" not in st.session_state:
        # ⭕ DEFINIM italic_flavour AICI - variabila locală necesară
        italic_flavour = (
            "*Te afli la marginea cetății Târgoviște, pe o noapte rece de toamnă. "
            "Flăcările torțelor dansează în vânt, proiectând umbre lungi pe zidurile masive. "
            "Porțile de stejar se ridică încet, cu un scârțâit apăsat, iar aerul miroase "
            "a fum, fier și pământ ud. În depărtare se aud cai și voci ale străjerilor. "
            "Fiecare decizie poate naște o legendă sau poate rămâne doar o filă de cronică...*\n\n"
        )
        
        # Inițializăm game_state cu Pydantic
        st.session_state.game_state = GameState(
            character=CharacterStats(),
            inventory=[
                InventoryItem(name="Pumnal valah", type=ItemType.weapon, value=3, quantity=1),
                InventoryItem(name="Hartă ruptă", type=ItemType.misc, value=0, quantity=1),
                InventoryItem(name="5 galbeni", type=ItemType.currency, value=5, quantity=1),
            ],
            story=[
                {
                    "role": "ai", 
                    "text": f"{Config.make_intro_text(5)}{italic_flavour}**Ce vrei să faci?**", 
                    "turn": 0, 
                    "image": None
                }
            ],
            turn=0,
            last_image_turn=-10
        )
    
    # Restul variabilelor session_state (compatibilitate)
    if "story" not in st.session_state:
        st.session_state.story = st.session_state.game_state.story
    if "turn" not in st.session_state:
        st.session_state.turn = st.session_state.game_state.turn
    if "character" not in st.session_state:
        # Compatibilitate cu cod vechi - poți elimina gradual aceste variabile
        st.session_state.character = st.session_state.game_state.character.model_dump()
    if "story_history" not in st.session_state:
        st.session_state.story_history = []  # ⬅️ FIX: Inițializarea listei de istoric
    
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False # Inițializarea flag-ului de procesare
        
    if "prompt_cache" not in st.session_state:
        st.session_state.prompt_cache = "" # Cache pentru prompturi
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

# =========================
# — Main Application
# =========================
def main():
    """Main app logic - inițializează și pornește jocul"""
    st.set_page_config(
        page_title="Wallachia - D&D Adventure",
        page_icon="⚔️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_css()
    init_session()

    # 🔥 Verifică fallback pe API după 3 eșecuri
    if st.session_state.settings.get("api_fail_count", 0) > 3:
        st.warning("⚠️ API a eșuat de 3+ ori. Se trece în modul local automat.")
        st.session_state.settings["use_api_fallback"] = False

    render_header()

    # ⭕ CRITICAL: Salvăm legend_scale în session_state pentru a fi accesibil peste tot
    # render_sidebar primește GameState și returnează valoarea slider-ului
    legend_scale = render_sidebar(st.session_state.game_state)
    st.session_state.legend_scale = legend_scale  # 🔥 STOCHEM PENTRU acces global

    # 🔥 Pornește worker-ul de imagini dacă există elemente în coadă
    start_image_worker()
    
    # Layout: coloane centrate pentru story
    col_left, col_center, col_right = st.columns([0.5, 4, 0.5])
    with col_center:
        display_story(st.session_state.game_state.story)

    # 🔥 Procesează input-ul jucătorului (folosește legend_scale din session_state)
    handle_player_input()

def start_image_worker():
    """Pornește thread-ul de imagine dacă e necesar"""
    if st.session_state.image_queue and not st.session_state.get("image_worker_active"):
        st.session_state.image_worker_active = True
        t = threading.Thread(target=background_image_gen, daemon=True)
        add_script_run_ctx(t)
        t.start()

def background_image_gen():
    """Generează imagine și o atașează - FĂRĂ st.rerun()"""
    from image_handler import generate_scene_image
    try:
        text, turn = st.session_state.image_queue.pop(0)
        location = st.session_state.character.get("location", "Târgoviște")
        img_bytes = generate_scene_image(text, is_initial=False)
        
        if img_bytes:
            # Căutăm de la sfârșit spre început (ultimul mesaj AI)
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
        # 🔧 FĂRĂ st.rerun() aici! Streamlit va detecta automat modificarea



def handle_player_input():
    """Procesează acțiunile jucătorului și APPEND sugestii la textul narativ"""
    from models import InventoryItem, ItemType
    
    # 🔥 GAME OVER CHECK - BLOCHEAZĂ ORICE ACȚIUNE DACĂ PLAYER-UL ESTE MORT
    if st.session_state.game_state.character.health <= 0:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.error("💀 **Ești mort! Aventura s-a încheiat.**")
            if st.button("🔄 Începe o nouă aventură", use_container_width=True):
                init_session()
                st.rerun()
        return  # Oprește executarea restului funcției

    col_left, col_centre, col_right = st.columns([0.5, 4, 0.5])
    with col_centre:
        # Formular pentru input
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

        # Procesăm acțiunea principală
        if submitted and user_action and user_action.strip():
            if st.session_state.is_generating:
                st.warning("⏳ Așteaptă finalizarea generării...")
                return
                        
            st.session_state.is_generating = True
            try:
                # Salvează acțiunea jucătorului
                current_turn = st.session_state.game_state.turn
                st.session_state.game_state.story.append(
                    {"role": "user", "text": user_action, "turn": current_turn, "image": None}
                )
                
                # 1. PREGĂTIREA DATELOR (Extragem datele simple din Session State)
                legend_scale = st.session_state.get("legend_scale", 5)
                gs_data = st.session_state.game_state

                # Verificăm dacă e obiect sau dict și extragem datele necesare pentru config
                if hasattr(gs_data, 'character'):
                    # Dacă e obiect Pydantic
                    character_data = gs_data.character.model_dump()
                    story_data = gs_data.story
                else:
                    # Dacă e deja dicționar (cum îl face uneori Streamlit)
                    character_data = gs_data['character']
                    story_data = gs_data['story']

                # 2. CONSTRUIREA PROMPTULUI (Returnează un string)
                # Aici se apelează funcția din config.py
                full_prompt_text = Config.build_dnd_prompt(
                    story=story_data, 
                    character=character_data, 
                    legend_scale=legend_scale
                )

                # 3. GENERAREA NARAȚIUNII (Se apelează API-ul cu textul construit mai sus)
                # Aici se apelează funcția din llm_handler.py
                response = generate_narrative_with_progress(full_prompt_text)
                # Corectează greșelile gramaticale
                corrected_narrative = fix_romanian_grammar(response.narrative)
                corrected_suggestions = [
                    fix_romanian_grammar(s) for s in response.suggestions 
                    if s and len(s) > 5
                ]
                
                # Fallback sugestii dacă LLM nu returnează
                if not corrected_suggestions:
                    corrected_suggestions = [
                        "Cauți un loc sigur pentru odihnă.",
                        "Cerți informații de la un localnic.",
                        "Explorezi zona cu atenție."
                    ]
                
                # 🔥 🔥 🔥 APPEND SUGESTII LA NARRATIV 🔥 🔥 🔥
                # Acesta este nucleul modificării - concatenăm sugestiile direct în text
                narrative_with_suggestions = corrected_narrative
                if corrected_suggestions:
                    narrative_with_suggestions += "\n\n**Posibile acțiuni:**"
                    narrative_with_suggestions += "\n".join([f"• {s}" for s in corrected_suggestions])
                
                # Update game state din response
                gs = st.session_state.game_state
                gs.character.health = max(0, min(100, gs.character.health + (response.health_change or 0)))
                gs.character.reputation = max(0, min(100, gs.character.reputation + (response.reputation_change or 0)))
                gs.character.gold = max(0, gs.character.gold + (response.gold_change or 0))
                
                # Update inventory
                for item in response.items_gained:
                    existing = next((i for i in gs.inventory if i.name == item.name), None)
                    if existing:
                        existing.quantity += item.quantity
                    else:
                        gs.inventory.append(item)
                gs.inventory = [i for i in gs.inventory if i.name not in response.items_lost]
                
                # Update locație
                if response.location_change:
                    gs.character.location = response.location_change
                    st.toast(f"📍 Locație nouă: {response.location_change}", icon="🗺️")
                
                # Adaugă efecte de status
                if response.status_effects:
                    gs.character.status_effects.extend(response.status_effects)
                
                # 🔥 ADĂUGĂ TEXTUL COMBINAT (NARRATIV + SUGESTII) LA STORY
                st.session_state.game_state.story.append({
                    "role": "ai",
                    "text": narrative_with_suggestions,  # AICI este textul final cu sugestii incluse
                    "turn": current_turn,
                    "image": None
                })
                
                # 🔥 DEBUG CONSOLĂ - Șterge sau comentează după testare
                print(f"\n{'='*60}")
                print(f"📤 NARRATIV FINAL (cu sugestii):")
                print(narrative_with_suggestions)
                print(f"{'='*60}\n")
                
                # Coadă imagine
                if (current_turn - st.session_state.last_image_turn) >= Config.IMAGE_INTERVAL:
                    st.session_state.image_queue.append((corrected_narrative, current_turn))
                    st.session_state.last_image_turn = current_turn
                
                # Increment turn și verifică game over
                gs.turn += 1
                if response.game_over or gs.character.health <= 0:
                    st.error("💀 **Aventura s-a încheiat.**")
                    st.session_state.is_game_over = True
                
                # Rerun pentru a afișa noul conținut
                st.rerun()

            except Exception as e:
                st.error(f"❌ Eroare în procesare: {e}")
                import traceback
                traceback.print_exc()
            finally:
                st.session_state.is_generating = False

        # Butoane secundare (zaruri și vindecare)
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