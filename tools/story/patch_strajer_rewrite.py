import json

source_path = "story_packs/episode_1/strajer_source.json"

new_nodes = {
    # --- Missing Combat/Action ---
    "Aruncă-te la pământ și strigă după ajutor.": {
        "narrative": "Te rostogolești în noroi. Săgeata trece pe deasupra ta. Străjerii de pe ziduri aud și sună alarma. Vizitiul fuge, lăsând carul.",
        "suggestions": ["Examinează carul abandonat."],
        "reputation_change": -1,
        "episode_progress": 0.4
    },
    "Încearcă să-l intimidezi (Reputație).": {
        "narrative": "\"Știi cine sunt eu?! Predă-te și poate scapi cu viață!\" Vizitiul ezită o secundă, intimidat de uniforma ta.",
        "suggestions": ["Dezarmează-l și arestează-l."],
        "episode_progress": 0.4
    },
    "Lovește-l pe la spate.": {
        "narrative": "Îl lovești cu mânerul sabiei la ceafă. Cade lat.",
        "suggestions": ["Dezarmează-l și arestează-l.", "Caută rapid indicii și pleacă."],
        "episode_progress": 0.4
    },
    "Fură pergamentul de la brâu.": {
        "narrative": "Ai mâini iuți. Iei pergamentul fără să simtă. Te retragi în umbră și citești: Planul de atac.",
        "suggestions": ["Fugi la Căpitan (Sigur)."],
        "items_gained": [{"name": "Planul de Atac", "type": "obiect_important", "value": 0, "quantity": 1}],
        "episode_progress": 0.5
    },
    "Intră cu sabia în mână.": {
        "narrative": "Dai buzna peste ei. Sunt surprinși.",
        "suggestions": ["Intră și ucide conspiratorii (Eroic)."],
        "episode_progress": 0.6
    },
    "Dă foc casei să-l scoți afară.": {
        "narrative": "Fumul îi scoate afară tușind. Îi aștepți cu sabia scoasă.",
        "suggestions": ["Dezarmează-l și arestează-l."],
        "reputation_change": -5, # Arson isn't great policing
        "episode_progress": 0.6
    },
    "Întoarce-te și raportează Căpitanului.": {
        "narrative": "Decizi să nu riști singur. Raportezi totul. Căpitanul trimite cavaleria.",
        "suggestions": ["Rămâi în alertă (Sfârșit)."],
        "episode_progress": 1.0
    },
    "Luptă pentru viața ta.": {
        "narrative": "Vizitiul te atacă cu o furie oarbă.",
        "suggestions": ["Luptă defensiv și obosește-l.", "Atacă furibund (Riscant)."],
        "episode_progress": 0.3
    },
    "Fugi și dă alarma.": {
        "narrative": "Fugi spre poartă strigând. Vizitiul încearcă să întoarcă carul, dar se blochează.",
        "suggestions": ["Cheamă gărzile de la poartă."],
        "episode_progress": 0.3
    },
    "Dă foc la praf (Sinucigaș).": {
        "narrative": "Arunci torța în car. O explozie asurzitoare spulberă totul, inclusiv pe tine. Ai salvat orașul cu prețul vieții.",
        "suggestions": ["Rejoacă."],
        "game_over": True,
        "episode_progress": 1.0
    },
    "Fură dovezile și pleacă.": {
        "narrative": "Iei harta de pe masă în timp ce ei se ceartă și sari pe geam.",
        "suggestions": ["Fugi la Căpitan (Sigur)."],
        "episode_progress": 0.7
    },
    "Curmă-i zilele.": {
        "narrative": "Nu ai timp de prizonieri. Îl străpungi. Mortul nu mai vorbește.",
        "suggestions": ["Caută rapid indicii și pleacă."],
        "episode_progress": 0.8
    },
    "Întreabă cine l-a trimis (cu sabia la gât).": {
        "narrative": "\"Dăneștii! Dăneștii plătesc!\" urlă el de frică.",
        "suggestions": ["Du-l la Căpitan (Final Bun)."],
        "episode_progress": 0.9
    },
    "Trage cu arcul după el.": {
        "narrative": "Săgeata îl lovește în spate. Cade de pe cal. Carul rămâne abandonat.",
        "suggestions": ["Examinează carul abandonat."],
        "episode_progress": 0.8
    },
    "Interoghează-l dur pe loc.": {
        "narrative": "Îl strângi de gât până vorbește.",
        "suggestions": ["Întreabă cine l-a trimis (cu sabia la gât)."],
        "reputation_change": -2,
        "episode_progress": 0.85
    },
    "Raportează eșecul.": {
        "narrative": "Căpitanul e furios. \"Ai lăsat să scape un spion?! Treci la curățat grajdurile!\" (Final Slab).",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    }
}

def update_source():
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, content in new_nodes.items():
            if key not in data:
                data[key] = content
                print(f"Added node: {key}")
            else:
                print(f"Skipped existing: {key}")
        
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully patched Strajer Story Source.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_source()
