import json

source_path = "story_packs/episode_1/strajer_source.json"

# Define missing nodes or aliases
new_nodes = {
    # Mappings
    "Du-te direct la Căpitan.": { # Alias
        "narrative": "Vezi 'Du-te direct la Căpitan cu documentul'.",
        "suggestions": ["Du-te direct la Căpitan cu documentul."]
    },
    "Fugi la Căpitan cu informația.": { # Alias
        "narrative": "Fugi la Căpitan să raportezi totul.",
        "suggestions": ["Fugi la Căpitan (Sigur)."]
    },

    # Re-definitions (Just in case they were lost or encoding mismatch)
    "Pregătește-te de război (Sfârșit).": { 
        "narrative": "Sfârșit Episod 1.", "suggestions": [], "win_condition": True 
    },
    "Raportează eșecul.": { 
        "narrative": "Raportezi eșecul. Căpitanul e dezamăgit.", "suggestions": ["Rejoacă."], "win_condition": True 
    },
    "Fugi înapoi la cetate (Eșec parțial).": {
        "narrative": "Te retragi rănit. Măcar ai supraviețuit.", "suggestions": ["Raportează eșecul."], "episode_progress": 1.0
    },
    "Raportează Căpitanului incidentul.": {
        "narrative": "Raportezi incidentul. \"Bine că ești viu.\"", "suggestions": ["Mergi la infirmerie (Sfârșit)."], "episode_progress": 1.0
    },
    "Atacă-i pe amândoi acum.": {
        "narrative": "Te lupți cu ei. E greu.", "suggestions": ["Luptă pentru scăpare."], "health_change": -10, "episode_progress": 0.5
    },
    "Du carul la cetate (Final Bun).": {
        "narrative": "Aduci carul în cetate. Victorie!", "suggestions": ["Pregătește-te de război (Sfârșit)."], "win_condition": True, "episode_progress": 1.0
    },
    "Cheamă gărzile de la poartă.": {
        "narrative": "Gărzile vin în ajutor.", "suggestions": ["Arestați vizitiul."], "episode_progress": 0.4
    },
    "Dezarmează-l și arestează-l.": {
        "narrative": "Îl dezarmezi și îl legi.", "suggestions": ["Du-l la Căpitan (Final Bun)."], "episode_progress": 0.8
    },
    "Fugi la Căpitan (Sigur).": {
        "narrative": "Ajungi la Căpitan în siguranță.", "suggestions": ["Săbătorește victoria (Sfârșit)."], "win_condition": True, "episode_progress": 1.0
    },
    
    # Missing Endings
    "Mergi la infirmerie (Sfârșit).": { "narrative": "Sfârșit Episod 1.", "suggestions": [], "win_condition": True },
    "Săbătorește victoria (Sfârșit).": { "narrative": "Sfârșit Episod 1.", "suggestions": [], "win_condition": True },
    
    # Missing Actions
    "Arestați vizitiul.": {
        "narrative": "Gărzile îl înconjoară. E prins.",
        "suggestions": ["Du-l la interogatoriu.", "Verifică carul."],
        "episode_progress": 0.4
    },
    "Du-l la Căpitan (Final Bun).": {
        "narrative": "Căpitanul te laudă. Ai făcut o treabă excelentă.",
        "suggestions": ["Pregătește-te de război (Sfârșit)."],
        "win_condition": True,
        "episode_progress": 1.0
    }
}

def apply_fixes():
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, content in new_nodes.items():
            # Always overwrite/add to ensure it exists
            data[key] = content
            print(f"Patched: {key}")
            
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully applied Final Stealth Fixes.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    apply_fixes()
