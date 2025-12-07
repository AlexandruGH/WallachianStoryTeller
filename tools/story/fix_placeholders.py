import os
import json
import glob
import random

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- NARRATIVE TEMPLATES ---
COMBAT_NARRATIVES = [
    "Scoți arma și te arunci în luptă. Inamicul este surprins de ferocitatea ta. Oțelul se ciocnește de oțel. După câteva schimburi dure, adversarul cade la pământ, învins.",
    "Atacul tău este rapid și precis. Nu le lași timp de reacție. În scurt timp, ești singurul care mai stă în picioare. Adrenalina îți pulsează în vene.",
    "Te ferești de o lovitură mortală și ripostezi decisiv. Lupta este scurtă, dar brutală. Îți ștergi lama de sânge și privești în jur."
]
COMBAT_SUGGESTIONS = [
    ["Verifică cadavrele.", "Pleacă rapid din zonă.", "Bandajează-te."],
    ["Ia armele lor.", "Ascunde corpurile.", "Caută martori."],
    ["Recuperează suflul.", "Curăță sabia.", "Pregătește-te de următoarea luptă."]
]

MOVE_NARRATIVES = [
    "Te deplasezi rapid prin umbre. Nimeni nu te observă. Ajungi la destinație fără incidente, dar simți că ești urmărit.",
    "Drumul este greu, dar ești obișnuit cu efortul. Peisajul se schimbă. Ajungi într-un loc nou, plin de posibilități... și pericole.",
    "Alergi până simți gust de sânge în gură. Ai lăsat pericolul în urmă. Acum ești într-o zonă liniștită, cel puțin aparent."
]
MOVE_SUGGESTIONS = [
    ["Privește în jur cu atenție.", "Caută un adăpost.", "Așteaptă să vezi ce se întâmplă."],
    ["Investighează zona.", "Ascultă zgomotele.", "Verifică harta."],
    ["Odihnește-te puțin.", "Pregătește armele.", "Caută urme."]
]

SOCIAL_NARRATIVES = [
    "Cuvintele tale sunt bine alese. Interlocutorul te privește cu respect (sau frică). Îți spune ce vrei să auzi, sperând să scape de tine.",
    "Negocierea este o artă, iar tu ești un maestru. După câteva replici schimbate, ajungeți la o înțelegere. Ai obținut informația dorită.",
    "Ridici tonul și mulțimea se dă înapoi. Autoritatea ta este incontestabilă. Oamenii fac loc și răspund la întrebări."
]
SOCIAL_SUGGESTIONS = [
    ["Mulțumește și pleacă.", "Cere mai multe detalii.", "Amenință-l să tacă."],
    ["Aruncă-i un ban.", "Notează informația.", "Verifică dacă minte."],
    ["Cere o dovadă.", "Pleacă spre noua pistă.", "Recrutează-l."]
]

INVESTIGATE_NARRATIVES = [
    "Cercetezi cu atenție. Nu îți scapă nimic. Găsești un indiciu ascuns: o bucată de pergament ars, o urmă de cizmă sau o monedă străină.",
    "Îți folosești simțurile ascuțite. Ceva nu e la locul lui. Sub un strat de praf, descoperi un mecanism sau un obiect uitat.",
    "Analizezi situația la rece. Detaliile se leagă. Acum înțelegi mai bine ce s-a întâmplat aici. Piesa lipsă din puzzle este în mâinile tale."
]
INVESTIGATE_SUGGESTIONS = [
    ["Ia obiectul găsit.", "Analizează-l mai bine.", "Lasă-l acolo (capcană?)."],
    ["Notează descoperirea.", "Urmărește pista.", "Arată-l cuiva."],
    ["Păstrează secretul.", "Folosește indiciul.", "Mergi mai departe."]
]

GENERIC_NARRATIVES = [
    "Acțiunea ta are consecințe neașteptate. Situația se schimbă, deschizând noi oportunități. Trebuie să te adaptezi rapid.",
    "Reușești să duci planul la bun sfârșit. Totul a decurs conform așteptărilor. Acum, drumul este liber pentru următoarea mișcare.",
    "Evenimentele se precipită. Ești în mijlocul acțiunii. Nu e timp de ezitare. Instinctul îți spune să continui."
]
GENERIC_SUGGESTIONS = [
    ["Mergi mai departe.", "Fii precaut.", "Grăbește-te."],
    ["Evaluează situația.", "Caută avantaje.", "Pregătește-te."],
    ["Continuă misiunea.", "Ia o pauză.", "Verifică echipamentul."]
]

def get_replacement(key):
    key_lower = key.lower()
    
    if any(x in key_lower for x in ["lupt", "atac", "omoară", "trage", "lovește", "ucide", "săbi", "pumn"]):
        idx = random.randint(0, len(COMBAT_NARRATIVES)-1)
        return COMBAT_NARRATIVES[idx], COMBAT_SUGGESTIONS[idx]
    
    if any(x in key_lower for x in ["mergi", "fugi", "urmărește", "pleacă", "intră", "ieși", "coboară", "urcă"]):
        idx = random.randint(0, len(MOVE_NARRATIVES)-1)
        return MOVE_NARRATIVES[idx], MOVE_SUGGESTIONS[idx]
        
    if any(x in key_lower for x in ["vorbește", "întreabă", "cere", "strigă", "negociază", "minte", "convinge", "mitu", "anunță"]):
        idx = random.randint(0, len(SOCIAL_NARRATIVES)-1)
        return SOCIAL_NARRATIVES[idx], SOCIAL_SUGGESTIONS[idx]
        
    if any(x in key_lower for x in ["caută", "verifică", "examinează", "observă", "studiază", "citește", "ascultă"]):
        idx = random.randint(0, len(INVESTIGATE_NARRATIVES)-1)
        return INVESTIGATE_NARRATIVES[idx], INVESTIGATE_SUGGESTIONS[idx]
        
    idx = random.randint(0, len(GENERIC_NARRATIVES)-1)
    return GENERIC_NARRATIVES[idx], GENERIC_SUGGESTIONS[idx]

def fix_file(filepath):
    data = load_json(filepath)
    modified = False
    
    placeholder_marker = "a fost executată, dar povestea este încă în lucru"
    
    # Iterate over a copy because we might modify dictionary size
    for key, node in list(data.items()):
        narrative = node.get("narrative", "")
        if placeholder_marker in narrative:
            print(f"  - Replacing placeholder for: '{key}'")
            new_text, new_suggs = get_replacement(key)
            node["narrative"] = new_text
            node["suggestions"] = new_suggs
            # Keep progress/win as is or default
            modified = True
            
            # Also ensure the NEW suggestions have entries (recursion risk avoided by simplistic filling)
            # But we need to ensure they exist in the file to avoid NEW fallbacks.
            # So we add them as "Generic Endings" if missing.
            for s in new_suggs:
                if s not in data:
                    data[s] = {
                        "narrative": "Acțiunea continuă. Ești pe drumul cel bun.",
                        "suggestions": ["Mergi înainte."],
                        "episode_progress": (node.get("episode_progress") or 0) + 0.1
                    }
                    if "Mergi înainte." not in data:
                        data["Mergi înainte."] = {
                             "narrative": "Te apropii de deznodământ.",
                             "suggestions": [],
                             "episode_progress": 1.0,
                             "win_condition": True
                        }
    
    if modified:
        save_json(filepath, data)
        print(f"✅ Updated {filepath}")

def main():
    files = glob.glob("story_packs/**/*_source.json", recursive=True)
    files += glob.glob("story_packs/*_source.json")
    
    for f in files:
        fix_file(f)

if __name__ == "__main__":
    main()
