import streamlit as st
from models import CharacterClassType, FactionType, CharacterStats, GameMode, InventoryItem, ItemType
from typing import Dict, Any, Optional

# =========================
# — Character Data Definitions
# =========================

CHARACTER_CLASSES: Dict[CharacterClassType, Dict[str, Any]] = {
    CharacterClassType.AVENTURIER: {
        "description": "Războinic adaptabil, supraviețuitor.",
        "stats": {"strength": 1, "agility": 1, "instinct": 1},
        "special_ability": "Voință de Fier – primești un bonus minor la rezistența la intimidare și durere.",
        "icon": "⚔️"
    },
    CharacterClassType.STRAJER: {
        "description": "Gardian de margine, militar disciplinat.",
        "stats": {"constitution": 1, "perception": 1, "archery": 1},
        "special_ability": "Scutul Frontierei – primești un bonus defensiv dacă aperi un loc, obiect sau persoană.",
        "icon": "🛡️",
        "starting_items": [
            InventoryItem(name="Arbaletă de Străjer", type=ItemType.weapon, value=15, quantity=1, description="Perception +1 | Archery +1"),
            InventoryItem(name="Săgeți", type=ItemType.consumable, value=1, quantity=10)
        ]
    },
    CharacterClassType.NEGUSTOR: {
        "description": "Diplomat, comerciant și manipulator economic.",
        "stats": {"negotiation": 2, "intelligence": 1, "charisma": 1},
        "special_ability": "Prețul Corect – cumperi și vinzi orice cu profit.",
        "icon": "💰"
    },
    CharacterClassType.SPION: {
        "description": "Maestru al umbrelor, minciunii și intrigii.",
        "stats": {"agility": 1, "stealth": 2, "intelligence": 1},
        "special_ability": "Umbra Neobservată – ai șanse mari de reușită la infiltrare și evadare.",
        "icon": "🕵️"
    },
    CharacterClassType.CALATOR_RAZBOI: {
        "description": "Un fel de „specialist tactician”.",
        "stats": {"intelligence": 2, "strategy": 1, "charisma": 1},
        "special_ability": "Ochii Comandantului – identifici punctele slabe ale unui inamic sau ale unei fortificații.",
        "icon": "📜"
    },
    CharacterClassType.CALUGAR: {
        "description": "Erudit și om al bisericii.",
        "stats": {"culture": 2, "intelligence": 1, "charisma": 1}, # Charisma as 'Empatie' proxy
        "special_ability": "Vocea Cuviosului – deschizi drumuri narative pacifiste, convingi oameni greu de convins.",
        "icon": "✝️"
    },
    CharacterClassType.VANATOR: {
        "description": "Războinic al Codrilor.",
        "stats": {"agility": 1, "perception": 2, "survival": 1},
        "special_ability": "Săgețile Codrilor – bonus mare în păduri, munți și teren accidentat.",
        "icon": "🏹"
    },
    CharacterClassType.LIBER: {
        "description": "Fără jurăminte, fără stăpân.",
        "stats": {}, # 4 points to distribute manually (simplified to defaults for now or random)
        "special_ability": "Fără Jurăminte – nimeni nu te controlează, dar nimeni nu te protejează.",
        "icon": "🦅"
    }
}

AVAILABLE_CLASSES = [
    CharacterClassType.AVENTURIER,
    CharacterClassType.NEGUSTOR,
    CharacterClassType.SPION,
    CharacterClassType.STRAJER
]

FACTIONS: Dict[FactionType, Dict[str, Any]] = {
    FactionType.DRACULESTI: {
        "description": "Casa lui Vlad Țepeș. Drăculeștii descind din Mircea cel Bătrân, marele voievod al Țării Românești, și reprezintă ramura militară, dură și autoritară a Basarabilor. Numele vine de la Ordinul Dragonului, în care Vlad Dracul (tatăl lui Vlad Țepeș) a fost primit de regele Ungariei pentru promisiunea de a apăra creștinătatea. Moștenirea lor este una de disciplină, război și cruzime justițiară, iar Vlad Țepeș a dus această reputație la extrem prin pedepse exemplare, lege severă și o guvernare bazată pe ordine. Rivalitatea lor cu Dăneștii este una de sânge, legată de lupta pentru tron începută încă din vremea lui Mircea cel Bătrân și fratele său Dan.",
        "motto": "Sângele nostru este legea.",
        "location": "Târgoviște, Curtea de Argeș",
        "bonuses": "+1 Duel, +1 Disciplina, +1 Intimidare",
        "passive": "Frica de Domn – adversarii slabi se intimidează mai ușor când află cine ești.",
        "disadvantage": "Sașii și Otomanii te urăsc din start.",
        "icon": "🐉"
    },
    FactionType.DANESTI: {
        "description": "Pretendenții Umbrelor. Dăneștii sunt cealaltă ramură a Basarabilor, urmașii lui Dan I, fratele lui Mircea cel Bătrân. Între cele două ramuri, Drăculești și Dănești, a existat o rivalitate mortală timp de peste un secol, fiecare încercând să dețină tronul Țării Românești cu sprijinul diferitelor mari puteri: Ungaria, Imperiul Otoman și cu ajutorul boierilor locali. Dăneștii excelează în intrigă politică, comploturi, manipulare și alianțe secrete, fiind adesea favoriții coroanei maghiare. Sunt considerați mai puțin războinici decât Drăculeștii, dar mult mai versatili în jocurile de putere.",
        "motto": "Umbra are multe fețe.",
        "location": "Oltenia, Severin",
        "bonuses": "+2 Intrigă, +1 Furt",
        "passive": "Alianțe Nepătrunse – acces la spioni, comploturi și contacte ungurești.",
        "disadvantage": "Drăculeștii vor să te vadă mort.",
        "icon": "🦊"
    },
    FactionType.BOIERI_ARGESENI: {
        "description": "Străjerii Munților. Boierimea argeșeană provine din familii ce controlau drumurile comerciale și trecătorile Carpaților Meridionali, în special spre Brașov. Ei au fost adesea cei mai influenți la curtea de la Curtea de Argeș, capitala veche a Țării Românești. Conducători de oști locale, străjeri și cunoscători ai muntelui, acești boieri sunt recunoscuți pentru loialitate fluctuantă, fiind adesea responsabili pentru ridicări sau căderi ale domnilor în funcție de interesele lor.",
        "motto": "Pădurile ne ascund, munții ne apără.",
        "location": "Argeș, Muscel",
        "bonuses": "+1 Supraviețuire, +1 Tir, +1 Ambuscadă",
        "passive": "Trecători Secrete – poți traversa munții fără penalități.",
        "disadvantage": "Faima de boieri indeciși – primești neîncredere în marile curți.",
        "icon": "⛰️"
    },
    FactionType.SASI: {
        "description": "Breslele din Brașov/Sibiu. Sașii transilvăneni sunt un popor germanic colonizat în Evul Mediu, renumiți pentru meșteșug, comerț, urbanizare și tehnologie militară vestică. Orașele lor — Brașov și Sibiu — au fost centre economice vitale pentru Țara Românească. Relația lor cu Vlad Țepeș a fost tensionată, mai ales din cauza taxelor și interdicțiilor comerciale impuse de acesta. Sașii au ținut și tipărit primele izvoare istorice europene despre Vlad, contribuind la transformarea sa în legendă.",
        "motto": "Prin negustorie, noi stăpânim lumea.",
        "location": "Brașov, Sibiu",
        "bonuses": "+2 Negociere, +1 Inginerie",
        "passive": "Bresle Puternice – prețuri comerciale mai bune, acces la arme vestice.",
        "disadvantage": "Vlad Țepeș te poate persecuta în campanie.",
        "icon": "🔨"
    },
    FactionType.OTOMANI: {
        "description": "Cercul Semilunii. Reprezintă puterea dominantă a secolului XV în Balcani. După cucerirea Constantinopolului din anul 1453, Imperiul Otoman, a devenit un colos militar și politic. În Țara Românească aveau pretendenți, trupe, spioni și drept de tribut. Războaiele lui Vlad Țepeș cu otomanii, în special noaptea atacului de la Târgoviște din 1462, sunt parte centrală a istoriei regiunii. Otomanii se bazează pe disciplină, cavalerie rapidă, armament modern și logistică impecabilă.",
        "motto": "Sultanul vede tot.",
        "location": "Nicopole, Giurgiu, Rusciuk",
        "bonuses": "+1 Disciplina Militară, +1 Cavalerie, +1 Tactică",
        "passive": "Cadea Ravager – moral crescut în lupte ofensive.",
        "disadvantage": "Românii și sașii nu te vor în orașele lor.",
        "icon": "🌙"
    },
    FactionType.BOIERI_NOI: {
        "description": "Gărzile Nocturne ale lui Vlad. Aceștia sunt boieri ridicați de Vlad Țepeș din rândul armatei sau micii nobilimi, înlocuindu-i pe vechii boieri considerați trădători. Loiali doar lui Vlad, au format nucleul Gărzii Nocturne, un corp de elită cunoscut pentru execuții rapide, tortură judiciară și disciplină extremă. Urâți de boierimea veche, dar temuti în întreaga țară, acești oameni au asigurat stabilitatea domniei lui Vlad Țepeș.",
        "motto": "Jurăm pe sânge!",
        "location": "Poenari, București, Târgoviște",
        "bonuses": "+2 Loialitate, +1 Duel",
        "passive": "Sabia Dreaptă – primești bonus la execuții, interogatorii, ordine.",
        "disadvantage": "Ura generală a boierimii vechi.",
        "icon": "🗡️"
    },
    FactionType.BOIERI_MOLDOVENI: {
        "description": "Marile familii din Nord. Familiile boierești din Moldova (Movilești, Arbore, Șoldan, alții) sunt recunoscute pentru cavalerie ușoară rapidă, diplomație flexibilă și relații extinse cu Polonia și Lituania. Deși nu sunt parte directă a conflictului Drăculești–Dănești, influența lor de la nord putea decide echilibrele politice. Au tradiție în apărarea frontierelor Carpaților Orientali.",
        "motto": "Cine ține Moldova, ține trecătorile lumii.",
        "location": "Suceava, Vaslui, Roman",
        "bonuses": "+1 Cavalerie Ușoară, +1 Diplomație, +1 Supraviețuire",
        "passive": "Hotarul Neîmblânzit – te miști rapid în Moldova, Polonia și nordul Carpaților.",
        "disadvantage": "Relații instabile între familii.",
        "icon": "🐂"
    },
    FactionType.CRAIOVESTI: {
        "description": "Vulturii Olteniei. Craioveștii au fost cea mai puternică familie boierească a Olteniei. În vremea lui Vlad Țepeș încă nu-și atinseseră apogeul, dar influența lor creștea periculos. Spre deosebire de boierii argeșeni, erau războinici, duri și mândri, cu tradiție în cavaleria grea. Loialitatea lor oscila între Drăculești și Dănești după interes.",
        "motto": "Oltenii nu se supun decât puterii adevărate.",
        "location": "Craiova, Jiu, Amaradia",
        "bonuses": "+1 Forță, +1 Cavalerie, +1 Reputație Locală",
        "passive": "Adunarea de la Jiu – poți ridica în joc miliții oltenești.",
        "disadvantage": "Neîncredere din partea Țării de Sus și a Drăculeștilor.",
        "icon": "🦅"
    },
    FactionType.SECUI: {
        "description": "Săgețile Carpaților. Populație militarizată aflată la marginea Transilvaniei, secuii au servit adesea în expediții anti-otomane. Sunt excelenți arcași și războinici ai terenului montan. În timpul lui Vlad, unii secui l-au însoțit în raiduri sau l-au sprijinit după evadarea din Ungaria.",
        "motto": "Viteza este scutul nostru.",
        "location": "Scaunele secuiești (Odorhei, Ciuc, Covasna)",
        "bonuses": "+2 Tir, +1 Mobilitate",
        "passive": "Fulger Montan – primești primul atac în teren montan.",
        "disadvantage": "Slabi la negociere, antisociali.",
        "icon": "🏹"
    },
    FactionType.ROMANI_TRANSILVANENI: {
        "description": "Fiii Pădurilor Negre. Clasa românească din Transilvania se bazează pe păstorit, vânătoare și supraviețuire în munți. În epoca Țepeș, mulți dintre ei oferă sprijin clandestin voievodului sau devin călăuze în raidurile împotriva sașilor și a nobililor ostili. Sunt războinici ai pădurilor și ai muntelui.",
        "motto": "Sub coroana munților, totul respiră liber.",
        "location": "Făgăraș, Hațeg, Țara Bârsei rurală",
        "bonuses": "+1 Supraviețuire, +1 Ambuscadă, +1 Cunoaștere Carpatină",
        "passive": "Zid Verde – pădurile îți oferă protecție uriașă.",
        "disadvantage": "Valoare politică scăzută.",
        "icon": "🌲"
    },
    FactionType.DOBROGENI: {
        "description": "Păzitorii Vadurilor. Dobrogea este în perioada Țepeș disputată între otomani și Țara Românească. Localnicii, obișnuiți cu navigația pe Dunăre, au rol crucial în recunoașteri, raiduri pe apă și contracararea incursiunilor otomane. Oameni duri, obișnuiți cu frontiera.",
        "motto": "Dunărea nu iartă pe cei fără pricepere.",
        "location": "Isaccea, Dobrogea centrală",
        "bonuses": "+2 Navigație Fluvială, +1 Viteză pe apă",
        "passive": "Cârma Dunării – reduci penalități la evenimente pe râu.",
        "disadvantage": "Slabi pe teren montan.",
        "icon": "🌊"
    },
    FactionType.MARGINIMEA: {
        "description": "Grăniceri ai Negurii. Marginimea Sibiului este o sursă de oameni rezistenți, ciobani războinici și călăuze montane. În vremea lui Vlad, au ajutat adesea la trecerile secrete dintre Transilvania și Țara Românească, uneori contra cost, alteori după interese locale.",
        "motto": "Munții ne cresc, noi îi apărăm.",
        "location": "Săliște, Orlat, Rășinari",
        "bonuses": "+1 Percepție, +1 Tir, +1 Mobilitate",
        "passive": "Calea Oierilor – te miști foarte repede prin trecători.",
        "disadvantage": "Relații politice modeste.",
        "icon": "🐑"
    },
    FactionType.MERCENARI: {
        "description": "Sulițele Sudului. Războinicii balcanici (sârbi, bulgari, albanezi) sunt omniprezenți în conflictele dintre Vlad, turci și unguri. Fără loialități, dar cu experiență enormă în luptele din Balcani, aceștia au servit în atacuri rapide și misiuni riscante. Vlad i-a folosit inclusiv ca forțe auxiliare în campanii nocturne.",
        "motto": "Aurul nu are stăpân.",
        "location": "Serbia, Bulgaria, Albania",
        "bonuses": "+1 Lupi de Război, +1 Forță, +1 Intimidare",
        "passive": "Aur și Sânge – pot lupta pentru oricine, inclusiv dușmani.",
        "disadvantage": "Moral instabil.",
        "icon": "⚔️"
    },
    FactionType.NOBILI_TRANSILVANENI: {
        "description": "Cavaleri ai Coroanei Ungurești. Elita militară a Ungariei, instrument al regelui Matia Corvin. Sunt bine înarmați, organizați în cavalerie grea și sprijină adesea Dăneștii împotriva lui Vlad. După arestarea lui Țepeș, unii nobili îl supraveghează în castelul Visegrád. Reprezintă puterea instituțională a regatului.",
        "motto": "Lege și sabie.",
        "location": "Alba Iulia, Hunedoara, Cluj",
        "bonuses": "+2 Cavalerie Greasă, +1 Armură",
        "passive": "Pavăza Occidentului – armurile vestice reduc mult daunele.",
        "disadvantage": "Dușmănie cu Drăculeștii.",
        "icon": "🏰"
    },
    FactionType.LIBER: {
        "description": "Fără apartenență politică. Aventurieri, negustori, haiduci, călători sau simpli oameni ai vremii. În epoca lui Vlad, libertatea este rară și periculoasă. Fără o familie mare în spate, dar cu abilitatea de a intra oriunde, de a negocia și de a evita conflictele politice majore.",
        "motto": "Fără jurăminte, fără stăpâni.",
        "location": "Oriunde",
        "bonuses": "Niciunul",
        "passive": "Neutru – Nu ai dușmani impliciți, dar nici aliați.",
        "disadvantage": "Lipsa protecției.",
        "icon": "🕊️"
    }
}

AVAILABLE_FACTIONS = [
    FactionType.DRACULESTI
]

# =========================
# — Logic & UI
# =========================

def apply_character_class_stats(game_state, class_type: CharacterClassType):
    """Applies base stats, abilities, and items from the selected class"""
    data = CHARACTER_CLASSES[class_type]
    character = game_state.character
    
    # Apply stats
    for stat, value in data["stats"].items():
        current_val = getattr(character, stat, 0)
        setattr(character, stat, current_val + value)
    
    # Set abilities
    character.special_ability = data["special_ability"]
    character.character_class = class_type

    # Apply starting items
    if "starting_items" in data:
        for item in data["starting_items"]:
            # Check if exists (to avoid duplicates if re-run, though re-run resets char usually)
            if not any(i.name == item.name for i in game_state.inventory):
                game_state.inventory.append(item)

def apply_faction_modifiers(character: CharacterStats, faction_type: FactionType):
    """Applies faction bonuses (mostly narrative/passive stored in description for now)"""
    data = FACTIONS[faction_type]
    character.passive_ability = data["passive"]
    character.faction = faction_type
    
    # Note: Faction bonuses are often qualitative or apply to stats not yet strictly tracked
    # We store the choice, and the LLM will interpret the 'passive_ability' and faction name.

def set_game_mode(game_state, mode: GameMode):
    """Sets the game mode and initializes campaign if needed"""
    # Store in character stats for DB persistence without schema changes
    game_state.character.game_mode = mode
    if mode == GameMode.CAMPAIGN:
        game_state.character.current_episode = 1
    else:
        game_state.character.current_episode = 0

def render_character_creation(game_state, db=None, user_id=None, db_session_id=None, loading_placeholder=None) -> bool:
    """
    Renders the character creation wizard.
    Returns True if character creation is complete, False if still in progress.
    Handles loading screen clearing intelligently to avoid flickers.
    """
    # Add JavaScript for smooth polling to reduce flickering on button clicks
    st.markdown("""
    <script>
    let charUpdateInterval;

    function updateCharacterCreation() {
        // Make a request to get updated character creation data
        fetch(window.location.href, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'update_char_creation': 'true'
            })
        })
        .then(response => response.text())
        .then(html => {
            // Extract and update only the character creation section
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            // Look for the main content area (adjust selector as needed)
            const newCharSection = doc.querySelector('div[data-testid="stVerticalBlock"]');

            if (newCharSection) {
                // Find current character creation section
                const currentCharSection = document.querySelector('div[data-testid="stVerticalBlock"]');
                if (currentCharSection) {
                    // Smooth fade transition
                    currentCharSection.style.transition = 'opacity 0.3s ease';
                    currentCharSection.style.opacity = '0';

                    setTimeout(() => {
                        currentCharSection.innerHTML = newCharSection.innerHTML;
                        currentCharSection.style.opacity = '1';
                    }, 300);
                }
            }
        })
        .catch(error => {
            console.log('Character creation update failed:', error);
        });
    }

    function startCharPolling() {
        // Update every 2 seconds for responsive UI
        charUpdateInterval = setInterval(updateCharacterCreation, 2000);
    }

    function stopCharPolling() {
        if (charUpdateInterval) {
            clearInterval(charUpdateInterval);
        }
    }

    // Start polling when page loads
    window.addEventListener('load', startCharPolling);

    // Clean up on page unload
    window.addEventListener('beforeunload', stopCharPolling);
    </script>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        .char-card {
            background-color: #1E1E1E;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #333;
            margin-bottom: 15px;
            transition: transform 0.2s;
            height: 100%;
            min-height: 320px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .char-card:hover {
            border-color: #D4AF37;
            transform: scale(1.01);
            background-color: #252525;
        }
        .faction-desc {
            font-size: 0.95rem;
            line-height: 1.5;
            color: #dcdcdc;
            text-align: justify;
            margin: 10px 0;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
            border-left: 2px solid #5a3921;
        }
        .stat-badge {
            background-color: #333;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-right: 5px;
        }
        h3 {
            color: #D4AF37 !important;
            margin-bottom: 10px;
        }
        /* Fade out disabled cards */
        .char-card-disabled {
            opacity: 0.5;
            filter: grayscale(0.8);
            cursor: not-allowed;
        }
        </style>
    """, unsafe_allow_html=True)

    # 1. GAME MODE SELECTION (Now FIRST)
    if game_state.character.game_mode is None:
        if loading_placeholder:
            loading_placeholder.empty()

        st.markdown("<h1 style='text-align: center; color: #D4AF37;'>🗺️ Alege Calea</h1>", unsafe_allow_html=True)
        
        # CAMPAIGN (Primary Option)
        st.markdown("""
        <div class="char-card" style="text-align: center; border: 2px solid #8a0303; background: linear-gradient(145deg, #1a0505, #0a0202); margin-bottom: 30px; min-height: auto;">
            <h1 style="font-size: 4rem;">🐉</h1>
            <h2 style="color: #ff4d4d !important;">CAMPANIE: PECETEA DRĂCULEȘTILOR</h2>
            <p style="font-size: 1.1rem;">O poveste epică în 8 episoade: Recuperează relicva sacră a Drăculeștilor.</p>
            <p><i>Conține puzzle-uri, bătălii istorice, personaje reale și finaluri multiple.</i></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show Episode List Preview if user is interested? 
        # Or just let them click Start.
        
        if st.button("🔥 Începe Campania (Recomandat)", key="btn_mode_campaign", use_container_width=True, type="primary"):
            set_game_mode(game_state, GameMode.CAMPAIGN)
            
            # Setup Campaign Intro (Episode 1)
            from campaign import CAMPAIGN_EPISODES
            ep1 = CAMPAIGN_EPISODES[1]
            
            if len(game_state.story) > 0:
                # Remove flavor text entirely for Campaign start, replace with Episode 1 Card
                # We keep the first message structure but clear text and set type
                game_state.story[0] = {
                    "role": "ai",
                    "text": "", # Content handled by type
                    "turn": 0,
                    "image": None,
                    "type": "episode_intro",
                    "content_data": ep1,
                    "suggestions": ep1.get("initial_suggestions", [])
                }

            # Mark to show structure screen next
            st.session_state.show_campaign_structure = True

            new_sid = None
            if db and user_id:
                new_sid = db.save_game_state(user_id, game_state, db_session_id)
            if new_sid:
                st.session_state.db_session_id = new_sid
            st.rerun()

        st.markdown("---")

        # FREE WORLD (Secondary Option)
        st.markdown("""
        <div class="char-card" style="text-align: center; opacity: 0.9; min-height: auto;">
            <h1>🌍</h1>
            <h3>Lume Liberă</h3>
            <p>O experiență sandbox. Călătorește liber prin Valahia, interacționează cu lumea și fă-ți propriul destin.</p>
            <p><i>Textul de început se va adapta alegerilor tale.</i></p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Începe Lume Liberă", key="btn_mode_free", use_container_width=True):
            set_game_mode(game_state, GameMode.FREE_WORLD)
            
            # ATTEMPT PERSISTENCE: Load inventory from last campaign if available
            if db and user_id:
                try:
                    campaign_inv = db.get_last_campaign_inventory(user_id)
                    if campaign_inv:
                        game_state.inventory = campaign_inv
                        st.toast("🎒 Inventar din campanie recuperat!", icon="📦")
                except Exception as e:
                    print(f"Inventory carry-over failed: {e}")

            # Setup custom intro text for Free World based on choices
            # Note: Class/Faction not chosen yet, so we just set a placeholder or generic intro that will be updated later?
            # Actually, if we reorder flow, we select Mode FIRST. So we don't know Class/Faction yet.
            # We will update the intro text AFTER Faction selection for Free World.
            
            new_sid = None
            if db and user_id:
                new_sid = db.save_game_state(user_id, game_state, db_session_id)
            if new_sid:
                st.session_state.db_session_id = new_sid
            st.rerun()

        return False

    # 1.5 CAMPAIGN STRUCTURE SCREEN
    elif st.session_state.get('show_campaign_structure', False) and game_state.character.game_mode == GameMode.CAMPAIGN:
        if loading_placeholder:
            loading_placeholder.empty()

        st.markdown("<h1 style='text-align: center; color: #D4AF37;'>📜 Structura Campaniei</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8b6b6b;'>Călătoria ta va fi lungă și plină de pericole. Iată ce te așteaptă.</p>", unsafe_allow_html=True)
        
        from campaign import CAMPAIGN_EPISODES
        
        current_ep_num = game_state.character.current_episode
        if current_ep_num == 0: current_ep_num = 1

        # Display episodes in a list with buttons
        for i in range(1, 9):
            ep = CAMPAIGN_EPISODES.get(i)
            if ep:
                # Determine state
                is_completed = i < current_ep_num
                is_current = i == current_ep_num
                is_locked = i > current_ep_num

                # Styling based on state
                border_color = "#D4AF37" if is_current else "#5a3921" if is_completed else "#333"
                bg_color = "rgba(212, 175, 55, 0.1)" if is_current else "rgba(0,0,0,0.3)"
                opacity = "1.0" if is_current else "0.7" if is_completed else "0.4"
                
                col_text, col_btn = st.columns([3, 1])
                
                with col_text:
                    st.markdown(f"""
                    <div style="
                        background-color: {bg_color}; 
                        border-left: 4px solid {border_color}; 
                        padding: 15px; 
                        margin-bottom: 10px;
                        border-radius: 0 8px 8px 0;
                        opacity: {opacity};
                    ">
                        <h4 style="color: {border_color}; margin: 0;">Episodul {i}: {ep['title']}</h4>
                        <p style="color: #ccc; margin: 5px 0 0 0; font-style: italic;">{ep.get('mystery_desc', 'Detalii învăluite în mister...')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_btn:
                    # Vertical alignment spacer
                    st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
                    
                    if is_current:
                        if st.button("⚔️ Intră", key=f"ep_enter_{i}", type="primary", use_container_width=True):
                            st.session_state.show_campaign_structure = False
                            st.rerun()
                    elif is_completed:
                        st.button("✅ Complet", key=f"ep_done_{i}", disabled=True, use_container_width=True)
                    else:
                        st.button("🔒 Blocat", key=f"ep_lock_{i}", disabled=True, use_container_width=True)

        st.markdown("---")
        # Removed generic "Continue" button as we now have specific enter buttons
            
        return False

    # 2. CHARACTER CLASS SELECTION
    elif game_state.character.character_class is None:
        if loading_placeholder:
            loading_placeholder.empty()
            
        st.markdown("<h1 style='text-align: center; color: #D4AF37;'>⚔️ Alege Destinul Eroului Tău</h1>", unsafe_allow_html=True)
        st.info("Tipul de caracter îți definește stilul de joc și abilitățile de bază.")
        
        # Sort classes: Available first
        sorted_classes = sorted(CHARACTER_CLASSES.items(), key=lambda x: x[0] not in AVAILABLE_CLASSES)

        cols = st.columns(2)
        for idx, (cls_type, data) in enumerate(sorted_classes):
            is_available = cls_type in AVAILABLE_CLASSES
            
            with cols[idx % 2]:
                with st.container():
                    # Styling
                    card_class = "char-card" if is_available else "char-card char-card-disabled"
                    badge = "" if is_available else "<br><b>🚫 ÎN CURÂND</b>"

                    st.markdown(f"""
                        <div class="{card_class}">
                            <h3>{data['icon']} {cls_type.value} {badge}</h3>
                            <p><i>{data['description']}</i></p>
                            <p><b>Abilitate Specială:</b> {data['special_ability']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Stats display
                    stats_str = " | ".join([f"{k.capitalize()}: +{v}" for k,v in data['stats'].items()])
                    st.caption(f"📊 {stats_str}")
                    
                    if st.button(f"Alege {cls_type.value}", key=f"btn_cls_{idx}", use_container_width=True, disabled=not is_available):
                        apply_character_class_stats(game_state, cls_type)

                        # If Free World, maybe update intro text partially? No wait until Faction.

                        new_sid = None
                        if db and user_id:
                            new_sid = db.save_game_state(user_id, game_state, db_session_id)

                        if new_sid:
                            st.session_state.db_session_id = new_sid
                        st.rerun()
        return False

    # 3. FACTION SELECTION
    elif game_state.character.faction is None:
        if loading_placeholder:
            loading_placeholder.empty()

        st.markdown("<h1 style='text-align: center; color: #D4AF37;'>🚩 Alege Loialitatea</h1>", unsafe_allow_html=True)
        st.info("Facțiunea îți oferă aliați, dușmani și oportunități unice în poveste.")

        # Sort factions: Available first
        sorted_factions = sorted(FACTIONS.items(), key=lambda x: x[0] not in AVAILABLE_FACTIONS)

        # Render List of Factions
        for idx, (fac_type, data) in enumerate(sorted_factions):
            is_available = fac_type in AVAILABLE_FACTIONS
            card_class = "char-card" if is_available else "char-card char-card-disabled"
            coming_soon_badge = "" if is_available else "<br><b>🚫 ÎN CURÂND</b>"
            
            # Define HTML without indentation to avoid markdown code block interpretation
            card_html = f"""<div class="{card_class}" style="margin-bottom: 30px; min-height: auto; padding: 25px;">
<h2 style="margin: 0 0 10px 0; color: #D4AF37 !important; text-align: center; font-size: 1.8rem;">
{data['icon']} {fac_type.value} {coming_soon_badge}
</h2>
<div style="font-family: 'Cinzel', serif; font-style: italic; color: #f0e68c; font-size: 1.2rem; margin-bottom: 15px; text-align: center; border-bottom: 1px solid #333; padding-bottom: 10px;">
<strong>DEVIZĂ:</strong> "{data.get('motto', '')}"
</div>
<div style="text-align: center; margin-bottom: 15px; color: #aaa; font-size: 1rem;">
📍 <b>Centru Putere:</b> {data.get('location', '')}
</div>
<div class="faction-desc" style="font-size: 1.05rem; margin-bottom: 20px;">
{data['description']}
</div>
<div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #333; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
<p style="margin: 5px 0; font-size: 1rem;">✅ <b>Bonusuri:</b> <span style="color: #90ee90;">{data['bonuses']}</span></p>
<p style="margin: 5px 0; font-size: 1rem;">✨ <b>Pasivă:</b> <span style="color: #ffd700;">{data['passive']}</span></p>
<p style="margin: 5px 0; font-size: 1rem;">⚠️ <b>Dezavantaj:</b> <span style="color: #ff6b6b;">{data['disadvantage']}</span></p>
</div>
</div>"""
            
            st.markdown(card_html, unsafe_allow_html=True)
            
            if st.button(f"🛡️ Mă alătur: {fac_type.value.upper()}", key=f"btn_fac_{idx}", type="primary", use_container_width=True, disabled=not is_available):
                apply_faction_modifiers(game_state.character, fac_type)
                
                # FINAL STEP: Update Intro Text if Free World
                if game_state.character.game_mode == GameMode.FREE_WORLD:
                        intro_text = f"Ești un **{game_state.character.character_class.value}** loial facțiunii **{game_state.character.faction.value}**.\n\n"
                        intro_text += f"Ai pornit la drum cu abilitatea ta de bază: *{game_state.character.special_ability}*.\n"
                        intro_text += "Valahia se întinde în fața ta, plină de pericole și oportunități. Încotro te îndrepți?"
                        
                        # We update the story text only if it hasn't advanced
                        if len(game_state.story) > 0 and "Ce vrei să faci?" in game_state.story[0]['text']:
                            # Or overwrite generic intro
                            # Let's keep it simple and just set it
                            game_state.story[0]['text'] = intro_text

                # CRITICAL: Save state to DB immediately
                new_sid = None
                if db and user_id:
                    new_sid = db.save_game_state(user_id, game_state, db_session_id)
                
                if new_sid:
                    st.session_state.db_session_id = new_sid
                st.rerun()
            
            st.markdown("---")
        return False

    else:
        # Done! DO NOT clear loading placeholder here. Let app.py do it when rendering main UI.
        return True
