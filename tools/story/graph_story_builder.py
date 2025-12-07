import json
import networkx as nx
import os
from models import CharacterClassType, FactionType, NarrativeResponse, CharacterStats, GameState, InventoryItem, ItemType, GameMode
from campaign import CAMPAIGN_EPISODES
from config import Config
from caching import CacheManager

class StoryNode:
    def __init__(self, id, narrative, **kwargs):
        self.id = id
        self.narrative = narrative
        self.kwargs = kwargs # items_gained, health_change, etc.
        self.options = [] # List of tuples (text, target_node_id)

    def add_option(self, text, target_id):
        self.options.append((text, target_id))

class StoryGraph:
    def __init__(self):
        self.nodes = {}
        self.root_id = None

    def add_node(self, id, narrative, **kwargs):
        node = StoryNode(id, narrative, **kwargs)
        self.nodes[id] = node
        if not self.root_id:
            self.root_id = id
        return node

    def add_edge(self, from_id, to_id, text):
        if from_id in self.nodes:
            self.nodes[from_id].add_option(text, to_id)
        else:
            print(f"Error: Source node {from_id} does not exist.")

    def export_to_source_json(self, filepath):
        """
        Converts the Graph into the flat Dictionary format used by the game engine.
        Key = User Action (Edge Text)
        Value = Target Node Data (Narrative + Next Suggestions)
        """
        flat_data = {}
        
        for node_id, node in self.nodes.items():
            # For the game engine, the "Key" is the action that led TO this node.
            # But the Source format actually keys by "Action Text" -> "Result Narrative".
            # So we need to find all edges pointing TO this node?
            # No, the Source format is:
            # "User Action String": { "narrative": "Response", "suggestions": ["Next A", "Next B"] }
            
            # So for every edge (u -> v) with label L:
            # flat_data[L] = v.data (narrative) + v.suggestions (edges out of v)
            
            # Wait, what about the Root? The Root narrative comes from previous context (Campaign Intro).
            # The Source File contains keys for the *suggestions offered by the Root*.
            # e.g. Root offers ["A", "B"]. Source file has keys "A" and "B".
            
            # We iterate over all nodes. For each node 'u', we look at its outgoing edges.
            # For edge (u -> v) with text T:
            # flat_data[T] = v.narrative + [edge.text for edge in v.options]
            
            for text, target_id in node.options:
                target_node = self.nodes.get(target_id)
                if target_node:
                    # Construct the value object
                    next_suggestions = [opt[0] for opt in target_node.options]
                    
                    entry = {
                        "narrative": target_node.narrative,
                        "suggestions": next_suggestions
                    }
                    # Add optional fields
                    entry.update(target_node.kwargs)
                    
                    # Handle duplicate keys? 
                    # If two nodes have the same option text leading to different outcomes, that's a conflict in the flat model.
                    # The Graph model supports it (context dependent), but the Flat Source model relies on unique keys (mostly).
                    # We warn or append context if needed, but for now assume unique texts.
                    if text in flat_data:
                        print(f"WARNING: Duplicate key '{text}' detected. Overwriting.")
                    
                    flat_data[text] = entry
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(flat_data, f, ensure_ascii=False, indent=2)
        print(f"Exported Source JSON to {filepath}")

    def export_to_mermaid(self, filepath):
        """Generates a Mermaid flowchart."""
        lines = ["graph TD"]
        
        # Style definitions
        lines.append("classDef default fill:#1a0f0b,stroke:#d4af37,color:#e8d8c3;")
        lines.append("classDef win fill:#2d3a1e,stroke:#4caf50;")
        lines.append("classDef dead fill:#3a1e1e,stroke:#f44336;")
        
        for node_id, node in self.nodes.items():
            # Shorten narrative for display
            short_desc = (node.narrative[:40] + "...") if len(node.narrative) > 40 else node.narrative
            short_desc = short_desc.replace('"', "'")
            
            # Class styling
            css_class = ""
            if node.kwargs.get("win_condition"): css_class = ":::win"
            elif node.kwargs.get("health_change", 0) < -10: css_class = ":::dead"
            
            lines.append(f'    {node_id}["{node_id}<br/>{short_desc}"]{css_class}')
            
            for text, target_id in node.options:
                lines.append(f'    {node_id} -->|"{text}"| {target_id}')
                
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        print(f"Exported Mermaid Graph to {filepath}")

    def compile_to_hash_cache(self, output_path, episode, char_class, faction):
        """
        Simulates the game using the Graph as the source of truth and generates
        the hashed cache file.
        """
        print(f"Compiling Graph to Hash Cache: {output_path}")
        
        # Initialize Mock Game State
        character = CharacterStats()
        character.game_mode = GameMode.CAMPAIGN
        character.current_episode = episode
        character.location = CAMPAIGN_EPISODES.get(episode, {}).get("location", "Târgoviște")
        
        # Minimal stats/inventory
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
        
        # BFS Traversal to cover all reachable nodes from Root
        # Queue stores: (node_id, accumulated_story_list)
        # This is expensive if history grows indefinitely.
        # Optimization: Just use the "Standard" history + current step?
        # Or limit depth.
        
        # Let's assume a simplified simulation where we just traverse the graph
        # and construct prompts as if it was the "next step".
        # Note: This won't perfectly match "deep" histories if the user took a winding path,
        # but it covers the direct path.
        
        # Map Node ID -> Story Node
        # We need to map "Suggestion Text" -> Target Node
        
        queue = [(self.root_id, game_state.story)] # Start at root
        visited_states = set() # text_hash of last message
        
        # Limit iterations to avoid infinite loops
        max_nodes = 100
        count = 0
        
        while queue and count < max_nodes:
            current_node_id, current_story = queue.pop(0)
            current_node = self.nodes[current_node_id]
            
            # Process all outgoing options
            for text, target_id in current_node.options:
                target_node = self.nodes.get(target_id)
                if not target_node: continue
                
                # Simulate user selecting this option
                temp_story = current_story + [{
                    "role": "user",
                    "text": text,
                    "turn": 0, # Turn number doesn't affect hash usually? Config.build_dnd_prompt uses history.
                    "image": None
                }]
                
                # Build Prompt
                prompt = Config.build_dnd_prompt(
                    story=temp_story,
                    character=character.model_dump(mode='json'), # Use base character
                    legend_scale=5,
                    game_mode=GameMode.CAMPAIGN,
                    current_episode=episode
                )
                
                # Hash & Store
                key_hash = CacheManager._get_hash(prompt)
                
                # Construct Response Object
                next_suggs = [opt[0] for opt in target_node.options]
                
                resp_data = {
                    "narrative": target_node.narrative,
                    "suggestions": next_suggs
                }
                resp_data.update(target_node.kwargs)
                
                generated_cache[key_hash] = resp_data
                
                # Add next state to queue
                # Construct new AI message
                new_ai_msg = {
                    "role": "ai",
                    "text": target_node.narrative,
                    "suggestions": next_suggs
                }
                new_story = temp_story + [new_ai_msg]
                
                # Avoid cycles/redundancy
                state_sig = f"{target_id}_{len(new_story)}"
                if state_sig not in visited_states:
                    visited_states.add(state_sig)
                    queue.append((target_id, new_story))
            
            count += 1
            
        # Save Bundle
        bundle = {
            "character_class": char_class.value,
            "faction": faction.value,
            "episode": episode,
            "description": f"Graph Compiled Pack Ep {episode}",
            "cache_data": generated_cache
        }
        
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(generated_cache)} graph hashes to {output_path}")

# ==========================================
# DEFINING THE STRĂJER DRĂCULEȘTI FLOW
# ==========================================
def build_strajer_graph():
    g = StoryGraph()
    
    # 1. ROOT (Start of Episode)
    # This node represents the state *before* the user clicks anything.
    # The suggestions here match the campaign intro suggestions.
    g.add_node("root", "Intro - Carul Negru ajunge în piață.")
    
    # 2. LEVEL 1 NODES (Outcomes of Initial Choices)
    g.add_node("wagon_approach", 
               "Te apropii precaut. Vizitiul ascunde ceva. Semnul Dăneștilor e pe osie.",
               reputation_change=0)
    
    g.add_node("market_rumors", 
               "Zvonurile spun că Dăneștii vor să ardă orașul.",
               reputation_change=1)
               
    g.add_node("high_ground", 
               "Vezi un schimb de pachete între vizitiu și un boier.",
               reputation_change=1)
    
    # Edges from Root
    g.add_edge("root", "wagon_approach", "Mă apropii discret de carul negru.")
    g.add_edge("root", "market_rumors", "Merg în piață să ascult zvonurile.")
    g.add_edge("root", "high_ground", "Caut un loc înalt pentru a observa.")
    
    # 3. LEVEL 2 - Wagon Branch
    g.add_node("inspect_tarp", 
               "Sub prelată e praf de pușcă! E o capcană.",
               episode_progress=0.1)
    
    g.add_node("provoke_driver", 
               "Omul scoate un cuțit. Atacă!",
               episode_progress=0.1, health_change=-2)
               
    g.add_node("stab_sack", 
               "Curge praf negru. Vizitiul fuge cu carul.",
               episode_progress=0.2, health_change=-5)

    g.add_edge("wagon_approach", "inspect_tarp", "Cere-i să ridice prelata.")
    g.add_edge("wagon_approach", "provoke_driver", "Provoacă-l să coboare.")
    g.add_edge("wagon_approach", "stab_sack", "Înțeapă un sac cu pumnalul.")
    
    # 4. LEVEL 3 - Alarm Branch (The fix)
    g.add_node("alarm_raised", 
               "ALARMĂ! TRĂDARE! Gărzile blochează ieșirea. Carul e prins.",
               episode_progress=0.25)
               
    g.add_node("chase_scene",
               "Alergi după car prin mahalale.",
               episode_progress=0.25)
               
    g.add_node("horse_chase",
               "Iei un cal și galopezi după el.",
               episode_progress=0.25)
               
    g.add_edge("stab_sack", "alarm_raised", "Strigă alarma.")
    g.add_edge("stab_sack", "chase_scene", "Urmărește carul în fugă.")
    g.add_edge("stab_sack", "horse_chase", "Notează direcția și cere un cal.")

    # 5. LEVEL 4 - Resolution of Alarm
    g.add_node("arrest_success", 
               "Vizitiul e arestat. Mărturisește tot.",
               episode_progress=0.3)
    
    g.add_node("cargo_seized", 
               "Praf de pușcă confiscat. Orașul e salvat.",
               episode_progress=0.3)
               
    g.add_node("captain_report", 
               "Căpitanul te laudă și îți dă o pungă de bani.",
               gold_change=5, episode_progress=0.3)

    g.add_edge("alarm_raised", "arrest_success", "Arestați vizitiul.")
    g.add_edge("alarm_raised", "cargo_seized", "Confiscați marfa.")
    g.add_edge("alarm_raised", "captain_report", "Raportează Căpitanului.")
    
    # 6. Convergence to Monastery
    g.add_node("monastery_travel", 
               "Toate indiciile duc la Mănăstirea Dealu. Pleci într-acolo.",
               location_change="Mănăstirea Dealu", episode_progress=0.4)
               
    g.add_edge("arrest_success", "monastery_travel", "Du-l la interogatoriu.")
    g.add_edge("captain_report", "monastery_travel", "Mergi la mănăstirea părăsită.")
    # Link back other branches (simplified for example)
    g.add_edge("market_rumors", "monastery_travel", "Mergi la mănăstirea părăsită.")
    
    return g

if __name__ == "__main__":
    graph = build_strajer_graph()
    
    # Export to JSON (Playable)
    graph.export_to_source_json("story_packs/episode_1/strajer_graph_source.json")
    
    # Export to Mermaid (Visual)
    graph.export_to_mermaid("docs/strajer_flow_diagram.mermaid")
    
    # Compile to Hash Cache
    from models import CharacterClassType, FactionType
    graph.compile_to_hash_cache(
        "story_packs/episode_1/strajer_draculesti.json",
        episode=1,
        char_class=CharacterClassType.STRAJER,
        faction=FactionType.DRACULESTI
    )
