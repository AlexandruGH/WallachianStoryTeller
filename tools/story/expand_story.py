import json
import os
import sys
import time
import requests
import random
from collections import deque

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
import codecs

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

load_dotenv()

TARGET_DEPTH = 10
JSON_PATH = "story_packs/episode_1/strajer_source.json"

def get_all_groq_tokens():
    tokens = []
    token = os.getenv("GROQ_API_KEY")
    if token and token.strip(): tokens.append(token.strip())
    i = 1
    while True:
        token = os.getenv(f"GROQ_API_KEY{i}")
        if token and token.strip():
            tokens.append(token.strip())
            i += 1
        else:
            break
    return list(set(tokens))

def get_llm_response(messages, model="llama-3.3-70b-versatile"):
    tokens = get_all_groq_tokens()
    if not tokens:
        print("No API Key")
        return None

    # Simple rotation or retry
    for token in tokens:
        url = "https://api.groq.com/openai/v1/chat/completions"
        if token.startswith("sk-or-v1"):
             url = "https://openrouter.ai/api/v1/chat/completions"
             model = "meta-llama/llama-3.3-70b-instruct:free"
        
        payload = {
            "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
        "response_format": {"type": "json_object"}
    }
    
        try:
            res = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content']
            elif res.status_code == 401:
                print(f"Invalid key: {token[:5]}...")
                continue # Try next
            else:
                print(f"Error: {res.text}")
        except Exception as e:
            print(f"Ex: {e}")
            
    return None

def load_data():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def build_graph(data):
    graph = {}
    roots = [
        "Mă apropii discret de carul negru.",
        "Merg în piață să ascult zvonurile.",
        "Caut un loc înalt pentru a observa."
    ]
    
    for key, value in data.items():
        children = []
        for sug in value.get("suggestions", []):
            if sug in data:
                children.append(sug)
        graph[key] = children
        
    return graph, roots

def get_node_depths(graph, roots):
    depths = {}
    queue = deque([(root, 1) for root in roots])
    
    while queue:
        node, d = queue.popleft()
        if node not in depths or d > depths[node]:
            depths[node] = d # Keep max depth
        
        if node in graph:
            for child in graph[node]:
                queue.append((child, d + 1))
    return depths

def extend_node(node_key, current_depth, data):
    print(f"Extending node: {node_key} (Depth {current_depth})")
    
    node_data = data[node_key]
    
    # Check if eligible for extension
    if not node_data.get("win_condition"):
        print("Skipping - Not a win condition")
        return False
        
    if current_depth >= TARGET_DEPTH:
        print("Skipping - Target depth reached")
        return False

    # Remove win condition to continue story
    del node_data["win_condition"]
    
    # Generate continuation
    prompt = f"""
    You are expanding a D&D story for a 'Strajer' (Guard) in medieval Wallachia (Vlad Tepes era).
    Current Situation:
    Action: {node_key}
    Result: {node_data['narrative']}
    
    The story ended too soon (Win Condition). We need to extend it by adding a complication or a new step in the investigation before the final success.
    
    Generate 2 NEW distinct options (suggestions) for the player to continue from here.
    For each option, generate the resulting narrative (2-3 sentences, detailed, atmospheric).
    
    One option should lead to further investigation/combat.
    The other should be a risky/different approach.
    
    Format JSON:
    {{
        "option_1": "text of option 1",
        "narrative_1": "narrative result of option 1",
        "option_2": "text of option 2",
        "narrative_2": "narrative result of option 2"
    }}
    
    Language: Romanian.
    """
    
    response = get_llm_response([{"role": "user", "content": prompt}])
    if not response:
        return False
        
    try:
        gen_data = json.loads(response)
        
        opt1 = gen_data["option_1"]
        nar1 = gen_data["narrative_1"]
        opt2 = gen_data["option_2"]
        nar2 = gen_data["narrative_2"]
        
        # Update current node suggestions
        node_data["suggestions"] = [opt1, opt2]
        
        # Add new nodes to data
        # Propagate summary/stats if needed (simplified)
        
        data[opt1] = {
            "narrative": nar1,
            "suggestions": [],
            "episode_progress": min(0.9, node_data.get("episode_progress", 0.5) + 0.1),
            # Mark as win condition temporarily so recursive loop picks it up next time?
            # Or just leave it open. The loop will see it has no children.
            "win_condition": True 
        }
        
        data[opt2] = {
            "narrative": nar2,
            "suggestions": [],
            "episode_progress": min(0.9, node_data.get("episode_progress", 0.5) + 0.1),
            "win_condition": True
        }
        
        # Generate summaries for new nodes immediately
        from tools.story.inject_summaries import generate_summary
        
        sum1 = generate_summary(opt1, nar1)
        if sum1: data[opt1]["event_summary"] = sum1
        
        sum2 = generate_summary(opt2, nar2)
        if sum2: data[opt2]["event_summary"] = sum2
        
        print(f"Extended with: {opt1}, {opt2}")
        return True
        
    except Exception as e:
        print(f"Error parsing gen response: {e}")
        return False

def main():
    data = load_data()
    
    # Iterative expansion until all Win leaves are >= TARGET_DEPTH
    # Limit iterations to avoid infinite loops
    for i in range(5): # Max 5 passes
        print(f"--- PASS {i+1} ---")
        graph, roots = build_graph(data)
        depths = get_node_depths(graph, roots)
        
        extended_any = False
        
        # Find leaves that are Wins and too shallow
        # We iterate a snapshot of keys because we modify data
        keys = list(data.keys())
        for key in keys:
            if key not in depths: continue # Unreachable?
            
            d = depths[key]
            node = data[key]
            
            # Check if leaf (no suggestions or win)
            # Actually, we extend "Win" nodes.
            if node.get("win_condition") and d < TARGET_DEPTH:
                if extend_node(key, d, data):
                    extended_any = True
                    save_data(data) # Save incrementally
                    time.sleep(1) # Rate limit
        
        if not extended_any:
            print("No more nodes to extend.")
            break

if __name__ == "__main__":
    main()
