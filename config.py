# config.py - Model Router & Romanian-Aware Configuration
import re
import streamlit as st
from typing import List, Dict, Any
from deep_translator import GoogleTranslator
import os
import random
import requests
from models import NarrativeResponse

class Config:
    """Central configuration with Romanian-optimized models"""

    PRIMARY_API_MODEL = "dumitrescustefan/bloom-1b1-romanian"
    FALLBACK_API_MODELS = [
        "microsoft/DialoGPT-medium",
        "facebook/xglm-564M",
        "bigscience/bloom-560m"
    ]
    LOCAL_MODEL = "EleutherAI/gpt-neo-1.3B"

    IMAGE_MODEL = "stabilityai/stable-diffusion-2-1"
    IMAGE_INTERVAL = 3
    IMAGE_NEGATIVE = "modern, cartoon, anime, text, watermark, lowres, blurry, extra limbs"
    

    @staticmethod
    def make_intro_text(scale: int) -> str:
        # Propoziții istorice
        historical_sentences = [
            "Vlad Țepeș, domnitor al Țării Românești, a condus cu o mână de fier între anii 1448 și 1476.",
            "Cetățile de la poalele Carpaților au fost întărite sub domnia lui, pentru a apăra țara de invazii.",
            "Metodele sale dure i-au adus atât respect, cât și teamă în rândul dușmanilor și al supușilor.",
            "Târgoviște era inima puterii, locul unde deciziile puteau schimba soarta unui întreg popor.",
            "Cronici vechi îl descriu ca pe un strateg necruțător, dar drept."
        ]

        # Propoziții legendare
        legendary_sentences = [
            "Se spune că umbrele nopții prindeau viață în prezența lui.",
            "Bătrânii șoptesc că putea chema creaturi ascunse în bezna pădurilor.",
            "Legenda afirmă că aerul se răcea brusc când Vlad se mânia.",
            "Unii credeau că străvechi spirite îl protejau în luptă.",
            "Se povestește că sângele dușmanilor îi întărea puterea."
        ]

        # Transformăm scale într-un raport 0-1
        ratio = min(max(scale / 10.0, 0), 1)

        # Număr de propoziții istorice vs legendare
        num_hist = max(1, int((1 - ratio) * 3))  
        num_leg = max(1, int(ratio * 3))         

        # Alegem propoziții random
        chosen_hist = random.sample(historical_sentences, num_hist)
        chosen_leg = random.sample(legendary_sentences, num_leg)

        # Le mixăm
        mixed_sentences = chosen_hist + chosen_leg
        random.shuffle(mixed_sentences)

        mixed_text = " ".join(mixed_sentences)

        # Intro narativ
        return (
        "Țara Românească, 1456. "
        + mixed_text
        + "\n\n"        
        )

    @staticmethod
    def build_dnd_prompt(story: List[Dict], character: Dict, legend_scale: int = 5) -> str:
        """Construiește prompt pentru LLM folosind structuri de date simple (dict/list)"""
        from models import NarrativeResponse # Import local
        
        # Calcul raport legend vs istoric
        ratio = legend_scale / 10.0
        
        # Selectare prefix stil
        if ratio < 0.3:
            style_prefix = "Stil STRICT ISTORIC. Fără magie, fără creaturi fantastice. "
        elif ratio > 0.7:
            style_prefix = "Stil LEGENDAR VAMPIRIC. Umbre, mister, folklore întunecat. "
        else:
            style_prefix = "Stil echilibrat istoric și legendar. "
        
        # Construire context narativ din ultimele replici
        context = "\n".join([f"{m['role'].upper()}: {m['text']}" for m in story[-4:]])
        
        # Construire Info caracter (Accesăm prin CHEI de dicționar ['key'], nu prin punct .attr)
        # Verificăm existența cheilor cu .get() pentru siguranță
        char_health = character.get('health', 100)
        char_rep = character.get('reputation', 20)
        char_gold = character.get('gold', 0)
        char_loc = character.get('location', 'Târgoviște')
        
        power_desc = 'SLABĂ'
        if char_rep >= 60: power_desc = 'CRESCUTĂ'
        elif char_rep >= 30: power_desc = 'MEDIE'

        char_info = (
            f"\n\nSTATISTICI CRITICE: Viață={char_health} | "
            f"Reputație={char_rep} | "
            f"Locație={char_loc} | "
            f"Galbeni={char_gold} | "
            f"Puterea ta este {power_desc}\n"
        )
        
        # Restricții bazate pe reputație
        restrictions = ""
        if char_rep < 20:
            restrictions = "Jucătorul are reputație FOARTE JOSĂ. Este tratat cu suspiciune. Nu poate intra în audiență la boieri. "
        elif char_rep < 50:
            restrictions = "Jucătorul are reputație MEDIE. Poate interacționa cu negustori și soldați, dar nu cu înalta nobilime. "
        else:
            restrictions = "Jucătorul are reputație BUNĂ. Poate cere audiențe, dar ȚEPEȘ este INACCESIBIL direct fără motiv întemeiat. "
        
        # Schema JSON
        schema = NarrativeResponse.model_json_schema()
        
        # Construire instrucțiuni finale
        instructions = (
            f"\n{style_prefix}{restrictions}"            
            "REGULI OBLIGATORII:\n"
            "- 'narrative': 2-3 propoziții, fără greșeli gramaticale, în română medievală\n"
            "- 'suggestions': Listă de EXACT 2-3 string-uri, fără numere, fără bullet points\n"
            "  EXEMPLU: [\"Cere audiență la curte.\", \"Caută informații în târg.\", \"Explorezi adâncul pădurii.\"]\n"
            "- Respectă gramatica: 'unei păsări', 'unor boieri', nu 'unui păsări'\n"
            "VLAD ȚEPEȘ NU POATE FI ÎNVINS – orice tentativă = game_over instant\n"
            "Reputația sub 20 = nu poți interacționa cu nobilii\n\n"
            f"Răspunde STRICT în format JSON conform schemei:\n"
            f"STRICT JSON SCHEMA:\n"
            f"```json\n{schema}\n```\n"
        )
    
        return context + char_info + instructions
    
    @staticmethod
    def generate_image_prompt_llm(text: str, location: str) -> str:
        """Generează prompt pentru Stable Diffusion folosind LLM"""
        token = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
        if not token:
            return Config.generate_image_prompt(text, location)

        system = (
            "You are an assistant that writes short, highly detailed prompts "
            "for Stable-Diffusion in English. "
            "Include: time of day, number of people, context, weather, camera angle, lighting style. "
            "Keep it under 200 characters. DO NOT include object names like 'candle'. "
            "Describe LIGHTING EFFECTS only: 'warm dim lighting', 'soft glow', 'moonlight'."
        )

        user = (
            f"Story fragment: {text}\n"
            f"Exact place: {location}\n"
            "Write one English Stable-Diffusion prompt with lighting effects, no objects."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.75,
            "max_tokens": 60,
            "stream": False
        }

        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            r.raise_for_status()
            llm_prompt = r.json()["choices"][0]["message"]["content"].strip()
            llm_prompt = llm_prompt.replace('"', '')
            if llm_prompt.endswith('.'):
                llm_prompt = llm_prompt[:-1]
            
            # Prompt final cu descriere de iluminare, nu obiecte
            prompt = (
                f"Romanian medieval Wallachia 1456, Vlad Tepes era, atmospheric, "
                f"dark fantasy, {llm_prompt}, highly detailed, oil-on-canvas, "
                f"warm dim lighting, soft orange glow, deep shadows, 4k, vintage parchment look"
            )
            return prompt
        except Exception as e:
            print("LLM image-prompt failed:", e)
            # Fallback la metoda veche
            return Config.generate_image_prompt(text, location)
        
    @staticmethod
    def generate_image_prompt(text: str, location: str) -> str:
        # Extragem ultimele 3 propoziții sau primele 150 caractere
        short = " ".join(text.split(".")[-3:]).strip()
        if len(short) < 20:
            short = text[:150]

        def translate_to_english(text: str) -> str:
            """Traduce textul românesc în engleză pentru Stable Diffusion"""
            try:        
                return GoogleTranslator(source='ro', target='en').translate(text)
            except Exception as e:
                print(f"⚠️ Eroare traducere: {e}")
                return text  # Fallback la română
        # **TRADUCERE în engleză**
        short_en = translate_to_english(short)
        location_en = translate_to_english(location)
        
        # Construim promptul în engleză
        prompt = (
            f"Romanian medieval Wallachia 1456, Vlad Tepes era, atmospheric, "
            f"dark fantasy, {location_en}, {short_en}, highly detailed, oil-on-canvas, "
            f"warm candle-light, 4k, vintage parchment look"
        )
        
        return prompt[:195]
    
    @staticmethod
    def generate_image_prompt_llm(text: str, location: str) -> str:
        """
        Ask the SAME Groq endpoint we use for narration to write a short
        Stable-Diffusion prompt in English, grounded in the *exact* place
        and current narrative moment.
        """
        token = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
        if not token:
            # fallback to old method if somehow no key
            return Config.generate_image_prompt(text, location)

        system = (
            "You are an assistant that writes short, highly detailed prompts "
            "for Stable-Diffusion in English. "
            "Include: time of day, number of people in the image, context, weather, "
            "camera angle and any information usefull for image generation. Keep it under 200 characters."
        )

        user = (
            f"Story fragment: {text}\n"
            f"Exact place: {location}\n"
            "Write one English Stable-Diffusion prompt."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.75,
            "max_tokens": 60,
            "stream": False
        }

        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            r.raise_for_status()
            llm_prompt = r.json()["choices"][0]["message"]["content"].strip()
            # 🔧 CLEAN: remove quotes and trailing period
            llm_prompt = llm_prompt.replace('"', '')
            if llm_prompt.endswith('.'):
                llm_prompt = llm_prompt[:-1]
            prompt = (
            f"Romanian medieval Wallachia 1456, Vlad Tepes era, atmospheric, "
            f"dark fantasy, {llm_prompt}, highly detailed, oil-on-canvas, "
            f"warm dim lighting, deep shadows, 4k, vintage parchment look"
        )
            return prompt
        except Exception as e:
            print("LLM image-prompt failed:", e)
            # graceful fallback
            return Config.generate_image_prompt(text, location)


class ModelRouter:
    def __init__(self):
        self.api_models = Config.FALLBACK_API_MODELS.copy()
        self.api_models.insert(0, Config.PRIMARY_API_MODEL)
        self.current_api_index = 0

    def get_next_api_model(self) -> str:
        model = self.api_models[self.current_api_index]
        self.current_api_index = (self.current_api_index + 1) % len(self.api_models)
        return model