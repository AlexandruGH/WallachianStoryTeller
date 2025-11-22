# image_handler.py  –  two-tier fallback for image generation
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from huggingface_hub import InferenceClient
from io import BytesIO
import requests
from typing import Optional, List
import time
import os
from config import Config

# ========== 1. LISTA MODELELOR (ordinea = prioritate) ==========
IMAGE_MODELS: List[str] = [
    "stabilityai/stable-diffusion-xl-base-1.0"      # 2nd choice
]
# ===============================================================

# client unic pentru toate apelurile
client = InferenceClient(
    provider="nscale",
    api_key=os.environ["HF_TOKEN"],   # ← asigură-te că există
    timeout=120
)

def generate_scene_image(text: str, is_initial: bool = False) -> Optional[bytes]:
    token = Config.get_api_token()
    if not token:
        st.info("🔒 Mod offline – generăm imagine de rezervă...")
        return generate_fallback_image(text, is_initial)

    location = st.session_state.character.get("location", "Târgoviște")
    prompt = Config.generate_image_prompt(text, location)
    
    # Încercăm fiecare model
    for model in IMAGE_MODELS:
        try:
            with st.spinner(f"🎨 Artistul medievale lucrează..."):
                # Generează direct PIL.Image
                pil_img = client.text_to_image(
                    prompt,
                    model=model,
                    negative_prompt=Config.IMAGE_NEGATIVE,
                    num_inference_steps=30,
                    guidance_scale=7.5,
                )
            
            if pil_img:
                print(f"✅ Imagine generată cu succes folosind {model}")
                return pil_to_bytes(pil_img)
            
        except Exception as e:
            st.warning(f"⚠️ Model {model} a eșuat: {e}")
            continue
    
    st.error("❌ Toate modelele de imagine au eșuat.")
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

