# character.py - Character management system
import random
import re
from typing import Dict, List
import streamlit as st

class CharacterSheet:
    def __init__(self):
        self.name = "Aventurier Misterios"
        self.health = 100
        self.max_health = 100
        self.reputation = 20  # START MAI JOS
        self.max_reputation = 100
        self.inventory = ["Pumnal", "Hartă ruptă", "Foiță de pergament"]
        self.gold = 5  # Adăugăm monede
        self.location = "Târgoviște"
        self.status_effects = []
        self.power_level = 1  # NIVEL DE PUTERE
        self.gold = 5
        self.inventory = [
            {"name": "Pumnal", "type": "armă", "value": 3},
            {"name": "Hartă ruptă", "type": "obiect", "value": 0},
            {"name": "Foiță de pergament", "type": "obiect", "value": 0},
            {"name": "5 galbeni", "type": "monedă", "value": 5}
        ]

    def to_dict(self) -> Dict:
        return self.__dict__
    
    def can_interact_with(self, target_tier: str) -> bool:
        """GATE logic: jucătorul nu poate interacționa cu entități de tier prea înalt"""
        tiers = {
            "țăran": 1,
            "negustor": 2,
            "soldat": 3,
            "căpitan": 4,
            "boier": 5,
            "domnitor": 10  # INACCESIBIL
        }
        
        required_tier = tiers.get(target_tier, 1)
        player_tier = max(1, self.reputation // 15)  # Reputația determină tier
        
        return player_tier >= required_tier
    
    @classmethod
    def from_dict(cls, data: Dict):
        char = cls()
        char.__dict__.update(data)
        return char

    def heal(self, amount: int):
        self.health = min(self.max_health, self.health + amount)

    def take_damage(self, amount: int):
        self.health = max(0, self.health - amount)

def roll_dice(sides: int = 20) -> int:
    return random.randint(1, sides)

def update_stats(character: Dict, action: str, response: str):
    action_lower = action.lower()
    response_lower = response.lower()
    if any(word in action_lower for word in ["onor", "noblețe", "datorie", "curaj", "ajută"]):
        rep_gain = roll_dice(10) + 2  # VALORI CRESCUTE
        character["reputation"] = min(100, character["reputation"] + rep_gain)
        st.toast(f"👑 Reputație +{rep_gain}!", icon="⭐")
    
    # Penalități mai severe
    elif any(word in action_lower for word in ["trădare", "laș", "minciună", "furt", "amenință"]):
        rep_loss = roll_dice(10) + 3
        character["reputation"] = max(0, character["reputation"] - rep_loss)
        st.toast(f"👑 Reputație -{rep_loss}!", icon="⬇️")
    if any(word in response_lower for word in ["rănit", "sânge", "atac", "răni", "durere", "te pierzi", "cazi"]):
        damage = roll_dice(10)
        character["health"] = max(0, character["health"] - damage)
        st.toast(f"💔 Ai pierdut {damage} puncte de viață!", icon="⚔️")
    elif any(word in response_lower for word in ["vindecat", "odihnă", "sigur", "refăcut", "te simți mai bine"]):
        heal = roll_dice(8)
        character["health"] = min(100, character["health"] + heal)
        st.toast(f"❤️ Te-ai vindecat cu {heal} puncte!", icon="✨")
    if any(word in action_lower for word in ["onor", "noblețe", "datorie", "curaj", "ajută", "protejează", "nobil"]):
        rep_gain = roll_dice(6)
        character["reputation"] = min(100, character["reputation"] + rep_gain)
        st.toast(f"👑 Reputație +{rep_gain}!", icon="⭐")
    elif any(word in action_lower for word in ["trădare", "laș", "minciună", "furt", "amenință", "ucide"]):
        rep_loss = roll_dice(6)
        character["reputation"] = max(0, character["reputation"] - rep_loss)
        st.toast(f"👑 Reputație -{rep_loss}!", icon="⬇️")
    # RESTRICȚIE PUTERNICĂ: Vlad Țepeș este invincibil
    # if "vlad" in response_lower and ("înfrânt" in response_lower or "învins" in response_lower):
    #     character["health"] = 0
    #     st.toast("💀 AI ÎNDRĂZNIT SĂ-L ÎNFRUNȚI PE VLAD?! MOARTE INSTANTANEE!", icon="☠️")
    if "primești" in response_lower:
        item_match = re.search(r'primești (?:un|o|unui|niște) ([\w\s]+)', response_lower)
        if item_match:
            new_item = item_match.group(1).strip()
            if new_item not in character["inventory"]:
                character["inventory"].append(new_item)
                st.toast(f"🎒 Obiect nou: {new_item}!", icon="📦")
    if "găsește" in response_lower or "primești" in response_lower:
        # Gold pattern
        gold_match = re.search(r'(\d+)\s*galben[i]', response_lower)
        if gold_match:
            gold_amount = int(gold_match.group(1))
            character["gold"] = character.get("gold", 0) + gold_amount
            st.toast(f"💰 +{gold_amount} galbeni!", icon="🪙")
        
        # Item pattern
        item_match = re.search(r'primești (?:un|o|niște) ([\w\s\-]+)', response_lower)
        if item_match:
            new_item = item_match.group(1).strip()
            # Evităm duplicatele
            existing_names = [item["name"] for item in character["inventory"]]
            if new_item not in existing_names:
                character["inventory"].append({
                    "name": new_item,
                    "type": "obiect",
                    "value": 0
                })
                st.toast(f"🎒 Obiect nou: {new_item}!", icon="📦")