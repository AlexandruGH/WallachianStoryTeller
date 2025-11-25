# image_handler.py  –  two-tier fallback for image generation
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from huggingface_hub import InferenceClient
from io import BytesIO
import requests
from typing import Optional, List
import threading
import time
import os
from config import Config

# ========== 1. LISTA MODELELOR (ordinea = prioritate) ==========
IMAGE_MODELS: List[str] = [
    "stabilityai/stable-diffusion-xl-base-1.0"      # 2nd choice
]
# ===============================================================

# Thread-safe rotation pentru HF tokens
_hf_token_index = 0
_hf_token_lock = threading.Lock()

# client unic pentru toate apelurile
client = InferenceClient(
    provider="nscale",
    api_key=os.getenv("HF_TOKEN"),   # ← asigură-te că există
    timeout=120
)

def get_session_id():
    """Obține ID-ul de sesiune din Streamlit session_state"""
    return st.session_state.get('session_id', 'UNKNOWN_SESSION')

def get_hf_tokens() -> List[str]:
    """Citește TOATE token-urile HF: HF_TOKEN, HF_TOKEN1, HF_TOKEN2, etc."""
    tokens = []
    # Token principal
    token = os.getenv("HF_TOKEN")
    if token and token.strip():
        tokens.append(token.strip())
    
    # Tokeni secundari (HF_TOKEN1, HF_TOKEN2, ...)
    i = 1
    while True:
        token = os.getenv(f"HF_TOKEN{i}")
        if token and token.strip():
            tokens.append(token.strip())
            i += 1
        else:
            break
    
    # Elimină duplicate păstrând ordinea
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)
    
    return unique_tokens


def generate_scene_image(text: str, is_initial: bool = False) -> Optional[bytes]:
    """
    Generează imagine cu rotație inteligentă a token-urilor HF.
    La fiecare request se rotește la următorul token. Dacă un token eșuează,
    se încearcă automat următorul din listă.
    """
    session_id = get_session_id()  # ⭕ OBTINE ID SESIUNE
    tokens = get_hf_tokens()
    if not tokens:
        print(f"[SESSION {session_id}] 🔒 NO HF TOKENS - OFFLINE MODE")  # ⭕ LOG
        st.info("🔒 Mod offline – generăm imagine de rezervă...")
        return generate_fallback_image(text, is_initial)
    print(f"[SESSION {session_id}] 🎨 GENERATING IMAGE: {text[:100]}...")  # ⭕ LOG PROMPT
    # Rotation logic: determinăm token-ul de start pentru acest request
    global _hf_token_index
    with _hf_token_lock:
        start_index = _hf_token_index
        # Incrementăm pentru următorul request
        _hf_token_index = (_hf_token_index + 1) % len(tokens)
    
    location = st.session_state.character.get("location", "Târgoviște")
    prompt = Config.generate_image_prompt_llm(text, location)

    # Încercăm fiecare token începând de la index-ul rotit
    for i in range(len(tokens)):
        token_index = (start_index + i) % len(tokens)
        token = tokens[token_index]
        
        # Afișăm doar dacă avem mai multe token-uri
        if len(tokens) > 1:
            st.toast(f"🎨 Folosind token-ul HF {token_index + 1}/{len(tokens)}", icon="🔄")
        print(f"[SESSION {session_id}] 🎨 USING HF TOKEN {token_index + 1}")  # ⭕ LOG TOKEN
        # Încercăm fiecare model cu acest token
        for model in IMAGE_MODELS:
            try:
                client = InferenceClient(
                    provider="nscale",
                    api_key=token,
                    timeout=120
                )
                print(f"[SESSION {session_id}] ✅ Token {token_index + 1}, Model {model}, IMAGE Prompt: {prompt}")  # ⭕ LOG
                with st.spinner("🎨 Artistul medieval lucrează..."):
                    pil_img = client.text_to_image(
                        prompt,
                        model=model,
                        negative_prompt=Config.IMAGE_NEGATIVE,
                        num_inference_steps=30,
                        guidance_scale=7.5,
                    )
                if pil_img:
                    print(f"[SESSION {session_id}] ✅ IMAGE SUCCESS (Token {token_index + 1}, Model {model})")  # ⭕ LOG
                    return pil_to_bytes(pil_img)
            except Exception as e:
                print(f"[SESSION {session_id}] ❌ IMAGE FAIL (Token {token_index + 1}, Model {model}): {e}")  # ⭕ LOG
                st.warning(f"⚠️ Token {token_index + 1} / Model {model} a eșuat: {e}")
                continue  # Trecem la următorul model
        
        # Dacă toate modelele au eșuat pentru acest token, continuăm cu următorul token
    
    # Dacă toate token-urile și modelele au eșuat
    print(f"[SESSION {session_id}] ❌ ALL IMAGE TOKENS FAILED")  # ⭕ LOG
    st.error("❌ Toate token-urile și modelele de imagine au eșuat.")
    return generate_fallback_image(text, is_initial)

# ---------- helper ----------
def pil_to_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------- restul funcțiilor rămân identice ----------
def generate_fallback_image(text: str, is_initial: bool) -> bytes:
    try:
        img = Image.new('RGB', (768, 512), color='#0d0704')
        draw = ImageDraw.Draw(img)
        for y in range(512):
            shade = int((y / 512) * 30)
            draw.line([(0, y), (768, y)], fill=f'#{shade:02x}{shade//2:02x}{shade//3:02x}')
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 70)
            subfont = ImageFont.truetype("DejaVuSans.ttf", 30)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 70)
                subfont = ImageFont.truetype("arial.ttf", 30)
            except:
                font = ImageFont.load_default(); subfont = font

        msg = "WALLACHIA" if is_initial else "Scenă Medievală"
        submsg = "Anno Domini 1456" if is_initial else "(Mod Offline)"

        bbox = draw.textbbox((0, 0), msg, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (768 - w) / 2, (512 - h) / 2 - 40
        draw.text((x + 2, y + 2), msg, font=font, fill='#000000')
        draw.text((x, y), msg, font=font, fill='#d4af37')

        bbox2 = draw.textbbox((0, 0), submsg, font=subfont)
        w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
        draw.text(((768 - w2) / 2, (512 + h) / 2 - 20), submsg,
                  font=subfont, fill='#5a3921')

        img = ImageOps.expand(img, border=10, fill='#5a3921')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    except Exception as e:
        img = Image.new('RGB', (512, 512), color='#1a0f0b')
        buffer = BytesIO(); img.save(buffer, format='PNG')
        return buffer.getvalue()

