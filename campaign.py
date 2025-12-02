from typing import Dict, Any, List

# =========================
# — Campaign Definition: "Pecetea Drăculeștilor"
# =========================

CAMPAIGN_EPISODES = {
    1: {
        "title": "Umbra Carului Negru",
        "location": "Târgoviște – Curtea Domnească",
        "description": "Într-o dimineață de iarnă, un car negru cu însemne arse intră în târg. Încărcătura? Un document furat din vistieria domnească: un fragment din sigiliu.",
        "mystery_desc": "O dimineață rece în Târgoviște. O încărcătură misterioasă sosește în cetate, purtând secrete ce pot zdruncina tronul.",
        "objectives": [
            "Observă carul negru fără a fi detectat.",
            "Recuperează indiciul din car.",
            "Găsește ștampila boierului dăneștean."
        ],
        "key_npcs": ["Ilie Neguț (Negustor)"],
        "reward": "Scrisoare sigilată cu semnul Dăneștilor",
        "hints": ["Caută în piață, ascultă zvonurile.", "Urmărește urmele de noroi."],
        "initial_suggestions": ["Merg în piață să ascult zvonurile.", "Mă apropii discret de carul negru.", "Caut un loc înalt pentru a observa."]
    },
    2: {
        "title": "Răspântia Trădărilor",
        "location": "Hanul Argeșean (Drumul Câmpulung)",
        "description": "La un han izolat se întâlnesc spioni, călători, agenți ai sașilor și ai otomanilor. Radu cel Frumos își țese pânza.",
        "mystery_desc": "Un han izolat, unde șoaptele sunt mai ascuțite decât pumnalele. Cineva te privește din umbră.",
        "objectives": [
            "Rezolvă ghicitoarea medievală pentru a intra în cercul conspiratorilor.",
            "Identifică agentul otoman.",
            "Recrutează menestrelul brașovean."
        ],
        "key_npcs": ["Menestrel Brașovean", "Agent Otoman"],
        "reward": "Informații despre Radu cel Frumos",
        "hints": ["Discută cu hangurul.", "Fii atent la accentele străine."],
        "initial_suggestions": ["Intru în han și comand o băutură.", "Mă așez la o masă retrasă.", "Ascult discuțiile de la masa vecină."]
    },
    3: {
        "title": "Drumul Contrabandiștilor",
        "location": "Munții Muscelului",
        "description": "Pe potecile ascunse dintre Valahia și Transilvania, brașovenii aduc arme și sare. Un boier dăneștean finanțează totul.",
        "mystery_desc": "Poteci ascunse în munți, unde legea domnească nu ajunge. O alianță periculoasă se formează la graniță.",
        "objectives": [
            "Infiltrează-te în transportul ilegal.",
            "Descoperă cine finanțează contrabanda.",
            "Supraviețuiește ambuscadei hoților de codru."
        ],
        "key_npcs": ["Căpitanul Contrabandiștilor"],
        "reward": "Condica de comerț (Dovadă)",
        "hints": ["Nu te abate de la potecă.", "Ascultă sunetul pădurii."],
        "initial_suggestions": ["Caut urme de căruță pe potecă.", "Mă ascund în tufișuri și aștept.", "Cercetez luminișul din apropiere."]
    },
    4: {
        "title": "Judecata Lemnului",
        "location": "Bârsești (Vâlcea)",
        "description": "În zona Vâlcea, tradițiile vechi dăinuie. Baba Dochia poate descifra fragmentele sigiliului, dar cere o jertfă de spirit.",
        "mystery_desc": "Vechi credințe și ritualuri uitate. O bătrână înțeleaptă deține cheia, dar prețul cunoașterii este mare.",
        "objectives": [
            "Găsește-o pe Baba Dochia.",
            "Rezolvă puzzle-ul (simboluri dacice).",
            "Obține traducerea fragmentului."
        ],
        "key_npcs": ["Baba Dochia"],
        "reward": "Fragment descifrat",
        "hints": ["Respectă tradițiile locale.", "Caută semnele sculptate în lemn."],
        "initial_suggestions": ["O caut pe Baba Dochia în sat.", "Examinez stâlpii sculptați de la intrare.", "Întreb sătenii despre ritualuri."]
    },
    5: {
        "title": "Seara în care trebuia să mori",
        "location": "Tabăra Oștirii Domnești",
        "description": "Vlad pregătește Atacul de Noapte. În tabără, trădarea fierbe. Un asasin îl pândește pe un căpitan loial.",
        "mystery_desc": "În inima armatei, loialitatea este testată. Un cuțit sclipește în lumina focului de tabără.",
        "objectives": [
            "Identifică trădătorii din tabără.",
            "Previno asasinatul.",
            "Participă la consiliul de război."
        ],
        "key_npcs": ["Căpitan Loial", "Asasin Infiltrat"],
        "reward": "Încrederea Oștirii",
        "hints": ["Fii atent la cine lipsește de la apel.", "Verifică armele soldaților."],
        "initial_suggestions": ["Patrulez prin tabără.", "Verific corturile căpitanilor.", "Discut cu soldații de gardă."]
    },
    6: {
        "title": "Fântâna de Sare și Sânge",
        "location": "Cetatea Poenari",
        "description": "Refăcută cu munca silnică a boierilor, cetatea ascunde tuneluri și secrete. Un paznic răzvrătit păzește cel mai mare fragment.",
        "mystery_desc": "Ziduri ridicate cu suferință. Tunelurile de dedesubt ascund ceva ce nu ar trebui să vadă lumina zilei.",
        "objectives": [
            "Pătrunde în tunelurile de sub cetate.",
            "Confruntă paznicul răzvrătit.",
            "Recuperează fragmentul principal."
        ],
        "key_npcs": ["Paznic Răzvrătit"],
        "reward": "Fragmentul Principal al Pecetei",
        "hints": ["Nu intra neînarmat în tuneluri.", "Ferește-te de capcane vechi."],
        "initial_suggestions": ["Aprind o torță și intru în tunel.", "Caut intrarea secretă.", "Examinez zidurile cetății."]
    },
    7: {
        "title": "Adevărul de dincolo de masă",
        "location": "Curtea Domnească",
        "description": "Diplomație pură. Boieri, soli otomani și unguri. Trebuie să prezinți dovezile fără a declanșa un război civil prematur.",
        "mystery_desc": "Cuvintele pot fi mai letale decât săbiile. O singură greșeală poate arunca țara în haos.",
        "objectives": [
            "Folosește Condica și Scrisorile ca dovezi.",
            "Convinge solii lui Matia Corvin.",
            "Demască boierul trădător."
        ],
        "key_npcs": ["Solul Maghiar", "Boierul Trădător"],
        "reward": "Susținere Politică",
        "hints": ["Fii diplomat cu solii.", "Nu acuza fără dovezi clare."],
        "initial_suggestions": ["Prezint dovezile în fața tuturor.", "Vorbesc privat cu Solul Maghiar.", "Îl provoc pe boierul trădător."]
    },
    8: {
        "title": "Iarna Pecetei",
        "location": "Sala Tronului",
        "description": "Finalul. În fața lui Vlad Țepeș, recompui sigiliul. Soarta Valahiei și a trădătorului stă în mâinile tale.",
        "mystery_desc": "Momentul adevărului. În fața Domnitorului, destinul se scrie cu sânge și cerneală.",
        "objectives": [
            "Recompune Pecetea.",
            "Decide soarta trădătorului (Moarte/Exil/Iertare).",
            "Alege-ți propriul destin."
        ],
        "key_npcs": ["Vlad Țepeș"],
        "reward": "FINAL JOC",
        "hints": ["Ascultă-ți instinctul.", "Soarta Valahiei este în mâinile tale."],
        "initial_suggestions": ["Îi prezint Pecetea lui Vlad.", "Cer judecata domnească.", "Îngenunchez în fața Voievodului."]
    }
}

def get_current_episode(turn: int) -> Dict[str, Any]:
    """Returns the episode data for the current turn"""
    for ep_num, data in CAMPAIGN_EPISODES.items():
        start, end = data["turn_range"]
        if start <= turn <= end:
            data["episode_number"] = ep_num
            return data
    
    # If turn > 100 or undefined, return Epilogue or End
    if turn > 100:
        return {
            "episode_number": 9,
            "title": "Epilog",
            "location": "Valahia",
            "description": "Povestea s-a încheiat. Legenda ta dăinuie.",
            "objectives": [],
            "reward": None
        }
    
    return CAMPAIGN_EPISODES[1] # Default to Ep 1
