import json

source_path = "story_packs/episode_1/strajer_source.json"

new_nodes = {
    # --- Meta ---
    "Rejoacă.": {
        "narrative": "Felicitări pentru parcurgerea acestui fir narativ! Poți încerca alte alegeri pentru a descoperi toate secretele.",
        "suggestions": [],
        "game_over": True
    },

    # --- Variations / Typos ---
    "Taie-i calea.": { # Redirect to existing logic
        "narrative": "Faci o manevră bruscă.",
        "suggestions": ["Sari pe capră.", "Oprește caii."],
        "episode_progress": 0.28
    },
    "Urmărește-l de la distanță.": {
        "narrative": "Îl lași să creadă că a scăpat. Te duce direct la ascunzătoare.",
        "suggestions": ["Pândește de afară."], # Link to Monastery stakeout
        "episode_progress": 0.4
    },

    # --- Combat / Chase Actions ---
    "Lovește caii.": {
        "narrative": "Caii se sperie și carul se răstoarnă într-un nor de praf!",
        "suggestions": ["Verifică carul.", "Caută supraviețuitori."],
        "episode_progress": 0.35
    },
    "Caută supraviețuitori.": {
        "narrative": "Vizitiul e prins sub roată, gemând.",
        "suggestions": ["Arestați vizitiul.", "Cere numele celui care l-a plătit."],
        "episode_progress": 0.35
    },
    "Blochează drumul cu calul.": {
        "narrative": "Te pui de-a curmezișul străzii. Vizitiul trage disperat de frâie să nu te lovească.",
        "suggestions": ["Sari pe capră.", "Strigă să se predea."],
        "episode_progress": 0.3
    },
    "Îmbrâncește-l.": {
        "narrative": "Îl împingi cu umărul. Se dezechilibrează.",
        "suggestions": ["Aruncă-l din car."],
        "episode_progress": 0.32
    },
    "Dezarmează-l.": {
        "narrative": "Îi sucești încheietura până scapă cuțitul.",
        "suggestions": ["Aruncă-l din car.", "Arestați vizitiul."],
        "episode_progress": 0.33
    },
    "Lasă-l și verifică carul.": {
        "narrative": "Importantă e încărcătura, nu vizitiul.",
        "suggestions": ["Verifică carul."],
        "episode_progress": 0.35
    },

    # --- Investigation fillers ---
    "Notează descrierea.": {
        "narrative": "Scrii în minte fiecare detaliu. Boierul trădător nu va scăpa.",
        "suggestions": ["Raportează la căpitan."],
        "episode_progress": 0.4
    },
    "Caută indicii în cameră.": {
        "narrative": "Găsești o scrisoare arsă pe jumătate în șemineu. Se distinge sigiliul Dăneștilor.",
        "suggestions": ["Raportează la căpitan."],
        "items_gained": [{"name": "Scrisoare arsă", "type": "obiect_important", "value": 0, "quantity": 1}],
        "episode_progress": 0.4
    },
    "Dă foc casei (Radical).": {
        "narrative": "Arunci torța. Lemnul vechi se aprinde instantaneu. Cuibul de șobolani arde. (Reputație scăzută, dar eficient).",
        "suggestions": ["Raportează la căpitan."],
        "reputation_change": -2,
        "episode_progress": 0.4
    },

    # --- Tunnel / Puzzle fillers ---
    "Lasă-te să cazi.": {
        "narrative": "Cazi în gol... și lovești apa rece a unui râu subteran. Curentul te duce departe.",
        "suggestions": ["Caută altă ieșire."],
        "episode_progress": 0.9
    },
    "Blochează ușa.": {
        "narrative": "Tragi zăvorul greu de fier. Acum ești blocat cu ei, dar ei nu pot primi întăriri.",
        "suggestions": ["Atacă cât sunt orbiți.", "Ascunde-te."],
        "episode_progress": 0.7
    },
    "Atacă-i din spate.": {
        "narrative": "Îi surprinzi total!",
        "suggestions": ["Termină lupta rapid (riscant)."],
        "episode_progress": 0.72
    },
    "Fugi după lider.": {
        "narrative": "Îi lași pe soldați să se ocupe de restul și urmărești ținta.",
        "suggestions": ["Fugi după cel cu fragmentul."],
        "episode_progress": 0.72
    },
    
    # --- Capture / Finish ---
    "Sari pe el.": {
        "narrative": "Îl pui la pământ sub greutatea ta.",
        "suggestions": ["Ia fragmentul și leagă-l."],
        "episode_progress": 0.9
    },
    "Luptă cu el.": {
        "narrative": "E un spadasin bun, dar obosit.",
        "suggestions": ["Termină-l.", "Dezarmează-l."], # Dezarmează-l links to existing above? Careful with context. Narrative above implies car.
                                                # Need specific node or unique name.
                                                # Let's map to unique name.
    },
    "Termină-l.": { # Unique
        "narrative": "O lovitură precisă în inimă. S-a terminat.",
        "suggestions": ["Ia fragmentul și calul."],
        "episode_progress": 1.0
    },
    "Ia fragmentul și leagă-l.": {
        "narrative": "Îl legi fedeleș. Ai prins spionul ȘI ai recuperat Pecetea! O victorie totală.",
        "suggestions": ["Pleacă spre curte."],
        "items_gained": [{"name": "Fragment Pecete", "type": "obiect_important", "value": 0, "quantity": 1}],
        "reputation_change": 5,
        "episode_progress": 1.0
    },
    "Fugi după el.": { # Redirect loop break
        "narrative": "Nu-l lași să scape!",
        "suggestions": ["Prinde-l din urmă."],
        "episode_progress": 0.76
    },
    
    # --- Tunnel Exploration ---
    "Aprinde o torță.": {
        "narrative": "Lumina flăcării dansează pe pereții umezi.",
        "suggestions": ["Mergi tiptil."],
        "episode_progress": 0.5
    },
    "Mergi tiptil.": {
        "narrative": "Auzi voci în față. Se apropie.",
        "suggestions": ["Ascultă planul lor.", "Atacă-i din umbră."],
        "episode_progress": 0.55
    }
}

def update_source():
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Add new nodes if they don't exist
        for key, content in new_nodes.items():
            if key not in data:
                data[key] = content
                print(f"Added node: {key}")
            else:
                pass
        
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully updated source file (Round 2).")
        
    except Exception as e:
        print(f"Error updating source: {e}")

if __name__ == "__main__":
    update_source()
