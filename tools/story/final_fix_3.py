import json

source_path = "story_packs/episode_1/strajer_source.json"

new_nodes = {
    "Arată harta Căpitanului.": {
        "narrative": "Îi arăți harta găsită. \"Mănăstirea Dealu!\"",
        "suggestions": ["Pregătește-te de război (Sfârșit)."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Ascunde harta.": {
        "narrative": "Păstrezi harta pentru tine. Cunoașterea e putere.",
        "suggestions": ["Mergi singur în recunoaștere la Mănăstire."],
        "episode_progress": 0.5
    },
    "Intră furișat în criptă.": {
        "narrative": "Cobori în criptă. Vezi depozitul de arme.",
        "suggestions": ["Sabotează stocul de arme.", "Asasinează liderul (Foarte Riscant)."],
        "episode_progress": 0.7
    },
    "Intră cu sabia scoasă, strigând.": {
        "narrative": "Ataci frontal! Ești un tăvălug.",
        "suggestions": ["Luptă până la capăt (Moarte Glorioasă).", "Fugi și raportează totul."],
        "episode_progress": 0.7
    },
    "Pândește de afară.": {
        "narrative": "Stai în ploaie și numeri gărzile.",
        "suggestions": ["Elimină santinela izolată.", "Intră furișat în criptă."],
        "episode_progress": 0.55
    },
    "Atacă-i din umbră.": {
        "narrative": "Lovești din întuneric. Primul cade fără să știe ce l-a lovit.",
        "suggestions": ["Intră cu sabia scoasă, strigând.", "Retrage-te și trage cu arbaleta."],
        "episode_progress": 0.65
    },
    "Retrage-te și trage cu arbaleta.": {
        "narrative": "Te distanțezi și tragi. Îi elimini unul câte unul.",
        "suggestions": ["Du carul la cetate (Final Bun)."], # Assuming victory
        "episode_progress": 0.9
    },
    "Mulțumește.": {
        "narrative": "Mulțumești Căpitanului pentru încredere.",
        "suggestions": ["Mergi la mănăstirea părăsită."],
        "episode_progress": 0.5
    },
    "Cere și o sabie.": {
        "narrative": "Căpitanul îți dă și o sabie de oțel. \"Să o folosești bine.\"",
        "suggestions": ["Mergi la mănăstirea părăsită."],
        "items_gained": [{"name": "Sabie de Oțel", "type": "armă", "value": 15, "quantity": 1}],
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
        print("Successfully applied Final Fix 3.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    apply_fixes()
