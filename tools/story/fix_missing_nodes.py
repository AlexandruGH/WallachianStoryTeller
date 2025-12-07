import json

source_path = "story_packs/episode_1/strajer_source.json"

# Nodes to add or link
new_nodes = {
    # --- Interogatoriu Branch ---
    "Cere o trupă de asalt.": {
        "narrative": "Căpitanul îți dă cinci soldați veterani. \"Să nu vă întoarceți până nu curățați cuibul de șobolani.\" Plecați în forță spre mănăstire.",
        "suggestions": ["Mergi la mănăstirea părăsită."],
        "reputation_change": 2,
        "episode_progress": 0.45
    },
    "Spune-i Căpitanului.": {
        "narrative": "Îi raportezi tot ce a spus vizitiul. Căpitanul încruntă sprâncenele. \"Deci Mănăstirea Dealu... Pregătește-te de drum.\"",
        "suggestions": ["Mergi la mănăstirea părăsită.", "Cere echipament mai bun."],
        "episode_progress": 0.45
    },

    # --- Chase Branch ---
    "Taie-i calea prin ulițe.": {
        "narrative": "Cunoști orașul mai bine ca el. Scurtezi printre case și ieși fix în fața carului. Vizitiul trage de hățuri, surprins!",
        "suggestions": ["Sari pe capră.", "Lovește caii.", "Strigă să se predea."],
        "episode_progress": 0.28
    },
    "Cere un cal unui trecător.": {
        "narrative": "\"În numele Vodă!\" strigi. Trecătorul, speriat, coboară. Ești călare în câteva secunde.",
        "suggestions": ["Galop după car!"],
        "episode_progress": 0.25
    },
    "Cheamă întăriri din șa.": {
        "narrative": "Strigi la gărzile de pe ziduri în timp ce galopezi. Ele sună din corn. Orașul e alertat.",
        "suggestions": ["Galop după car!"],
        "reputation_change": 1,
        "episode_progress": 0.26
    },
    "Ocolește pentru a-i tăia calea.": {
        "narrative": "Galopezi pe o stradă paralelă. Ajungi la intersecție înaintea lui.",
        "suggestions": ["Sari pe capră.", "Blochează drumul cu calul."],
        "episode_progress": 0.28
    },
    "Sari pe capră.": { # Helper for above
        "narrative": "Te lansezi în aer și aterizezi lângă vizitiu. El scoate un pumnal!",
        "suggestions": ["Luptă cu vizitiul.", "Îmbrâncește-l."],
        "episode_progress": 0.3
    },
    "Luptă cu vizitiul.": {
        "narrative": "Vă luptați pe carul în mișcare. E puternic, dar tu ești antrenat. Îi prinzi mâna înarmată.",
        "suggestions": ["Aruncă-l din car.", "Dezarmează-l."],
        "health_change": -2,
        "episode_progress": 0.32
    },
    "Aruncă-l din car.": {
        "narrative": "Cu un efort suprem, îl împingi. Cade în praf, rostogolindu-se. Oprești carul. Ai învins.",
        "suggestions": ["Arestați vizitiul.", "Verifică carul."],
        "episode_progress": 0.35
    },
    "Oprește caii.": {
        "narrative": "Tragi de hățuri. Caii se ridică în două picioare și se opresc. Vizitiul sare și fuge.",
        "suggestions": ["Fugi după vizitiu.", "Lasă-l și verifică carul."],
        "episode_progress": 0.35
    },
    
    # --- Investigation ---
    "Cere numele celui care l-a plătit.": {
        "narrative": "Vizitiul ezită, apoi șoptește: \"Un boier... cu inel de aur și rubin. Nu știu numele, dar l-am văzut intrând la Curte.\"",
        "suggestions": ["Raportează la căpitan.", "Notează descrierea."],
        "episode_progress": 0.35
    },
    "Intră cu sabia scoasă.": {
        "narrative": "Dai ușa de perete! Înăuntru e pustiu, doar urme recente și o trapă deschisă spre beci.",
        "suggestions": ["Intră în pasaj.", "Cheamă ajutoare."],
        "episode_progress": 0.35
    },
    "Cheamă ajutoare.": {
        "narrative": "Câțiva străjeri vin la strigătul tău. Împreună înconjurați casa. Dar păsărelele au zburat.",
        "suggestions": ["Intră în pasaj.", "Caută indicii în cameră."],
        "episode_progress": 0.35
    },
    "Pândește ferestrele.": {
        "narrative": "Nu se vede mișcare. Doar o umbră care coboară undeva în podea.",
        "suggestions": ["Intră cu sabia scoasă.", "Dă foc casei (Radical)."],
        "episode_progress": 0.35
    },

    # --- Endings / Transitions ---
    "Mergi la război.": {
        "narrative": "Te alături oastei lui Vlad. Vei lupta pentru Valahia cu sabia în mână. (Sfârșit Episod 1 - Calea Războinicului)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Acceptă destinul.": {
        "narrative": "Ai jurat credință. Soarta ta e legată de cea a Voievodului. (Sfârșit Episod 1 - Loialist)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Predă raportul.": {
        "narrative": "Căpitanul te ascultă. \"Ai făcut o treabă bună azi. Odihnește-te.\" (Sfârșit Episod 1 - Succes)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Mergi la infirmerie.": {
        "narrative": "Rănile sunt îngrijite. Vei avea cicatrice, dar vei trăi. (Sfârșit Episod 1 - Supraviețuitor)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Curăță-ți armele.": {
        "narrative": "Ștergi sângele de pe oțel. Ești gata pentru următoarea luptă. (Sfârșit Episod 1 - Pregătit)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Jură răzbunare.": {
        "narrative": "Nu vei uita această înfrângere. Dăneștii vor plăti. (Sfârșit Episod 1 - Răzbunător)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Raportează eșecul.": {
        "narrative": "Vlad nu tolerează incompetența, dar are nevoie de oameni. Ești retrogradat la paza grajdurilor. (Sfârșit Episod 1 - Eșec)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },

    # --- Combat / Action fillers ---
    "Fugi după lider, ignorând lupta.": {
        "narrative": "Te ferești de săbii și alergi după cel cu fragmentul. El intră în tunel.",
        "suggestions": ["Ignoră-l și fugi în tunel."],
        "episode_progress": 0.68
    },
    "Trage: Dragon, Lup, Vultur.": {
        "narrative": "Se aude un clic, dar nu se deschide. O trapă se deschide sub tine! Cazi!",
        "suggestions": ["Prinde-te de margine.", "Lasă-te să cazi."],
        "health_change": -5,
        "episode_progress": 0.85
    },
    "Prinde-te de margine.": {
        "narrative": "Te ții cu vârfurile degetelor. Te ridici gâfâind. Mai ai o încercare.",
        "suggestions": ["Examinează pârghiile (Puzzle)."],
        "episode_progress": 0.85
    },
    
    # --- Missing from previous lists ---
    "Fugi spre ieșire.": { "narrative": "Profite de confuzie și fugi spre ușa din spate.", "suggestions": ["Blochează ușa.", "Fugi după cel cu fragmentul."], "episode_progress": 0.7 },
    "Atacă cât sunt orbiți.": { "narrative": "Lovesti în stânga și dreapta. Inamicii sunt dezorientați.", "suggestions": ["Termină lupta rapid (riscant).", "Fugi după cel cu fragmentul."], "episode_progress": 0.7 },
    "Ascunde-te.": { "narrative": "Te lipești de un stâlp în umbră. Ei trec pe lângă tine.", "suggestions": ["Atacă-i din spate.", "Fugi după lider."], "episode_progress": 0.7 },
    "Prinde-l din urmă.": { "narrative": "Alergi mai tare ca niciodată. Îl ajungi din urmă la ieșirea din tunel.", "suggestions": ["Sari pe el.", "Luptă cu el."], "episode_progress": 0.75 },
    "Trage cu arbaleta în picior.": { "narrative": "Nimerești! El cade urlând. Fragmentul îi scapă din mână.", "suggestions": ["Ia fragmentul și leagă-l.", "Termină-l."], "episode_progress": 0.8 },
    "Strigă să se predea.": { "narrative": "El râde și fuge mai tare. Ai pierdut timp.", "suggestions": ["Fugi după el."], "episode_progress": 0.75 },
    
    # Generic fillers for simple interactions
    "Arată harta Căpitanului.": { "narrative": "Vezi 'Raportează la căpitan'.", "suggestions": ["Raportează la căpitan."], "episode_progress": 0.4 }, # Redirect
    "Ascunde harta.": { "narrative": "Pui harta la sân. E sigură.", "suggestions": ["Mergi la mănăstirea părăsită."], "episode_progress": 0.4 },
    "Mergi să verifici tunelul.": { "narrative": "Intri în tunelurile de sub palat. E întuneric.", "suggestions": ["Aprinde o torță.", "Mergi tiptil."], "episode_progress": 0.45 },
    
    "Fură un cal și anunță garda.": { "narrative": "Iei un cal legat la poartă și galopezi spre cazarmă.", "suggestions": ["Strigă alarma."], "episode_progress": 0.5 },
    "Sabotează-le carele.": { "narrative": "Tai osiile la două care. Asta îi va încetini.", "suggestions": ["Intră furișat în criptă."], "episode_progress": 0.55 },
    
    "Caută punctele slabe ale armurilor.": { "narrative": "Sunt armuri ușoare, slabe la încheieturi și gât.", "suggestions": ["Mergi la mănăstirea părăsită."], "episode_progress": 0.45 },
    
    "Pândește intrarea.": { "narrative": "Aștepți. Nimeni nu iese.", "suggestions": ["Pleacă spre curte."], "episode_progress": 0.95 },
    "Caută calul mercenarului.": { "narrative": "Găsești calul legat lângă zid.", "suggestions": ["Ia fragmentul și calul."], "episode_progress": 0.95 },
    
    "Ocolește prin pădure.": { "narrative": "Alegi drumul lung dar sigur.", "suggestions": ["Pleacă spre curte."], "episode_progress": 1.0 },
    "Verifică dacă ești urmărit.": { "narrative": "Nimeni în spate. Ești în siguranță.", "suggestions": ["Pleacă spre curte."], "episode_progress": 1.0 },
    
    "Caută urme.": { "narrative": "Urmele duc în adâncul pădurii. I-ai pierdut.", "suggestions": ["Raportează eșecul."], "episode_progress": 0.8 },
    "Renunță.": { "narrative": "Te întorci cu mâna goală.", "suggestions": ["Raportează eșecul."], "episode_progress": 0.9 },
    
    "Fugi să dai alarma.": { "narrative": "Fugi spre ieșire, dar ei te văd.", "suggestions": ["Luptă cu cei doi.", "Fugi spre ieșire să le tai calea."], "episode_progress": 0.65 },
    "Sabotează explozibilul.": { "narrative": "Încerci să uzi praful, dar te aud.", "suggestions": ["Luptă cu cei doi."], "episode_progress": 0.65 },
    
    "Intră în tunel.": { "narrative": "Intri în întuneric.", "suggestions": ["Ignoră-l și fugi în tunel."], "episode_progress": 0.7 },
    "Luptă mai departe.": { "narrative": "Te ridici și ataci.", "suggestions": ["Termină lupta rapid (riscant)."], "episode_progress": 0.7 },
    "Mulțumește providenței.": { "narrative": "Ai avut noroc. Acum, la treabă.", "suggestions": ["Intră în tunel."], "episode_progress": 0.7 },
    
    "Leagă-l și intră în tunel.": { "narrative": "Îl lași legat și intri în tunel.", "suggestions": ["Ignoră-l și fugi în tunel."], "episode_progress": 0.75 },
    "Lovitură de grație.": { "narrative": "Îi curmi suferința.", "suggestions": ["Intră în tunel."], "episode_progress": 0.75 },
    "Folosește-l ca scut.": { "narrative": "Îl împingi înainte.", "suggestions": ["Intră în tunel."], "episode_progress": 0.75 },
    
    "Trimite-i înainte.": { "narrative": "Voluntarii atacă frontal, creând o diversiune.", "suggestions": ["Atacă-i din umbră.", "Fugi după cel cu fragmentul."], "episode_progress": 0.5 },
    "Înmarchează-i.": { "narrative": "Îi organizezi într-o mică trupă.", "suggestions": ["Mergi la mănăstirea părăsită."], "episode_progress": 0.45 },
    
    "Intră în pasaj.": { "narrative": "Pasajul e îngust și duce spre criptă.", "suggestions": ["Intră furișat în criptă."], "episode_progress": 0.5 },
    "Verifică capcanele.": { "narrative": "Găsești o sârmă întinsă. O eviți.", "suggestions": ["Intră în pasaj."], "episode_progress": 0.8 },
    "Aruncă o torță înăuntru.": { "narrative": "Luminezi pasajul. Pare sigur.", "suggestions": ["Intră în pasaj."], "episode_progress": 0.8 },
    
    "Cere o binecuvântare.": { "narrative": "Preotul te binecuvântează. Te simți mai puternic.", "suggestions": ["Mergi la mănăstirea părăsită."], "health_change": 5, "episode_progress": 0.4 },
    "Ignoră sfatul.": { "narrative": "Pleci fără să mai asculți.", "suggestions": ["Mergi la mănăstirea părăsită."], "episode_progress": 0.4 },
    
    "Treci pe sub ea.": { "narrative": "Te rostogolești pe sub poartă în ultima secundă.", "suggestions": ["Trage: Vultur, Lup, Dragon."], "episode_progress": 0.85 }, # Reuse puzzle flow logic? Or just skip to chase
    "Blocheaz-o cu o piatră.": { "narrative": "Pui o piatră sub ea. Ai cale liberă.", "suggestions": ["Trage: Vultur, Lup, Dragon."], "episode_progress": 0.85 },
    "Las-o să cadă.": { "narrative": "Poarta cade. Ești blocat, dar ai găsit alt drum.", "suggestions": ["Caută un pasaj secret."], "episode_progress": 0.8 },
    
    "Mulțumește.": { "narrative": "Mulțumești Căpitanului.", "suggestions": ["Mergi la mănăstirea părăsită."], "episode_progress": 0.45 },
    "Cere și o sabie.": { "narrative": "Primești și o sabie bine ascuțită.", "suggestions": ["Mergi la mănăstirea părăsită."], "items_gained": [{"name": "Sabie de oțel", "type": "armă", "value": 10, "quantity": 1}], "episode_progress": 0.45 },
    
    "Ferește-te de foc.": { "narrative": "Te dai în spate. Praful nu ia foc încă.", "suggestions": ["Arestați vizitiul."], "episode_progress": 0.15 },
    
    # Fix for: [MISSING] From 'Aleargă după lider, sângerând.' -> Suggestion 'Urmărește-l în pădure.' is undefined.
    "Urmărește-l în pădure.": { "narrative": "Intri în pădure după el.", "suggestions": ["Caută urme.", "Trage o ultimă săgeată."], "episode_progress": 0.78 },
    "Bandajează-te întâi.": { "narrative": "Îți legi rănile. Pierzi timp, dar oprești sângerarea.", "suggestions": ["Urmărește-l în pădure."], "health_change": 5, "episode_progress": 0.78 },
    "Trage o ultimă săgeată.": { "narrative": "Tragi la întâmplare. Auzi un țipăt!", "suggestions": ["Caută cadavrul."], "episode_progress": 0.8 },
    "Caută cadavrul.": { "narrative": "L-ai nimerit! E mort.", "suggestions": ["Ia fragmentul și calul."], "episode_progress": 0.9 }
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
                # Optional: Update existing if needed? For now, assume manual fix priority.
                pass
        
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully updated source file.")
        
    except Exception as e:
        print(f"Error updating source: {e}")

if __name__ == "__main__":
    update_source()
