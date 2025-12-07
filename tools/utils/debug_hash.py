import json
import hashlib
import sys
import os

# Add root directory to path to allow importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from models import CharacterStats, GameMode, CharacterClassType, FactionType
from config import Config
from campaign import CAMPAIGN_EPISODES

def get_hash(text):
    return hashlib.sha512(text.encode('utf-8')).hexdigest()

def debug():
    # Simulate Compiler State Construction
    episode = 1
    char_class = CharacterClassType.STRAJER
    faction = FactionType.DRACULESTI
    
    character = CharacterStats(
        game_mode=GameMode.CAMPAIGN,
        current_episode=episode,
        location="Târgoviște" # MATCHING COMPILER
    )
    
    # Apply Stats (MATCHING COMPILER FIX)
    character.character_class = char_class
    character.constitution = 1
    character.perception = 1
    character.archery = 1 
    character.special_ability = "Scutul Frontierei – primești un bonus defensiv dacă aperi un loc, obiect sau persoană."
    
    character.passive_ability = "Frica de Domn – adversarii slabi se intimidează mai ușor când află cine ești."
    character.faction = FactionType.DRACULESTI
    
    # Story
    initial_suggs = CAMPAIGN_EPISODES.get(episode, {}).get("initial_suggestions", [])
    initial_story = [{
        "role": "ai",
        "text": "",
        "turn": 0,
        "image": None,
        "type": "episode_intro",
        "content_data": CAMPAIGN_EPISODES.get(episode, {}),
        "suggestions": initial_suggs
    }]
    
    # User Action
    sug = "Mă apropii discret de carul negru."
    
    story = initial_story + [{
        "role": "user",
        "text": sug,
        "turn": 0,
        "image": None
    }]
    
    # Build Prompt
    prompt = Config.build_dnd_prompt(
        story=story,
        character=character.model_dump(mode='json'),
        legend_scale=0, # MATCHING COMPILER
        game_mode=character.game_mode,
        current_episode=character.current_episode
    )
    
    h = get_hash(prompt)
    print(f"Generated Hash (SHA-512): {h}")
    
    # Check if in file
    try:
        # Path relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "../../story_packs/episode_1/strajer_draculesti.json")
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if h in data.get("cache_data", {}):
                print("✅ Hash FOUND in file!")
            else:
                print("❌ Hash NOT found in file.")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    debug()
