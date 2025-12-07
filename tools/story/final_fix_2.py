import json

source_path = "story_packs/episode_1/strajer_source.json"

new_nodes = {
    "Du-l la interogatoriu.": {
        "narrative": "În beciurile cetății, limba vizitiului se dezleagă. \"Mănăstirea Dealu... acolo e baza.\"",
        "suggestions": ["Mergi la mănăstirea părăsită.", "Raportează locația Căpitanului."],
        "episode_progress": 0.4
    },
    "Verifică carul.": {
        "narrative": "Găsești un fund dublu. Înăuntru e un tub cu o hartă.",
        "suggestions": ["Deschide tubul pe loc.", "Predă tubul Căpitanului."],
        "items_gained": [{"name": "Tub Sigilat", "type": "obiect_important", "value": 0, "quantity": 1}],
        "episode_progress": 0.35
    },
    "Deschide tubul pe loc.": {
        "narrative": "Rupi sigiliul. Înăuntru e harta tunelurilor secrete de sub palat. Semnată de un trădător din gardă.",
        "suggestions": ["Arată harta Căpitanului.", "Ascunde harta."],
        "episode_progress": 0.4
    },
    "Predă tubul Căpitanului.": {
        "narrative": "Îi dai tubul. El îl deschide. 'O hartă... Mănăstirea Dealu. Deci acolo se ascund!'",
        "suggestions": ["Mergi la mănăstirea părăsită.", "Cere echipament mai bun."],
        "episode_progress": 0.45
    },
    "Mergi la mănăstirea părăsită.": { # Ensure it exists if referenced
         "narrative": "Mănăstirea e o ruină. Ziduri surpate, liniște mormântală. Dar ușa grea de stejar de la intrarea în criptă e întredeschisă.",
         "suggestions": ["Intră furișat în criptă.", "Intră cu sabia scoasă, strigând.", "Pândește de afară."],
         "location_change": "Mănăstirea Părăsită",
         "episode_progress": 0.5
    }
}

def apply_fixes():
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, content in new_nodes.items():
            data[key] = content
            print(f"Patched: {key}")
            
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully applied Final Fix 2.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    apply_fixes()
