import json
import os
import sys
import time
import requests

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
from config import Config

def generate_summary(action, narrative):
    token = os.getenv("GROQ_API_KEY")
    if not token:
        print("No API Key")
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = f"""
    Rezumat scurt (1 frază) pentru acest eveniment din joc:
    Acțiune: {action}
    Rezultat: {narrative}
    
    Răspunde doar cu rezumatul, la persoana a 3-a (ex: "Străjerul a atacat banditul...").
    """
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 100
    }
    
    try:
        res = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'].strip()
        else:
            print(f"Error: {res.text}")
    except Exception as e:
        print(f"Ex: {e}")
    return None

def process_file(filepath):
    print(f"Processing {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated = False
    count = 0
    total = len(data)
    
    for key, value in data.items():
        count += 1
        if "event_summary" not in value:
            print(f"[{count}/{total}] Generating summary for: {key[:30]}...")
            summary = generate_summary(key, value['narrative'])
            if summary:
                value['event_summary'] = summary
                updated = True
                time.sleep(0.5) # Rate limit
            else:
                print("Failed to generate summary")
        
    if updated:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Saved updates.")
    else:
        print("No updates needed.")

if __name__ == "__main__":
    # List of files to process
    files = [
        "story_packs/episode_1/strajer_source.json",
        # Add others if needed
    ]
    
    for f in files:
        if os.path.exists(f):
            process_file(f)
        else:
            print(f"File not found: {f}")
