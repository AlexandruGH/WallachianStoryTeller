import os
import sys
import json
import time
import threading
from unittest.mock import MagicMock
from dotenv import load_dotenv
load_dotenv(override=True)

# Mock streamlit before importing modules that use it
streamlit_mock = MagicMock()
sys.modules["streamlit"] = streamlit_mock
sys.modules["streamlit.runtime"] = MagicMock()
sys.modules["streamlit.runtime.scriptrunner"] = MagicMock()

import streamlit as st
st.session_state = {}
st.error = print
st.warning = print
st.info = print

from models import GameState, CharacterStats, InventoryItem, ItemType, NarrativeResponse, CharacterClassType, FactionType, GameMode
from config import Config
from caching import CacheManager
from campaign import CAMPAIGN_EPISODES # Needed for content_data

CONFIGS = [
    {
        "source": "story_packs/episode_1/negustor_draculesti_source.json",
        "output": "story_packs/episode_1/negustor_draculesti.json",
        "class": CharacterClassType.NEGUSTOR,
        "faction": FactionType.DRACULESTI,
        "stats": {"charisma": 2, "negotiation": 1, "intelligence": 1},
        "desc": "Manual DM Flow for Negustor Drăculești Episode 1"
    }
]

# Global variable to hold current story tree
CURRENT_STORY_TREE = {}

def load_story_tree(path):
    global CURRENT_STORY_TREE
    try:
        with open(path, "r", encoding="utf-8") as f:
            CURRENT_STORY_TREE = json.load(f)
            print(f"Loaded story tree from {path} with {len(CURRENT_STORY_TREE)} keys.")
    except Exception as e:
        print(f"Error loading story tree {path}: {e}")
        CURRENT_STORY_TREE = {}

def generate_manual_response(user_action, prompt_text):
    """
    Matches the specific user action to the story tree.
    """
    # Direct match attempt
    if user_action in CURRENT_STORY_TREE:
        data = CURRENT_STORY_TREE[user_action]
        return NarrativeResponse(**data)
    
    for key in CURRENT_STORY_TREE.keys():
        if key in user_action:
            data = CURRENT_STORY_TREE[key]
            return NarrativeResponse(**data)
    
    # Warn if fallback hit
    print(f"[WARN] Fallback triggered for action: '{user_action}'")
    return NarrativeResponse(
        narrative="Acțiunea ta nu a avut efectul scontat. Situația e confuză. Trebuie să iei o decizie clară.",
        suggestions=["Privește în jur.", "Așteaptă.", "Încearcă altceva."],
        episode_progress=0.0
    )

def run_single_generation(cfg, turns=14):
    print(f"\n=== GENERATING: {cfg['class'].value} / {cfg['faction'].value} ===")
    
    load_story_tree(cfg['source'])
    
    # Create character with default stats first, then apply class/faction
    character = CharacterStats()
    # Apply class stats
    from character_creation import apply_character_class_stats, apply_faction_modifiers
    apply_character_class_stats(character, cfg['class'])
    apply_faction_modifiers(character, cfg['faction'])
    character.game_mode = GameMode.CAMPAIGN
    character.current_episode = 1
    character.location = "Târgoviște"
    
    # MATCH app.py DEFAULTS EXACTLY for correct hashing
    inventory = [
        InventoryItem(name="Pumnal", type=ItemType.weapon, value=3, quantity=1),
        InventoryItem(name="Hartă ruptă", type=ItemType.misc, value=0, quantity=1),
        InventoryItem(name="5 galbeni", type=ItemType.currency, value=5, quantity=1),
    ]
    
    # Use campaign.py suggestions for Turn 0
    # NOTE: app.py uses CAMPAIGN_EPISODES[1]["initial_suggestions"]
    ep1 = CAMPAIGN_EPISODES[1]
    suggestions_turn_0 = ep1.get("initial_suggestions", [])
    
    # REPLICATE app.py (Campaign) State
    # app.py clears text for Campaign intro
    game_state = GameState(
        character=character,
        inventory=inventory,
        story=[{
            "role": "ai",
            "text": "", # EMPTY to match app.py Campaign Start
            "turn": 0,
            "image": None,
            "type": "episode_intro",
            "content_data": ep1,
            "suggestions": suggestions_turn_0
        }],
        turn=0,
        last_image_turn=-10
    )
    
    CacheManager._ensure_cache_dir()
    
    # To store in bundle
    generated_cache = {}

    for i in range(turns):
        print(f"  [TURN {i}]")
        
        last_ai_msg = game_state.story[-1]
        suggestions = last_ai_msg.get("suggestions", [])
        
        if not suggestions:
            print("    No suggestions found! Stopping.")
            break
            
        responses = {}
        
        # Generate for ALL suggestions
        for sug in suggestions:
            temp_story = game_state.story + [{
                "role": "user",
                "text": sug,
                "turn": game_state.turn,
                "image": None
            }]
            
            # IMPORTANT: model_dump with mode='json' to match app.py/db serialization
            prompt = Config.build_dnd_prompt(
                story=temp_story,
                character=game_state.character.model_dump(mode='json'),
                legend_scale=5,
                game_mode=game_state.character.game_mode,
                current_episode=game_state.character.current_episode
            )
            
            # Generate & Cache
            resp = generate_manual_response(sug, prompt)
            responses[sug] = resp
            
            # Get hash to store in bundle
            key_hash = CacheManager._get_hash(prompt)
            generated_cache[key_hash] = resp.model_dump(mode='json')
            
            # Also set in CacheManager for runtime check consistency
            CacheManager.set(prompt, resp)

        # Advance Logic (Pick best match from Tree)
        chosen_sug = suggestions[0]
        best_sug = None
        for s in suggestions:
            if s in CURRENT_STORY_TREE:
                best_sug = s
                break
        if best_sug:
            chosen_sug = best_sug
        
        chosen_resp = responses.get(chosen_sug)
        print(f"    >>> Selected: {chosen_sug}")
        
        # Update State
        c = game_state.character
        c.health = max(0, min(100, c.health + (chosen_resp.health_change or 0)))
        c.reputation = max(0, min(100, c.reputation + (chosen_resp.reputation_change or 0)))
        c.gold = max(0, c.gold + (chosen_resp.gold_change or 0))
        if chosen_resp.location_change:
            c.location = chosen_resp.location_change
            
        for item in chosen_resp.items_gained:
             # simplistic inventory add
             game_state.inventory.append(item)
                
        game_state.story.append({
            "role": "user",
            "text": chosen_sug,
            "turn": game_state.turn,
            "image": None
        })
        
        game_state.story.append({
            "role": "ai",
            "text": chosen_resp.narrative,
            "turn": game_state.turn,
            "image": None,
            "suggestions": chosen_resp.suggestions
        })
        
        game_state.turn += 1
        
        if chosen_resp.episode_progress is not None:
            c.episode_progress = chosen_resp.episode_progress
            if c.episode_progress >= 1.0:
                print("    Episode Completed!")
                break

    # Save Bundle
    bundle = {
        "character_class": str(cfg['class'].value),
        "faction": str(cfg['faction'].value),
        "episode": 1,
        "description": cfg['desc'],
        "cache_data": generated_cache
    }
    
    os.makedirs("story_packs", exist_ok=True)
    with open(cfg['output'], "w", encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(generated_cache)} entries to {cfg['output']}")


def main():
    for cfg in CONFIGS:
        run_single_generation(cfg)

if __name__ == "__main__":
    main()
