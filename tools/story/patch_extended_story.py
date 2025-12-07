import json

source_path = "story_packs/episode_1/strajer_source.json"

new_nodes = {
    # --- Grămătic ---
    "Amenință-l cu trădarea.": {
        "narrative": "Pui mâna pe sabie. \"Dacă nu traduci, ești complice.\" El tremură și îți dă traducerea imediat.",
        "suggestions": ["Fugi la Căpitan cu traducerea."],
        "reputation_change": -1,
        "episode_progress": 0.4
    },
    "Oferă-i bani (5 galbeni).": {
        "narrative": "Ochii îi sclipesc. \"Pentru așa sumă... riscul merită.\" Îți traduce mesajul: Mănăstirea Dealu, miezul nopții.",
        "suggestions": ["Fugi la Căpitan cu traducerea."],
        "gold_change": -5,
        "episode_progress": 0.4
    },

    # --- Taverna ---
    "Provoacă-i la joc de zaruri.": {
        "narrative": "Te așezi la masă. Pierzi intenționat o mână, apoi îi tragi de limbă. Unul se laudă cu \"focul de la mănăstire\".",
        "suggestions": ["Ieși și raportează."],
        "gold_change": -2,
        "episode_progress": 0.45
    },
    "Ia-l pe unul la întrebări afară.": {
        "narrative": "Îl aștepți când iese să se ușureze. Îl prinzi de gât. Mărturisește tot despre Mănăstire.",
        "suggestions": ["Ieși și raportează.", "Lasă-l inconștient."],
        "episode_progress": 0.45
    },
    "Urmărește-i când pleacă.": {
        "narrative": "Se îndreaptă spre ieșirea din oraș. Îi urmărești până la un grajd secret unde își țin caii.",
        "suggestions": ["Fugi la Căpitan cu traducerea.", "Fură un cal și urmărește-i."],
        "episode_progress": 0.5
    },
    "Lasă-l inconștient.": {
        "narrative": "Îl lovești și pleci. Nimeni nu a văzut.",
        "suggestions": ["Ieși și raportează."],
        "episode_progress": 0.5
    },
    "Fură un cal și urmărește-i.": {
        "narrative": "Galopezi după ei până la Mănăstire.",
        "suggestions": ["Mergi singur în recunoaștere la Mănăstire."],
        "episode_progress": 0.55
    },

    # --- Căpitan ---
    "Întoarce-te în piață să verifici carul.": {
        "narrative": "Te întorci, dar carul a dispărut. Ai pierdut urma. Eșec.",
        "suggestions": ["Raportează eșecul."],
        "episode_progress": 0.9
    },
    
    # --- Mănăstire ---
    "Escaladează zidul din spate.": {
        "narrative": "Zidul e vechi și măcinat. Urc ușor. Ești în spatele magaziei.",
        "suggestions": ["Sabotează stocul de arme."],
        "episode_progress": 0.6
    },
    "Crează o diversiune (Foc).": {
        "narrative": "Dai foc la niște fân. Toți aleargă să stingă. Ai calea liberă spre centru.",
        "suggestions": ["Sabotează stocul de arme."],
        "episode_progress": 0.65
    },
    "Pândește de pe acoperiș.": {
        "narrative": "Ai o vedere perfectă. Poți trage cu arbaleta în butoaiele cu praf.",
        "suggestions": ["Trage în butoaie (Explozie)."],
        "episode_progress": 0.7
    },
    "Trage în butoaie (Explozie).": {
        "narrative": "Săgeata lovește butoiul. Scânteie. BOOM! Misiune îndeplinită.",
        "suggestions": ["Ascunde-te în pădure."],
        "episode_progress": 0.9
    },
    "Asasinează liderul (Foarte Riscant).": {
        "narrative": "Sari pe el din umbră. E o luptă pe viață și pe moarte. Reușești să-l înjunghii, dar ești grav rănit.",
        "suggestions": ["Târăște-te afară (Sfârșit)."],
        "health_change": -50,
        "episode_progress": 0.9
    },
    "Târăște-te afară (Sfârșit).": {
        "narrative": "Scapi cu viață. Liderul e mort, atacul e anulat. Ești un erou, dar vei sta mult la pat.",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Așteaptă momentul oportun.": {
        "narrative": "Aștepți prea mult. Te văd! Ești înconjurat.",
        "suggestions": ["Luptă până la capăt (Moarte Glorioasă)."],
        "episode_progress": 0.9
    },
    "Luptă până la capăt (Moarte Glorioasă).": {
        "narrative": "Iei cu tine 5 inamici înainte să cazi. Legenda ta va fi cântată.",
        "suggestions": ["Rejoacă."],
        "game_over": True,
        "episode_progress": 1.0
    },
    "Luptă pentru scăpare.": {
        "narrative": "Îți croiești drum cu sabia. Scapi, dar ești rănit.",
        "suggestions": ["Fugi înapoi la cetate (Eșec parțial)."],
        "episode_progress": 0.9
    },

    # --- Misc ---
    "Fugi spre piață.": {
        "narrative": "Fugi în mulțime (care începe să se adune). Te pierzi de ei.",
        "suggestions": ["Raportează Căpitanului incidentul."], # Leads to end
        "episode_progress": 0.8
    },
    "Urmărește-i.": {
        "narrative": "Îi urmărești în pădure. Găsești tabăra lor mică.",
        "suggestions": ["Atacă-i pe amândoi acum."],
        "episode_progress": 0.6
    },
    "Securizează carul și raportează.": {
        "narrative": "Păzești carul până vin întăriri. Captură bună.",
        "suggestions": ["Du carul la cetate (Final Bun)."],
        "episode_progress": 0.9
    },
    "Fugi și dă alarma.": { # Redirect
        "narrative": "Alergi spre cazarmă urlând.",
        "suggestions": ["Cheamă gărzile de la poartă."],
        "episode_progress": 0.5
    },
    "Trage din nou.": {
        "narrative": "Încă o săgeată. Încă un mort. Ultimul fuge.",
        "suggestions": ["Securizează carul și raportează."],
        "episode_progress": 0.8
    },
    "Percheziționează vizitiul.": {
        "narrative": "Găsești un pumnal ascuns și un pergament.",
        "suggestions": ["Citește pergamentul."], # Redirects to code logic
        "episode_progress": 0.2
    },
    "Atacă-l când e atent la lădiță.": {
        "narrative": "Îl lovești. Cade peste ladă. O deschizi: aur Dănești.",
        "suggestions": ["Dezarmează-l și arestează-l."],
        "items_gained": [{"name": "Pungă cu Aur", "type": "monedă", "value": 50, "quantity": 1}],
        "episode_progress": 0.3
    },
    "Trage cu arbaleta.": {
        "narrative": "Îl nimerești în picior. Nu mai fuge nicăieri.",
        "suggestions": ["Dezarmează-l și arestează-l."],
        "episode_progress": 0.3
    },
    "Interoghează-l dur pe loc.": {
        "narrative": "Îl strângi de gât. \"Mănăstirea Dealu! Acolo e baza!\"",
        "suggestions": ["Fugi la Căpitan (Sigur)."],
        "reputation_change": -2,
        "episode_progress": 0.8
    },
    
    # Missing Endings
    "Rejoacă.": { "narrative": "Sfârșit.", "suggestions": [], "win_condition": True }
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
                pass
        
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully patched Extended Story.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_source()
