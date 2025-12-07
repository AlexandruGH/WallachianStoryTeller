import json

source_path = "story_packs/episode_1/strajer_source.json"

updates = {
    "Fură pergamentul de la brâu.": {
        "narrative": "Ai mâini iuți. Iei pergamentul fără să simtă. Îl ai în mână, iar vizitiul continuă să privească în cealaltă parte, nebănuind nimic.",
        "suggestions": [
            "Retrage-te și examinează-l.",
            "Imobilizează vizitiul acum (Surpriză).",
            "Du-te direct la Căpitan cu dovada."
        ],
        "items_gained": [{"name": "Pergament Codificat", "type": "obiect_important", "value": 0, "quantity": 1}],
        "episode_progress": 0.2
    },
    
    "Retrage-te și examinează-l.": {
        "narrative": "Te retragi într-o alee lăturalnică și rupi sigiliul. E scris într-un cifru ciudat: '...la ceasul bufniței...'. Ai nevoie de ajutor.",
        "suggestions": [
            "Mergi la Grămăticul Curții (Erudit).",
            "Caută informatori în Taverna 'La Lupul Șchiop'.",
            "Du-te direct la Căpitan."
        ],
        "episode_progress": 0.25
    },

    "Imobilizează vizitiul acum (Surpriză).": {
        "narrative": "Profitând că e distras, îi aplici o cheie de braț și îl pui la pământ înainte să poată scoate cuțitul. \"M-ai prins, câine!\" scuipă el.",
        "suggestions": [
            "Leagă-l și percheziționează carul.",
            "Interoghează-l dur despre pergament."
        ],
        "reputation_change": 2,
        "episode_progress": 0.3
    },

    "Leagă-l și percheziționează carul.": {
        "narrative": "Îl legi de roata carului. În car găsești arme ascunse. Ai și spionul, și armele, și mesajul.",
        "suggestions": [
            "Du totul la Căpitan (Succes Total)."
        ],
        "episode_progress": 0.9
    },

    "Interoghează-l dur despre pergament.": {
        "narrative": "Îi arăți pergamentul. \"Ce scrie aici?!\" După câteva lovituri, cedează. \"Mănăstirea Dealu! Atac la miezul nopții!\"",
        "suggestions": [
            "Fugi la Căpitan cu informația.",
            "Lasa-l legat si mergi la Mănăstire."
        ],
        "episode_progress": 0.4
    },
    
    "Du totul la Căpitan (Succes Total).": {
        "narrative": "Intri în curtea cazărmii cu prizonierul și dovezile. Căpitanul e impresionat. \"O muncă de străjer adevărat!\"",
        "suggestions": ["Pregătește-te de război (Sfârșit)."],
        "win_condition": True,
        "gold_change": 30,
        "reputation_change": 10,
        "episode_progress": 1.0
    },

    "Lasa-l legat si mergi la Mănăstire.": {
        "narrative": "Îl lași pachet pentru patrulă și pleci în recunoaștere.",
        "suggestions": ["Mergi singur în recunoaștere la Mănăstire."],
        "episode_progress": 0.5
    },
    
    # Update link
    "Du-te direct la Căpitan cu dovada.": {
        "narrative": "Vezi 'Du-te direct la Căpitan cu documentul'.",
        "suggestions": ["Du-te direct la Căpitan cu documentul."]
    }
}

def apply_fixes():
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, content in updates.items():
            data[key] = content
            print(f"Updated: {key}")
            
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully patched Stealth Branch.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    apply_fixes()
