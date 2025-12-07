import json
import sys
import os

# Add root directory to path to allow importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from campaign import CAMPAIGN_EPISODES

def check():
    # Path relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.join(script_dir, "../../story_packs/episode_1/strajer_source.json")
    
    with open(source_path, 'r', encoding='utf-8') as f:
        source_data = json.load(f)
    
    source_keys = list(source_data.keys())
    
    campaign_suggs = CAMPAIGN_EPISODES[1]["initial_suggestions"]
    
    print("Checking keys...")
    for sug in campaign_suggs:
        if sug in source_keys:
            print(f"✅ '{sug}' found in source.")
        else:
            print(f"❌ '{sug}' NOT found in source.")
            # Print similar keys
            for k in source_keys:
                if "apropii" in k:
                    print(f"   Did you mean: '{k}'?")
                    print(f"   Camp hex: {sug.encode('utf-8').hex()}")
                    print(f"   File hex: {k.encode('utf-8').hex()}")

if __name__ == "__main__":
    check()
