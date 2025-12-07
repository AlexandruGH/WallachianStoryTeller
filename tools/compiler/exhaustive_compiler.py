import os
import sys
import json
import copy

# Add root directory to path to allow importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from models import CharacterClassType, FactionType, NarrativeResponse, CharacterStats, GameState, InventoryItem, ItemType, GameMode
from campaign import CAMPAIGN_EPISODES
from config import Config
from caching import CacheManager

# Limit recursion/depth to prevent infinite loops
MAX_DEPTH = 20 
MAX_STATES = 5000 # Safety break

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def compile_exhaustive(episode, char_class, faction, source_path, output_path):
    log_file = open("compiler_debug.log", "w", encoding='utf-8')
    def log(msg):
        log_file.write(str(msg) + "\n")
        log_file.flush()

    # Sanitize output for Windows console
    c_val = char_class.value.encode('ascii', 'ignore').decode('ascii')
    f_val = faction.value.encode('ascii', 'ignore').decode('ascii')
    log(f"\n=== EXHAUSTIVE COMPILATION: {c_val} / {f_val} (Ep {episode}) ===")
    log(f"Source: {source_path}")
    
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source_content = json.load(f)
    except Exception as e:
        log(f"Error reading source: {e}")
        return

    # 1. Setup Initial State
    character = CharacterStats(
        game_mode=GameMode.CAMPAIGN,
        current_episode=episode,
        location="Târgoviște" # Match runtime default, not campaign metadata yet
    )
    
    # Apply Class Stats (MATCHING character_creation.py)
    character.character_class = char_class
    if char_class == CharacterClassType.STRAJER:
        character.constitution = 1
        character.perception = 1
        character.archery = 1 # Was strength, fixed to match runtime
        character.special_ability = "Scutul Frontierei – primești un bonus defensiv dacă aperi un loc, obiect sau persoană."
    
    # Apply Faction Modifiers (MATCHING character_creation.py)
    if faction == FactionType.DRACULESTI:
        character.passive_ability = "Frica de Domn – adversarii slabi se intimidează mai ușor când află cine ești."
        character.faction = FactionType.DRACULESTI

    inventory = [
        InventoryItem(name="Pumnal", type=ItemType.weapon, value=3, quantity=1),
        InventoryItem(name="Hartă ruptă", type=ItemType.misc, value=0, quantity=1),
        InventoryItem(name="Arbaletă de Străjer", type=ItemType.weapon, value=15, quantity=1, description="Perception +1 | Archery +1"),
        InventoryItem(name="Săgeți", type=ItemType.consumable, value=1, quantity=10),
        # InventoryItem(name="5 galbeni", type=ItemType.currency, value=5, quantity=1), # Removed to use stats.gold only
    ]
    
    initial_suggs = CAMPAIGN_EPISODES.get(episode, {}).get("initial_suggestions", [])
    
    # Initial Story
    initial_story = [{
        "role": "ai",
        "text": "", # Content handled by 'content_data'
        "turn": 0,
        "image": None,
        "type": "episode_intro",
        "content_data": CAMPAIGN_EPISODES.get(episode, {}),
        "suggestions": initial_suggs
    }]

    initial_state = GameState(
        character=character,
        inventory=inventory,
        story=initial_story,
        turn=0,
        last_image_turn=-10
    )

    # Queue: (current_suggestions, game_state_snapshot, depth)
    queue = [(initial_suggs, initial_state, 0)]
    
    generated_cache = {}
    visited_prompts = set() # To avoid redundant processing if paths converge perfectly (rare due to history)
    
    processed_count = 0
    
    while queue and processed_count < MAX_STATES:
        current_suggestions, current_state, depth = queue.pop(0)
        
        if depth > MAX_DEPTH:
            continue
            
        # For each available suggestion at this point
        for sug in current_suggestions:
            try:
                # 1. Simulate User Action
                # Explicit deep copy of story to avoid reference issues (Pydantic v2 model_copy might not deep copy lists in all versions)
                new_story = copy.deepcopy(current_state.story)
                
                # Append User Message
                new_story.append({
                    "role": "user",
                    "text": sug,
                    "turn": current_state.turn,
                    "image": None
                })
                
                next_state = current_state.model_copy(deep=True)
                next_state.story = new_story
                
                # 2. Build Prompt & Hash
                prompt = Config.build_dnd_prompt(
                    story=next_state.story,
                    character=next_state.character.model_dump(mode='json'),
                    legend_scale=0, # Match UI default (Strict Historic)
                    game_mode=next_state.character.game_mode,
                    current_episode=next_state.character.current_episode
                )
                
                key_hash = CacheManager._get_hash(prompt)
                
                if "Mă apropii" in sug:
                    log(f"--- TARGET PROMPT DEBUG ({sug}) ---")
                    log(prompt)
                    log(f"HASH: {key_hash}")
                    log(f"--------------------------")

                if key_hash in visited_prompts:
                    # We already processed this exact state
                    continue
                visited_prompts.add(key_hash)
                
                # 3. Lookup Outcome in Source
                # Try exact match first
                resp_data = source_content.get(sug)
                
                # If not found, try partial match (fallback logic from before)
                if not resp_data:
                    for k in source_content:
                        if k in sug:
                            resp_data = source_content[k]
                            break
                
                # If still not found, we can't proceed on this branch (it's a dead end in source)
                if not resp_data:
                    # print(f"  [Dead End] No source for: {sug}")
                    continue
                    
                # 4. Store in Cache
                # Ensure response suggestions are valid
                next_suggs = resp_data.get("suggestions", [])
                if not next_suggs and not resp_data.get("win_condition") and not resp_data.get("game_over"):
                     # Fallback if source node has no suggestions but isn't end
                     next_suggs = ["Privește în jur."] 
                
                # Create Response Object
                resp_obj = NarrativeResponse(**resp_data)
                # Override suggestions if we fixed them
                if not resp_obj.suggestions:
                     resp_obj.suggestions = next_suggs

                generated_cache[key_hash] = resp_obj.model_dump(mode='json')
                
                # 5. Apply Outcome to State (for next iteration)
                # Apply changes
                c = next_state.character
                c.health = max(0, min(100, c.health + (resp_obj.health_change or 0)))
                c.reputation = max(0, min(100, c.reputation + (resp_obj.reputation_change or 0)))
                c.gold = max(0, c.gold + (resp_obj.gold_change or 0))
                
                if resp_obj.items_gained:
                    for item in resp_obj.items_gained:
                        next_state.inventory.append(item)
                
                if resp_obj.episode_progress is not None:
                    c.episode_progress = resp_obj.episode_progress
                
                # Append AI Message
                next_state.story.append({
                    "role": "ai",
                    "text": resp_obj.narrative,
                    "turn": next_state.turn,
                    "image": None,
                    "suggestions": next_suggs
                })
                
                next_state.turn += 1
                
                # 6. Add to Queue if not terminal
                if not resp_obj.win_condition and not resp_obj.game_over and next_suggs:
                    queue.append((next_suggs, next_state, depth + 1))
            except Exception as e:
                log(f"Error processing suggestion '{sug}': {e}")
                
        processed_count += 1
        if processed_count % 100 == 0:
            log(f"  Processed {processed_count} states...")

    log(f"Traversal Complete. Generated {len(generated_cache)} hashes.")
    
    # Save Compiled File
    bundle = {
        "character_class": char_class.value,
        "faction": faction.value,
        "episode": episode,
        "description": f"Exhaustive Compiled Pack Ep {episode}",
        "cache_data": generated_cache
    }
    
    ensure_dir(os.path.dirname(output_path))
    log(f"Saving to {output_path}...")
    try:
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
        log("Save successful.")
    except Exception as e:
        log(f"Save failed: {e}")

if __name__ == "__main__":
    # Run for Strajer Draculesti Ep 1
    compile_exhaustive(
        episode=1,
        char_class=CharacterClassType.STRAJER,
        faction=FactionType.DRACULESTI,
        source_path="story_packs/episode_1/strajer_source.json",
        output_path="story_packs/episode_1/strajer_draculesti.json"
    )
