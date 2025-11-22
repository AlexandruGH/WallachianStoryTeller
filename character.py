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
        self.reputation = 50
        self.max_reputation = 100
        self.inventory = ["Pumnal valah", "Hartă necoptată", "Foiță de pergament"]
        self.location = "Târgoviște"
        self.status_effects = []

    def to_dict(self) -> Dict:
        return self.__dict__

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
    if "primești" in response_lower:
        item_match = re.search(r'primești (?:un|o|unui|niște) ([\w\s]+)', response_lower)
        if item_match:
            new_item = item_match.group(1).strip()
            if new_item not in character["inventory"]:
                character["inventory"].append(new_item)
                st.toast(f"🎒 Obiect nou: {new_item}!", icon="📦")