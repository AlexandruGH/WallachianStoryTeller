import json

source_path = "story_packs/episode_1/strajer_source.json"

updates = {
    # 1. Fix Inventory
    "Cere echipament mai bun.": {
        "narrative": "Căpitanul îți dă o platoșă nouă din armurărie. \"Să nu o strici.\"",
        "suggestions": ["Mergi la mănăstirea părăsită.", "Mulțumește.", "Cere și o sabie."],
        "items_gained": [{"name": "Platoșă de străjer", "type": "diverse", "value": 15, "quantity": 1}],
        "episode_progress": 0.45
    },

    # 2. Fix Loop (Monastery -> Market)
    "Fură un cal și anunță garda.": {
        "narrative": "Iei un cal legat la poartă și galopezi spre cazarmă să aduci întăriri.",
        "suggestions": ["Dă alarma la cazarmă."], # Changed from "Strigă alarma" to avoid loop
        "episode_progress": 0.5
    },
    
    # 3. New Node for Monastery Alarm
    "Dă alarma la cazarmă.": {
        "narrative": "Intri în curtea cazărmii strigând. Căpitanul ascultă raportul scurt. \"La cai! Mergem peste ei!\"",
        "suggestions": ["Condu asaltul spre mănăstire."],
        "reputation_change": 2,
        "episode_progress": 0.55
    },
    "Condu asaltul spre mănăstire.": {
        "narrative": "Te întorci la mănăstire în fruntea unui detașament. Mercenarii sunt surprinși.",
        "suggestions": ["Atacă-i din umbră.", "Intră cu sabia scoasă, strigând."], # Reuse combat nodes
        "episode_progress": 0.6
    },

    # 4. Clarify "Spune-i Căpitanului"
    "Du-l la interogatoriu.": {
        "narrative": "În beciurile cetății, limba vizitiului se dezleagă. \"Mănăstirea Dealu... acolo e baza.\"",
        "suggestions": ["Mergi la mănăstirea părăsită.", "Raportează locația Căpitanului.", "Cere o trupă de asalt."],
        "episode_progress": 0.4
    },
    "Raportează locația Căpitanului.": { # Renamed from "Spune-i Căpitanului"
        "narrative": "Te duci la Căpitan cu noile informații. \"Deci Mănăstirea Dealu... Pregătește-te de drum.\"",
        "suggestions": ["Mergi la mănăstirea părăsită.", "Cere echipament mai bun."],
        "episode_progress": 0.45
    }
}

# Helper to remove old keys if needed? 
# "Spune-i Căpitanului" will become orphan, but that's fine.

def apply_fixes():
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Apply updates
        for key, content in updates.items():
            data[key] = content
            print(f"Updated/Added: {key}")
            
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully patched logic loops and inventory.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    apply_fixes()
