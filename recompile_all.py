import os
import json
import glob
from models import CharacterClassType, FactionType, NarrativeResponse, CharacterStats, GameState, InventoryItem, ItemType, GameMode
from campaign import CAMPAIGN_EPISODES
from config import Config
from caching import CacheManager

def compile_source_file(source_path):
    print(f"Compiling {source_path}...")
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source_content = json.load(f)
    except Exception as e:
        print(f"Error reading {source_path}: {e}")
        return
    
    filename = os.path.basename(source_path)
    folder = os.path.dirname(source_path)
    
    # Parse class/faction from filename
    parts = filename.replace("_source.json", "").split("_")
    c_str = parts[0] # e.g. "strajer"
    
    # Map string to Enum
    char_class = None
    for c in CharacterClassType:
        # Normalize enum value
        norm_enum = c.value.lower().replace("ă", "a").replace("â", "a").replace("î", "i").replace("ș", "s").replace("ț", "t")
        if norm_enum.startswith(c_str):
            char_class = c
            break
    
    if not char_class:
        print(f"Skipping {filename}: Unknown class {c_str}")
        return

    # Default faction
    faction = FactionType.DRACULESTI
    if len(parts) > 1:
        f_str = "_".join(parts[1:]) 
        for f in FactionType:
            norm_f = f.value.lower().replace("ă", "a").replace("â", "a").replace("î", "i").replace("ș", "s").replace("ț", "t").replace(" ", "_").replace("/", "_")
            if norm_f == f_str or f_str in norm_f:
                faction = f
                break
    
    if len(parts) == 1:
        output_filename = f"{c_str}_draculesti.json"
    else:
        output_filename = filename.replace("_source.json", ".json")
        
    output_path = os.path.join(folder, output_filename)
    
    # Extract episode number
    try:
        # folder is like "story_packs/episode_1"
        ep_str = os.path.basename(folder).split("_")[1]
        episode = int(ep_str)
    except:
        episode = 1

    character = CharacterStats()
    character.game_mode = GameMode.CAMPAIGN
    character.current_episode = episode
    character.location = CAMPAIGN_EPISODES.get(episode, {}).get("location", "Târgoviște")
    
    # Apply Class Stats
    if char_class == CharacterClassType.STRAJER:
        character.constitution = 1
        character.perception = 1
    elif char_class == CharacterClassType.SPION:
        character.agility = 1
        character.stealth = 2
    elif char_class == CharacterClassType.NEGUSTOR:
        character.charisma = 2
        character.negotiation = 1
    elif char_class == CharacterClassType.AVENTURIER:
        character.strength = 1
        character.charisma = 1

    inventory = [
        InventoryItem(name="Pumnal", type=ItemType.weapon, value=3, quantity=1),
        InventoryItem(name="Hartă ruptă", type=ItemType.misc, value=0, quantity=1),
        InventoryItem(name="5 galbeni", type=ItemType.currency, value=5, quantity=1),
    ]
    
    initial_suggs = CAMPAIGN_EPISODES.get(episode, {}).get("initial_suggestions", [])
    
    game_state = GameState(
        character=character,
        inventory=inventory,
        story=[{
            "role": "ai",
            "text": "",
            "turn": 0,
            "image": None,
            "type": "episode_intro",
            "content_data": CAMPAIGN_EPISODES.get(episode, {}),
            "suggestions": initial_suggs
        }],
        turn=0,
        last_image_turn=-10
    )
    
    generated_cache = {}
    
    current_suggestions = initial_suggs
    visited_keys = set()
    
    for _ in range(20):
        if not current_suggestions:
            break
            
        # Hash all current options
        for sug in current_suggestions:
            temp_story = game_state.story + [{
                "role": "user",
                "text": sug,
                "turn": game_state.turn,
                "image": None
            }]
            
            prompt = Config.build_dnd_prompt(
                story=temp_story,
                character=game_state.character.model_dump(mode='json'),
                legend_scale=5,
                game_mode=game_state.character.game_mode,
                current_episode=game_state.character.current_episode
            )
            
            resp_data = source_content.get(sug)
            if not resp_data:
                for k in source_content:
                    if k in sug:
                        resp_data = source_content[k]
                        break
            
            if resp_data:
                resp = NarrativeResponse(**resp_data)
                key_hash = CacheManager._get_hash(prompt)
                generated_cache[key_hash] = resp.model_dump(mode='json')

        chosen = current_suggestions[0]
        if chosen not in source_content:
             for s in current_suggestions:
                 if s in source_content:
                     chosen = s
                     break
        
        if chosen not in source_content or chosen in visited_keys:
            break
            
        visited_keys.add(chosen)
        resp_data = source_content[chosen]
        resp = NarrativeResponse(**resp_data)
        
        c = game_state.character
        c.health = max(0, min(100, c.health + (resp.health_change or 0)))
        c.reputation = max(0, min(100, c.reputation + (resp.reputation_change or 0)))
        c.gold = max(0, c.gold + (resp.gold_change or 0))
        
        game_state.story.append({"role": "user", "text": chosen, "turn": game_state.turn})
        game_state.story.append({"role": "ai", "text": resp.narrative, "turn": game_state.turn, "suggestions": resp.suggestions})
        game_state.turn += 1
        
        current_suggestions = resp.suggestions
        if resp.win_condition or (resp.episode_progress and resp.episode_progress >= 1.0):
            break

    bundle = {
        "character_class": char_class.value,
        "faction": faction.value,
        "episode": episode,
        "description": f"Recompiled Pack Ep {episode}",
        "cache_data": generated_cache
    }
    
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    # print(f"  Saved {len(generated_cache)} hashes to {output_filename}")

def main():
    files = glob.glob("story_packs/**/*_source.json", recursive=True)
    files += glob.glob("story_packs/*_source.json")
    
    print(f"Found {len(files)} source files.")
    for f in files:
        compile_source_file(f)

if __name__ == "__main__":
    main()
