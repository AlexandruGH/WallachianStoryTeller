import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from huggingface_hub import InferenceClient
from io import BytesIO
import requests
from typing import Optional, List
import threading
import time
import os
from config import Config

# Lista modelelor (prioritate descrescătoare)
IMAGE_MODELS: List[str] = [
    "stabilityai/stable-diffusion-xl-base-1.0"
]

# Thread-safe rotation pentru token-uri HF
_hf_token_index = 0
_hf_token_lock = threading.Lock()

# Client unic
client = InferenceClient(
    provider="nscale",
    api_key=os.getenv("HF_TOKEN"),
    timeout=120
)

def get_session_id():
    return st.session_state.get('session_id', 'UNKNOWN_SESSION')

def get_hf_tokens() -> List[str]:
    """Citește TOATE token-urile HF: HF_TOKEN, HF_TOKEN1, HF_TOKEN2, etc."""
    tokens = []
    token = os.getenv("HF_TOKEN")
    if token and token.strip():
        tokens.append(token.strip())
    
    i = 1
    while True:
        token = os.getenv(f"HF_TOKEN{i}")
        if token and token.strip():
            tokens.append(token.strip())
            i += 1
        else:
            break
    
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)
    
    return unique_tokens

def pil_to_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generate_scene_image(text: str, is_initial: bool = False) -> Optional[bytes]:
    """
    Generează imagine folosind Hugging Face API. Dacă toate token-urile și modelele eșuează,
    returnează None (fără fallback).
    """
    session_id = get_session_id()
    tokens = get_hf_tokens()
    
    if not tokens:
        print(f"[SESSION {session_id}] 🔒 NU EXISTĂ TOKEN-URI HF - IMAGINEA NU SE GENEAZĂ")
        return None
    
    global _hf_token_index
    with _hf_token_lock:
        start_index = _hf_token_index
        _hf_token_index = (_hf_token_index + 1) % len(tokens)
    
    location = st.session_state.character.get("location", "Târgoviște")
    prompt = Config.generate_image_prompt_llm(text, location)

    for i in range(len(tokens)):
        token_index = (start_index + i) % len(tokens)
        token = tokens[token_index]
        
        print(f"[SESSION {session_id}] 🎨 ÎNCERC TOKEN {token_index + 1}")
        
        for model in IMAGE_MODELS:
            try:
                client = InferenceClient(
                    provider="nscale",
                    api_key=token,
                    timeout=120
                )
                
                print(f"[SESSION {session_id}] ✅ Token {token_index + 1}, Model {model}")
                
                with st.spinner("🎨 Artistul medieval lucrează..."):
                    pil_img = client.text_to_image(
                        prompt,
                        model=model,
                        negative_prompt=Config.IMAGE_NEGATIVE,
                        num_inference_steps=30,
                        guidance_scale=7.5,
                    )
                
                if pil_img:
                    print(f"[SESSION {session_id}] ✅ IMAGINE GENERATĂ (Token {token_index + 1})")
                    return pil_to_bytes(pil_img)
            
            except Exception as e:
                print(f"[SESSION {session_id}] ❌ EȘEC IMAGINE (Token {token_index + 1}, Model {model}): {e}")
                continue
    
    # TOATE TOKEN-URILE ȘI MODELELE AU EȘUAT
    print(f"[SESSION {session_id}] ❌ TOATE TOKEN-URILE ȘI MODELELE DE IMAGINE AU EȘUAT")
    st.warning("⚠️ Generarea imaginilor este temporar indisponibilă.")
    return None