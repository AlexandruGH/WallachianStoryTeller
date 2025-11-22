# image_handler.py - Image generation with medieval vintage filter
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from io import BytesIO
import requests
from typing import Optional
import os
from config import Config

def generate_scene_image(text: str, is_initial: bool = False) -> Optional[bytes]:
    token = Config.get_api_token()
    if not token:
        st.info("🔒 Mod offline: generăm imagine de rezervă...")
        return generate_fallback_image(text, is_initial)
    try:
        location = "Târgoviște"  # default
        prompt = Config.generate_image_prompt(text, location)
        headers = {"Authorization": f"Bearer {token}"}
        api_url = f"https://api-inference.huggingface.co/models/{Config.IMAGE_MODEL}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "negative_prompt": Config.IMAGE_NEGATIVE
            }
        }
        with st.spinner("🎨 Artistul medievale lucrează..."):
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return apply_vintage_effect(response.content)
        else:
            st.error(f"❌ API Imagine Eroare: {response.status_code}")
            return generate_fallback_image(text, is_initial)
    except requests.exceptions.Timeout:
        st.error("⏰ Timeout la generarea imaginii")
        return generate_fallback_image(text, is_initial)
    except Exception as e:
        st.error(f"❌ Eroare generare imagine: {e}")
        return generate_fallback_image(text, is_initial)

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
                font = ImageFont.load_default()
                subfont = font
        if is_initial:
            msg = "WALLACHIA"
            submsg = "Anno Domini 1456"
        else:
            msg = "Scenă Medievală"
            submsg = "(Mod Offline)"
        bbox = draw.textbbox((0, 0), msg, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (768-w)/2, (512-h)/2 - 40
        draw.text((x+2, y+2), msg, font=font, fill='#000000')
        draw.text((x, y), msg, font=font, fill='#d4af37')
        bbox2 = draw.textbbox((0, 0), submsg, font=subfont)
        w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
        draw.text(((768-w2)/2, (512+h)/2 - 20), submsg, font=subfont, fill='#5a3921')
        img = ImageOps.expand(img, border=10, fill='#5a3921')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    except Exception as e:
        img = Image.new('RGB', (512, 512), color='#1a0f0b')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

def apply_vintage_effect(image_bytes: bytes) -> bytes:
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.grayscale(img)
        img = img.filter(ImageFilter.SMOOTH)
        img = ImageOps.colorize(img, black="#1a0f0b", white="#e8d8c3", mid="#5a3921")
        img = add_vignette(img)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    except Exception as e:
        st.warning(f"⚠️ Filtrul vintage a eșuat: {e}")
        return image_bytes

def add_vignette(img: Image.Image) -> Image.Image:
    try:
        width, height = img.size
        vignette = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(vignette)
        center_x, center_y = width/2, height/2
        max_dist = (center_x**2 + center_y**2)**0.5
        for y in range(height):
            for x in range(width):
                dist = ((x-center_x)**2 + (y-center_y)**2)**0.5
                intensity = int(255 * (dist / max_dist) * 0.25)
                vignette.putpixel((x, y), intensity)
        shadow = Image.new('RGB', img.size, '#000000')
        img = Image.composite(img, shadow, vignette)
        return img
    except:
        return img