import json

source_path = "story_packs/episode_1/strajer_source.json"

updates = {
    "Observă de la distanță (Vigilență).": { # Maps to old "Pândește"
        "narrative": "Te lipești de zidul unei case. După câteva minute, o siluetă encapșonată iese de pe ulița fierarilor. Se apropie de car și schimbă câteva vorbe cu vizitiul. Auzi doar fragmente: '...la Mănăstirea Dealu... arme... Dăneștii plătesc bine'. Străinul îi dă un pergament vizitiului.",
        "suggestions": [
            "Urmărește-l pe străin (Mesagerul).",
            "Atacă-i pe amândoi acum.",
            "Așteaptă să plece carul și urmărește-l."
        ],
        "episode_progress": 0.1
    },
    "Somează-l (Autoritate).": { # Maps to old "Ieși în față"
        "narrative": "\"În numele Voievodului Vlad, stai pe loc!\" Vocea ta tună în piață. Vizitiul tresare, dar nu se supune. Mâna lui coboară fulgerător sub capră și scoate o arbaletă încărcată! \"Mori, câine de Drăculești!\"",
        "suggestions": [
            "Ferește-te și scoate sabia!",
            "Aruncă-te la pământ și strigă după ajutor.",
            "Încearcă să-l intimidezi (Reputație)."
        ],
        "episode_progress": 0.1
    }
}

def update_source():
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, content in updates.items():
            if key not in data:
                data[key] = content
                print(f"Added node: {key}")
            else:
                print(f"Skipped existing: {key}")
        
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully patched missing root nodes.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_source()
