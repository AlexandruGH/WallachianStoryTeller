import json
import os

output_path = "story_packs/episode_1/strajer_source.json"

story_data = {
    # --- SCENA 1: INTRODUCERE (PIAȚA TÂRGOVIȘTE - DIMINEAȚA) ---
    "Mă apropii discret de carul negru.": {
        "narrative": "Este o dimineață rece de iarnă. Ceața se ridică leneș de pe caldarâmul Pieței Târgoviștei. Târgoveții abia își deschid obloanele. Carul negru e oprit lângă Fântâna Veche, contrastând cu albul zăpezii. Vizitiul, un individ masiv, pare agitat și verifică constant împrejurimile. Roțile carului sunt afundate adânc în noroi, semn că încărcătura e nefiresc de grea pentru niște simpli 'saci cu grâne'.",
        "suggestions": [
            "Observă de la distanță (Vigilență).",
            "Somează-l (Autoritate).",
            "Aruncă o piatră pentru a-i distrage atenția."
        ],
        "reputation_change": 0
    },

    # --- RAMURA: DIVERSIUNE & FURT (EXTINSĂ) ---
    "Aruncă o piatră pentru a-i distrage atenția.": {
        "narrative": "Piatra lovește caldarâmul cu zgomot. Vizitiul se întoarce brusc, cu mâna pe un cuțit. \"Cine-i acolo?!\" Profitând de moment, te poți strecura în spatele carului. În timp ce se întoarce, observi un tub de pergament prins neglijent la brâul său.",
        "suggestions": [
            "Taie prelata să vezi încărcătura.",
            "Fură pergamentul de la brâu.",
            "Lovește-l și imobilizează-l."
        ],
        "episode_progress": 0.1
    },

    # Furt Pergament -> CODIFICAT
    "Fură pergamentul de la brâu.": {
        "narrative": "Ai mâini iuți. Iei pergamentul fără să simtă și te retragi rapid într-o alee lăturalnică. Rup sigiliul. E scris într-un cifru ciudat, cu simboluri ungurești și otomane. Nu poți citi decât: '...la ceasul bufniței...'. Ai nevoie de ajutor.",
        "suggestions": [
            "Mergi la Grămăticul Curții (Erudit).",
            "Caută informatori în Taverna 'La Lupul Șchiop'.",
            "Du-te direct la Căpitan cu documentul."
        ],
        "items_gained": [{"name": "Pergament Codificat", "type": "obiect_important", "value": 0, "quantity": 1}],
        "episode_progress": 0.2
    },

    # --- RAMURA: INVESTIGAȚIE (MID-GAME) ---

    # 1. Grămăticul
    "Mergi la Grămăticul Curții (Erudit).": {
        "narrative": "Bătrânul logofăt te primește cu greu. Se uită la pergament și pălește. \"Acesta e cifrul Dăneștilor... dar combinat cu cel al Ienicerilor. Dacă traduc asta, capul meu va cădea primul. Îmi trebuie protecție.\"",
        "suggestions": [
            "Promite-i protecția Gărzii.",
            "Amenință-l cu trădarea.",
            "Oferă-i bani (5 galbeni)."
        ],
        "episode_progress": 0.3
    },
    "Promite-i protecția Gărzii.": {
        "narrative": "\"Bine...\" tremură el. \"Scrie aici: 'Armele sunt ascunse în pivnițele Mănăstirii Părăsite. Atacul începe când clopotele bat de miezul nopții.'\" Ai locația și ora!",
        "suggestions": [
            "Fugi la Căpitan cu traducerea.",
            "Mergi singur în recunoaștere la Mănăstire."
        ],
        "episode_progress": 0.4
    },
    
    # 2. Taverna
    "Caută informatori în Taverna 'La Lupul Șchiop'.": {
        "narrative": "Taverna e plină de fum și mercenari. Nimeni nu vorbește cu străjerii. Dar vezi un grup de străini care joacă zaruri și vorbesc în șoaptă o limbă amestecată. Unul are un tatuaj specific Dăneștilor.",
        "suggestions": [
            "Ascultă conversația (Discret).",
            "Provoacă-i la joc de zaruri.",
            "Ia-l pe unul la întrebări afară."
        ],
        "episode_progress": 0.3
    },
    "Ascultă conversația (Discret).": {
        "narrative": "Te prefaci că bei. Auzi: \"...pulberea e uscată. Mănăstirea e sigură. Mâine Târgoviște va arde.\" Ai confirmarea locației.",
        "suggestions": [
            "Ieși și raportează.",
            "Urmărește-i când pleacă."
        ],
        "episode_progress": 0.4
    },

    # 3. Căpitanul (Sceptic)
    "Du-te direct la Căpitan cu documentul.": {
        "narrative": "Căpitanul se uită la foaie. \"Ce e mâzgălitura asta? Fără o traducere sau dovezi clare, nu pot mobiliza garnizoana. Vlad Vodă ne taie capetele pentru alarme false. Adu-mi ceva concret!\"",
        "suggestions": [
            "Mergi la Grămăticul Curții (Erudit).",
            "Întoarce-te în piață să verifici carul."
        ],
        "episode_progress": 0.25
    },

    # --- RAMURA: MĂNĂSTIREA (ACTION/STEALTH) ---
    
    "Mergi singur în recunoaștere la Mănăstire.": {
        "narrative": "Ajungi la ruinele Mănăstirii la amurg. Zidurile sunt păzite de mercenari cu arbalete. Vezi butoaie cărate în curtea interioară.",
        "suggestions": [
            "Escaladează zidul din spate.",
            "Elimină santinela izolată.",
            "Crează o diversiune (Foc)."
        ],
        "episode_progress": 0.5
    },
    "Elimină santinela izolată.": {
        "narrative": "Te apropii tăcut. O lovitură precisă și cade fără sunet. Îi iei mantia pentru deghizare.",
        "suggestions": [
            "Intră deghizat în curte.",
            "Pândește de pe acoperiș."
        ],
        "items_gained": [{"name": "Mantia Mercenarului", "type": "diverse", "value": 0, "quantity": 1}],
        "episode_progress": 0.6
    },
    "Intră deghizat în curte.": {
        "narrative": "Treci printre ei. Nimeni nu te observă în întuneric. Vezi liderul Dăneștilor dând ordine lângă un stoc uriaș de arme.",
        "suggestions": [
            "Sabotează stocul de arme.",
            "Asasinează liderul (Foarte Riscant).",
            "Fugi și raportează totul."
        ],
        "episode_progress": 0.7
    },
    
    # --- RAMURA: SABOTAJ ---
    "Sabotează stocul de arme.": {
        "narrative": "Găsești butoaiele cu ulei și praf de pușcă. Le dai drumul să curgă și pregătești o torță.",
        "suggestions": [
            "Aprinde și fugi!",
            "Așteaptă momentul oportun."
        ],
        "episode_progress": 0.8
    },
    "Aprinde și fugi!": {
        "narrative": "BOOM! Explozia luminează cerul nopții. Haos total. Mercenarii fug panicați. Misiunea e îndeplinită, dar ești urmărit.",
        "suggestions": [
            "Luptă pentru scăpare.",
            "Ascunde-te în pădure."
        ],
        "episode_progress": 0.9
    },

    # --- FINALURI ---
    
    "Ascunde-te în pădure.": {
        "narrative": "Te faci nevăzut în codri. Ajungi la cetate dimineața, acoperit de funingine, dar victorios. Atacul a fost dejucat înainte să înceapă. (Sfârșit - Sabotor)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0,
        "reputation_change": 10
    },

    "Fugi și raportează totul.": {
        "narrative": "Ajungi la Căpitan cu informații complete și harta desenată. \"Excelent! Acum îi prindem ca pe șobolani.\" Conduci asaltul final al Gărzii.",
        "suggestions": ["Condu asaltul (Bătălie Finală)."],
        "episode_progress": 0.9
    },
    "Condu asaltul (Bătălie Finală).": {
        "narrative": "Porțile mănăstirii cad sub berbecii voievodali. Lupta e scurtă și brutală. Îl prinzi personal pe trădător. Onoare ție! (Sfârșit - Comandant)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "gold_change": 50,
        "episode_progress": 1.0
    },

    # --- ALTE RAMURI CONECTATE ---
    
    "Fugi la Căpitan cu traducerea.": {
        "narrative": "Cu traducerea în mână, Căpitanul nu mai ezită. \"Sună cornul! Toată garda la Mănăstire!\" Ești pus în avangardă.",
        "suggestions": ["Condu asaltul (Bătălie Finală)."],
        "episode_progress": 0.9
    },
    
    "Taie prelata să vezi încărcătura.": {
        "narrative": "Sfâșii pânza. Arme! Sute de săbii. Vizitiul te vede și fluieră. Din umbră ies trei indivizi înarmați. E o capcană!",
        "suggestions": [
            "Luptă defensiv (Rezistă până vin ajutoare).",
            "Fugi spre piață.",
            "Folosește arbaleta (Dacă o ai)."
        ],
        "episode_progress": 0.3
    },
    
    "Luptă defensiv (Rezistă până vin ajutoare).": {
        "narrative": "Te aperi cu spatele la fântână. \"Scutul Frontierei\" te ajută să parezi loviturile a trei oameni. Strigătele de luptă atrag patrula de noapte. Mercenarii fug.",
        "suggestions": [
            "Urmărește-i.",
            "Securizează carul și raportează."
        ],
        "episode_progress": 0.5
    },

    "Folosește arbaleta (Dacă o ai).": {
        "narrative": "Tragi rapid. Unul cade. Reîncarci în timp ce te retragi. Ceilalți ezită. Ai câștigat timp.",
        "suggestions": [
            "Fugi și dă alarma.",
            "Trage din nou."
        ],
        "episode_progress": 0.4
    },

    "Ieși și raportează.": {
        "narrative": "Ieși din tavernă și mergi direct la Căpitan. \"Mănăstirea Dealu, diseară.\" Căpitanul zâmbește rece. \"Le pregătim o primire caldă.\"",
        "suggestions": ["Participă la ambuscadă."],
        "episode_progress": 0.9
    },
    "Participă la ambuscadă.": {
        "narrative": "Îi așteptați la porți. Când ies, plouă cu săgeți. Victoria e totală. (Sfârșit - Tactician)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },

    # --- Missing Definitions from rewriting ---
    "Somează-l (Autoritate).": {
        "narrative": "\"Stai! Controlul Gărzii!\" Vizitiul se oprește, dar mâna îi tremură spre o bâtă. \"Nu am nimic, boierule...\"",
        "suggestions": ["Percheziționează carul.", "Percheziționează vizitiul."],
        "episode_progress": 0.15
    },
    "Observă de la distanță (Vigilență).": {
        "narrative": "Stai nemișcat. Vezi cum vizitiul ascunde un tub de pergament sub mantie și verifică obsesiv o lădiță de sub capră.",
        "suggestions": ["Fură pergamentul de la brâu.", "Atacă-l când e atent la lădiță."],
        "episode_progress": 0.15
    },
    "Percheziționează carul.": {
        "narrative": "Găsești arme ascunse sub grâu. Vizitiul încearcă să fugă!",
        "suggestions": ["Prinde-l!", "Trage cu arbaleta."],
        "episode_progress": 0.25
    },
    "Prinde-l!": {
        "narrative": "Îl plachezi în noroi. E al tău.",
        "suggestions": ["Interoghează-l dur pe loc.", "Du-l la Căpitan (Arest)."],
        "episode_progress": 0.3
    },
    "Du-l la Căpitan (Arest).": {
        "narrative": "Căpitanul îl preia. \"Vom afla totul.\" Ești lăudat, dar misterul rămâne parțial nerezolvat. (Final Mediu)",
        "suggestions": ["Rejoacă."],
        "win_condition": True,
        "episode_progress": 1.0
    },
    "Lovește-l și imobilizează-l.": {
        "narrative": "Îl lovești în moalele capului. Cade inconștient. Îi iei pergamentul.",
        "suggestions": ["Citește pergamentul."],
        "episode_progress": 0.2
    },
    "Citește pergamentul.": { # Redirect to coded logic
        "narrative": "E codificat. Vezi 'Fură pergamentul'.",
        "suggestions": ["Mergi la Grămăticul Curții (Erudit)."],
        "episode_progress": 0.25
    }
}

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(story_data, f, indent=4, ensure_ascii=False)
    print("Successfully extended Strajer Story.")
except Exception as e:
    print(f"Error: {e}")
