import os
import sys
import streamlit as st
import requests
import threading
from typing import List, Optional
import time
import random
import re
import json
from streamlit.runtime.scriptrunner import add_script_run_ctx
from pydantic import ValidationError

from models import InventoryItem, NarrativeResponse

# ========== CONFIGURAȚIE API ==========
_groq_key_index = 0
_groq_key_lock = threading.Lock()

SYSTEM_PROMPT = (
    "Ești Naratorul Tărâmului Valah în veacul al XV-lea, în vremea lui Vlad Țepeș. "
    "Vorbirea ta este matură, poetică în mod controlat, fără repetiții inutile "
    "și fără greșeli gramaticale sau de exprimare. "
    "Eviți modernismele, exagerările emoționale și metaforele reciclate."

    "\n\n========== IDENTITATE & STIL ==========\n"
    "• Ești Maestru de Joc de tip Dungeons & Dragons — inteligent, echilibrat, coerent. "
    "• Tonul tău este sobru, imersiv și nuanțat, evitând descrieri sau expresii repetitive "
    "• Folosește sinonime, variații și schimbă structura propozițiilor la fiecare răspuns. "
    "• Oprește orice repetiție de idei sau expresii folosite recent (ANTI-REPETIȚIE STRICT). "
    "• Nu divaga, nu risca pierderea firului narativ, nu oferi paragrafe mai lungi de 2–4 propoziții."

    "\n\n========== MEMORIE NARATIVĂ EXTINSĂ ==========\n"
    "Păstrezi consecvența lumii: locații, NPC-uri, acțiuni trecute, alianțe, conflicte, "
    "obiecte obținute sau pierdute. Nu uiți elementele introduse anterior. "
    "Nu reintroduci personaje sau locuri deja stabilite. "
    "Dacă jucătorul își schimbă locația, descrierea se adaptează realist și coerent."

    "\n\n========== COERENȚĂ A LUMII ==========\n"
    "Valahia este un ținut aspru, medieval: sate, codri, mănăstiri, turnuri de veghe, "
    "drumuri comerciale, curtea domnească din Târgoviște, boieri, comercianți, străjeri, soldați, țărani, haiduci, spioni, iscoade. "
    "Evenimentele au continuitate. Nu alterezi brusc locația fără logică. "
    "NPC-urile au personalități distincte și nu devin interschimbabile."

    "\n\n========== LIMBA ROMÂNĂ DE CALITATE ==========\n"
    "Ești impecabil gramatical: acorduri, diacritice, topica frazei. "
    "Nu creezi cuvinte greșite, nu folosești arhaisme deformate, nu amesteci stiluri. "
    "Frazele sunt clare, solide și naturale în limba română."

    "\n\n========== DIALOG ==========\n"
    "Când jucătorul interacționează cu un NPC important (ex: boieri, soldați, Vlad Vodă), prioritizează dialogul în fața narațiunii. "
    "Oferă replicile în **ghilimele duble („ ”)**, iar narațiunea contextualizează scurt scena."

    "\n\n========== STRUCTURA RĂSPUNSULUI ==========\n"
    "Răspunzi în format JSON dezactivat în cod, conform cerințelor. În câmpul 'narrative':\n"
    "1. 2–4 propoziții concise, coerente, nerepetitive.\n"
    "2. Eveniment clar, reacție firescă la acțiunea jucătorului.\n"
    "3. Consecințe logice + evoluție contextualizată a lumii.\n"
    "4. NICIODATĂ narațiune lungă, poezie exagerată sau descrieri repetitive.\n"

    "\n\n========== OPȚIUNI DE ACȚIUNE ==========\n"
    "La finalul narațiunii, în câmpul 'suggestions', oferă *exact 2–3 acțiuni DISTINCTE*, "
    "realiste, specifice situației curente. Fără repetiție cu sugestiile precedente. Fără opțiuni generice."

    "\n\n========== SARCINA TA PRINCIPALĂ ==========\n"
    "Transformă fiecare input al jucătorului într-o evoluție coerentă, variată, realistă "
    "și impecabil scrisă, într-o Valahie medievală dură și autentică, condusă de Vlad Țepeș."
)

def get_session_id():
    return st.session_state.get('session_id', 'UNKNOWN_SESSION')

def get_all_groq_tokens() -> List[str]:
    """Obține TOATE cheile Groq: GROQ_API_KEY, GROQ_API_KEY1, GROQ_API_KEY2, etc."""
    tokens = []
    token = os.getenv("GROQ_API_KEY")
    if token and token.strip():
        tokens.append(token.strip())
    
    i = 1
    while True:
        token = os.getenv(f"GROQ_API_KEY{i}")
        if token and token.strip():
            tokens.append(token.strip())
            i += 1
        else:
            break
    
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)
    
    return unique_tokens

def clean_ai_response(text: str) -> str:
    if not text: return ""
    
    markers = [
        "<|im_start|>", "<|im_end|>", "user", "assistant", "system", 
        "System:", "User:", "Assistant:", "*", "[End of response]", 
        "[END]", "End of response."
    ]
    for m in markers: 
        text = text.replace(m, "")
    
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def fix_romanian_grammar(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    
    corrections = {
        r'\bturchi\b': 'turci',
        r'\bunui păsări\b': 'unei păsări',
        r'\bunei păsări\b': 'unei păsări',
        r'\bunui (păsări|bestii|creaturi)\b': r'unor \1',
        r'\bsăgeată încoace\b': 'săgeată din spate',
        r'\bte atacă pe tine\b': 'te atacă',
        r'\bpentru ca\b': 'pentru că',
        r'\bsa (?!fi)\b': 'să ',
        r'\bcu o forță mare\b': 'cu forță mare',
        r'\b(ş|ţ)\b': lambda m: 'ș' if m.group(1) == 'ş' else 'ț',
        r'\bîl\b': 'îl',
        r'\bîi\b': 'îi',
        r'\bîți\b': 'îți',
        r'\b(o|un) (armă|săgeată|pumnal|secure|suliță)\b': r'\1n \2',
    }
    
    for pattern, replacement in corrections.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    text = re.sub(r'\s+', ' ', text.strip())
    if text and len(text) > 1:
        text = text[0].upper() + text[1:]
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    
    return text

def generate_with_api(prompt: str) -> NarrativeResponse:
    """
    Generează RĂSPUNS DOAR prin Groq API. Dacă toate cheile eșuează,
    returnează un mesaj de eroare clar pentru utilizator.
    """
    session_id = get_session_id()
    tokens = get_all_groq_tokens()
    
    if not tokens:
        print(f"[SESSION {session_id}] 🔑 NO GROQ TOKENS FOUND")
        st.error("🔒 **Serviciul de Narare este Dezactivat**")
        st.info("➡️ Adaugă `GROQ_API_KEY` în `.env` sau variabile de mediu.")
        return NarrativeResponse(
            narrative="**🔒 Serviciul de Narare este Momentan Indisponibil**  \n"
                     "Nu a fost configurată nicio cheie API validă.  \n"
                     "Contactează administratorul sistemului.",
            game_over=True
        )
    
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    model = "openai/gpt-oss-120b"
    
    global _groq_key_index
    with _groq_key_lock:
        start_index = _groq_key_index
        _groq_key_index = (_groq_key_index + 1) % len(tokens)
    
    for i in range(len(tokens)):
        token_index = (start_index + i) % len(tokens)
        token = tokens[token_index]
        print(f"[SESSION {session_id}] 🔑 ÎNCERC TOKEN {token_index + 1}")
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 1024,
            "stream": False,
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                content = re.sub(r'```json\s*', '', content)
                content = re.sub(r'```\s*', '', content)
                content = content.strip()
                
                try:
                    json_data = json.loads(content)
                    
                    if "narrative" in json_data:
                        json_data["narrative"] = fix_romanian_grammar(json_data["narrative"])
                    
                    if "items_gained" in json_data and isinstance(json_data["items_gained"], list):
                        items_gained = []
                        for item_dict in json_data["items_gained"]:
                            item_dict.setdefault("type", "diverse")
                            item_dict.setdefault("value", 0)
                            item_dict.setdefault("quantity", 1)
                            items_gained.append(InventoryItem(**item_dict))
                        json_data["items_gained"] = items_gained
                    
                    print(f"[SESSION {session_id}] ✅ SUCCES CU TOKEN {token_index + 1}")
                    return NarrativeResponse(**json_data)
                    
                except json.JSONDecodeError as e:
                    print(f"[SESSION {session_id}] ❌ TOKEN {token_index + 1} JSON Decode Error: {e}")
                    continue
                    
                except ValidationError as e:
                    print(f"[SESSION {session_id}] ❌ TOKEN {token_index + 1} Pydantic Validation Error: {e}")
                    continue

            elif response.status_code == 401:
                print(f"[SESSION {session_id}] ❌ TOKEN {token_index + 1} INVALID (401)")
                #st.warning(f"⚠️ Cheia {token_index + 1} este invalidă (401).")
                continue
            elif response.status_code == 429:
                print(f"[SESSION {session_id}] ⚠️ TOKEN {token_index + 1} RATE LIMITED (429)")
                continue
            elif response.status_code == 503:
                print(f"[SESSION {session_id}] ⚠️ TOKEN {token_index + 1} Service Unavailable (503)")
                continue
        
        except requests.exceptions.Timeout:
            print(f"[SESSION {session_id}] ⏱️ TIMEOUT TOKEN {token_index + 1}")
            continue
        except Exception as e:
            print(f"[SESSION {session_id}] ❌ EXCEPȚIE NECUNOSCUTĂ TOKEN {token_index + 1}: {e}")
            continue
    
    # Dacă am epuizat TOATE cheile
    print(f"[SESSION {session_id}] ❌ TOATE TOKEN-URILE AU EȘUAT")
    st.error("🔒 **Serviciul de Narare este Indisponibil**")
    st.info("➡️ Toate conexiunile API au eșuat. Încearcă din nou peste câteva minute.")
    
    return NarrativeResponse(
        narrative="**🔒 Serviciul de Narare este Momentan Indisponibil**  \n"
                 "Toate cheile API au eșuat sau au atins limita.  \n"
                 "Încearcă din nou peste câteva minute.",
        game_over=False
    )

def generate_narrative_with_progress(prompt: str) -> NarrativeResponse:
    """
    Generează narativ cu bară de progres. Dacă API eșuează complet,
    afișează mesaj de eroare pentru utilizator.
    """
    result_container = {"response": None, "error": None}
    
    def run_gen():
        try:
            result_container["response"] = generate_with_api(prompt)
        except Exception as e:
            result_container["error"] = str(e)
            print(f"❌ Eroare în thread-ul de generare: {e}")
    
    t = threading.Thread(target=run_gen, daemon=True)
    add_script_run_ctx(t)
    t.start()
    
    progress_container = st.empty()
    status_text = st.empty()
    
    with progress_container:
        progress_bar = st.progress(0)
        progress = 0
        
        while t.is_alive():
            time.sleep(0.1)
            if progress < 85:
                progress = min(progress + random.randint(1, 5), 85)
                progress_bar.progress(progress)
                status_text.markdown(
                    f'<div class="progress-text">⚔️ Scribii lui Vlad scriu... {progress}%</div>',
                    unsafe_allow_html=True
                )
        
        t.join()
        
        for i in range(progress, 101):
            progress_bar.progress(i)
            time.sleep(0.005)
        
        status_text.empty()
    
    progress_container.empty()
    
    if result_container["error"]:
        st.error(f"🧙 NARATOR: **EROARE CRITICĂ**: {result_container['error']}")
        return NarrativeResponse(
            narrative="**🔒 Eroare Sistem**  \nA apărut o eroare neașteptată. Reîncearcă.",
            game_over=False
        )
    
    response = result_container["response"]
    if not response:
        return NarrativeResponse(
            narrative="**🔒 Nu am putut genera un răspuns valid.**  \n"
                     "Verifică conexiunea la internet și cheile API.",
            game_over=False
        )
    
    return response