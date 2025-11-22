# config.py - Model Router & Romanian-Aware Configuration
import streamlit as st
from typing import List, Dict, Any
import os

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
    IMAGE_INTERVAL = 4
    IMAGE_NEGATIVE = "modern, cartoon, anime, text, watermark, lowres, blurry, extra limbs"

    @staticmethod
    def get_api_token() -> str:
        try:
            return st.secrets["HF_API_TOKEN"]
        except (FileNotFoundError, KeyError):
            return os.getenv("HF_API_TOKEN", "")

    @staticmethod
    def make_intro_text(scale: int) -> str:
        historical = ("Vlad Țepeș, domnitor al Țării Românești între 1448 și 1476, "
                     "a consolidat cetăți și respect prin metode dure dar eficiente.")
        legendary = ("Se spune că umbrele nopții tremură la numele său și că putea "
                    "chema creaturi din întunericul cel mai adânc.")
        ratio = scale / 10.0
        hist_words = historical.split()
        leg_words = legendary.split()
        num_hist = max(5, int(len(hist_words)*(1-ratio)))
        num_leg = max(5, int(len(leg_words)*ratio))
        mixed = " ".join(hist_words[:num_hist] + leg_words[:num_leg])
        return (
            f"**Țara Românească, 1456. "
            f"{mixed}\n\n"
            "*Te afli la marginea cetății Târgoviște, pe o noapte rece de toamnă. "
            "Flăcările torțelor joacă în vânt, proiectând umbre lungi pe zidurile "
            "de piatră. Porțile de lemn masiv se ridică cu un scârțâit, iar în aer "
            "plutește miros de lemn ars și pământ reavăn. Fiecare alegere poate "
            "naște legendă sau poate fi înscrisă în cronici...*\n\n"
            "**Ce vrei să faci?**"
        )

    @staticmethod
    def build_dnd_prompt(story: List[Dict], character: Dict) -> str:
        context = "\n".join([
            f"{m['role'].upper()}: {m['text']}"
            for m in story[-4:]
        ])
        char_info = (
            f"\n\nSTATISTICI: Viață={character['health']} | "
            f"Reputație={character['reputation']} | "
            f"Locație={character['location']}\n"
        )
        instructions = (
            "\nRăspunde în română medievală scurt și captivant. "
            "Maxim 3 propoziții. Nu repeta textul."
        )
        return context + char_info + instructions + "\nNARATOR: "

    @staticmethod
    def generate_image_prompt(text: str, location: str) -> str:
        short = " ".join(text.split(".")[-3:]).strip()
        if len(short) < 20:
            short = text[:150]
        prompt = (
            f"Romanian medieval Wallachia 1456, Vlad Tepes era, atmospheric, "
            f"dark fantasy, {location}, {short}, highly detailed, oil-on-canvas, "
            f"warm candle-light, 4k, vintage parchment look"
        )
        return prompt[:195]

class ModelRouter:
    def __init__(self):
        self.api_models = Config.FALLBACK_API_MODELS.copy()
        self.api_models.insert(0, Config.PRIMARY_API_MODEL)
        self.current_api_index = 0

    def get_next_api_model(self) -> str:
        model = self.api_models[self.current_api_index]
        self.current_api_index = (self.current_api_index + 1) % len(self.api_models)
        return model