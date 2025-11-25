import os
import sys
import streamlit as st
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import requests
import threading
from typing import List, Optional
import time
import random
import re
import json
from streamlit.runtime.scriptrunner import add_script_run_ctx
from pydantic import ValidationError # ⭕ FIX: Added explicit Pydantic ValidationError import

from models import InventoryItem, NarrativeResponse

if os.name == 'nt':
    os.environ["HF_HOME"] = "D:/huggingface_cache"
    os.makedirs("D:/huggingface_cache", exist_ok=True)


# Thread-safe rotation pentru Groq API keys
_groq_key_index = 0
_groq_key_lock = threading.Lock()

# llm_handler.py
SYSTEM_PROMPT = (
    "Ești Naratorul Tărâmului Valah în veacul al XV-lea, în zilele domniei lui Vlad Țepeș (Drăculea). "
    "Tonul tău este medieval românesc: grav, aspru, veridic și autentic, folosind expresii arhaice și un vocabular variat specific epocii. "
    "DIALOG DIRECT & FORMAL: Când adresez o întrebare unui personaj, mai ales NPC-uri majore ca Vlad Țepeș, favorizează dialogul în locul narațiunii și oferă prioritar replica în **GHILIMELE** duble (\"\") alături de contextul naratorului."
    "Nu folosi obiecte, noțiuni sau emoții moderne (ex: puști, singurătate, frică excesivă) și evită orice meta-comentariu. "

    "\n\n**MECANICA NARATIVĂ ȘI DIALOGUL:**"
    "1. **Anti-Repetiție Strictă:** Variează structura propozițiilor, descrierile (vânt/umbre) și verbele. Nu repeta descrieri similare în două răspunsuri consecutive. "
    "2. **Realism Medieval:** Respectă coerența locurilor (cetăți, sate, codri, mănăstiri, drumuri de negoț) și a personajelor (boieri, călăreți ai curții, țărani, monahi, negustori). "
    "3. **Firul Narativ:** Povestea se leagă de isprăvi domnești, slujbe trimise de Vlad Vodă, sau întâlniri ce dezvăluie secrete și primejdii ale vremii (ex: atacuri otomane, comploturi boierești, legende locale). "
    "4. **Descriere Scenă:** Păstrează firul narativ: locație, obiecte găsite/pierdute, NPC-uri, starea eroului. "
    "5. **Lungime și Stil:** Scrie strict 2-4 propoziții vii, direct legate de acțiunea jucătorului, evitând pasajele lungi sau divagațiile. "
    "6. **Opțiuni (FĂRĂ REPETIȚIE):** Oferă **mereu 2-3 opțiuni clare** de acțiune jucătorului la final. **Nu repeta aceleași opțiuni** dacă nu au fost alese, ci continuă logic firul narativ." # <--- ADĂUGATĂ REGULĂ ANTI-REPETIȚIE AICI
)

def get_session_id():
    """Obține ID-ul de sesiune din Streamlit session_state"""
    return st.session_state.get('session_id', 'UNKNOWN_SESSION')

def get_all_groq_tokens() -> List[str]:
    """Obține TOATE cheile Groq din mediu: GROQ_API_KEY, GROQ_API_KEY1, GROQ_API_KEY2, etc."""
    tokens = []
    # Cheia principală
    token = os.getenv("GROQ_API_KEY")
    if token and token.strip():
        tokens.append(token.strip())
    
    # Chei secundare (GROQ_API_KEY1, GROQ_API_KEY2, ...)
    i = 1
    while True:
        token = os.getenv(f"GROQ_API_KEY{i}")
        if token and token.strip():
            tokens.append(token.strip())
            i += 1
        else:
            break
    
    # Elimină duplicate păstrând ordinea
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)
    
    return unique_tokens


@st.cache_resource(show_spinner=True)
def load_local_model():
    try:
        model_name = "distilgpt2"
        cache_dir = os.getenv("HF_HOME", None)
        tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
        model = AutoModelForCausalLM.from_pretrained(model_name, cache_dir=cache_dir, torch_dtype=torch.float32, device_map="cpu")
        return tokenizer, model
    except Exception as e:
        return None, None

def get_groq_token():
    token = os.getenv("GROQ_API_KEY")
    if token: return token
    try:
        if "GROQ_API_KEY" in st.secrets:
            token = st.secrets["GROQ_API_KEY"]
            os.environ["GROQ_API_KEY"] = token
            return token
    except: pass
    return None

def validate_groq_token():
    token = get_groq_token()
    if not token:
        st.error("🔑 **GROQ_API_KEY lipsește!**")
        st.info("Adaugă-l în fișierul `.env` (local) sau în `Secrets` (Cloud):")
        st.code("GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", language="bash")
        return False
    if not token.startswith("gsk_"):
        st.warning("⚠️ Tokenul nu pare valid (trebuie să înceapă cu 'gsk_')")
    return True

def clean_ai_response(text: str) -> str:
    if not text: return ""
    
    # Eliminăm artifact-urile comune
    markers = [
        "<|im_start|>", "<|im_end|>", "user", "assistant", "system", 
        "System:", "User:", "Assistant:", "*", "[End of response]", 
        "[END]", "End of response."
    ]
    for m in markers: 
        text = text.replace(m, "")
    
    # Eliminăm spații multiple și newline-uri excesive
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def fix_romanian_grammar(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    
    corrections = {
        # Greșelile tale specificate
        r'\bturchi\b': 'turci',
        r'\bunui păsări\b': 'unei păsări',  # ⭕ FIX PENTRU PROBLEMA TA
        r'\bunei păsări\b': 'unei păsări',   # Confirmă forma corectă
        r'\bunui (păsări|bestii|creaturi)\b': r'unor \1',  # Plural corect
        r'\bsăgeată încoace\b': 'săgeată din spate',
        r'\bte atacă pe tine\b': 'te atacă',
        r'\bpentru ca\b': 'pentru că',
        r'\bsa (?!fi)\b': 'să ',
        r'\bcu o forță mare\b': 'cu forță mare',
        # Diacritice
        r'\b(ş|ţ)\b': lambda m: 'ș' if m.group(1) == 'ş' else 'ț',
        r'\bîl\b': 'îl',
        r'\bîi\b': 'îi',
        r'\bîți\b': 'îți',
        # Articole + substantive
        r'\b(o|un) (armă|săgeată|pumnal|secure|suliță)\b': r'\1n \2',
    }
    
    for pattern, replacement in corrections.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Capitalizare și punct final
    text = re.sub(r'\s+', ' ', text.strip())
    if text and len(text) > 1:
        text = text[0].upper() + text[1:]
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    
    return text

def generate_with_api(prompt: str, use_api: bool = True) -> NarrativeResponse:
    """
    Generează răspuns folosind Groq API cu rotație inteligentă de chei.
    La fiecare request se rotește la următoarea cheie. Dacă o cheie eșuează,
    se încearcă automat următoarea din listă.
    """
    session_id = get_session_id()  # ⭕ OBTINE ID SESIUNE
    tokens = get_all_groq_tokens()
    if not tokens:
        print(f"[SESSION {session_id}] 🔑 NO GROQ TOKENS FOUND")  # ⭕ LOG
        return NarrativeResponse(
            narrative="Conexiunea cu tărâmul magic s-a întrerupt. (Verifică GROQ_API_KEY în .env)",
            game_over=True
        )
    print(f"[SESSION {session_id}] 🔑 USING TOKEN: {tokens[start_index][:10]}...")  # ⭕ LOG TOKEN
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    model = "openai/gpt-oss-120b"
    max_retries_per_key = 1  # Doar 1 încercare per cheie înainte de a roti
    
    # Thread-safe rotation: determinăm cheia de start pentru acest request
    global _groq_key_index
    with _groq_key_lock:
        start_index = _groq_key_index
        # Incrementăm pentru următorul request
        _groq_key_index = (_groq_key_index + 1) % len(tokens)
    
    # Încercăm fiecare cheie începând de la index-ul rotit
    for i in range(len(tokens)):
        token_index = (start_index + i) % len(tokens)
        token = tokens[token_index]
        
        # Afișăm doar dacă avem mai multe chei
        if len(tokens) > 1:
            st.toast(f"🔑 Folosind cheia Groq {token_index + 1}/{len(tokens)}", icon="🔄")
        
        for attempt in range(max_retries_per_key):
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system", 
                        "content": SYSTEM_PROMPT
                    },
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
                        
                        #print(f"\n{'='*40} LLM RAW RESPONSE {'='*40}")
                        #print(f"JSON RAW Content: {content}") 
                        #rint(f"Câmp 'suggestions' există: {'suggestions' in json_data}")
                        #if 'suggestions' in json_data:
                        #    print(f"Valoare sugestii: {json_data['suggestions']}")
                        #print(f"{'='*90}\n")
                        print(f"[SESSION {session_id}] ✅ SUCCESS WITH TOKEN {token_index + 1}")  # ⭕ LOG SUCCES
                        # Returnăm răspunsul validat
                        return NarrativeResponse(**json_data)
                        
                    except json.JSONDecodeError as e:
                        print(f"[SESSION {session_id}] ❌ TOKEN {token_index + 1} JSON Decode Error: {e}")  # ⭕ LOG
                        
                        if attempt < max_retries_per_key - 1:
                            time.sleep(1)
                            continue
                        else:
                            st.warning(f"⚠️ JSON invalid cu cheia {token_index + 1}, trecem la următoarea...")
                            break
                            
                    except ValidationError as e:
                        print(f"[SESSION {session_id}] ❌ TOKEN {token_index + 1} Pydantic Validation Error: {e} {json_data}")  # ⭕ LOG
                        if attempt < max_retries_per_key - 1:
                            time.sleep(1)
                            continue
                        else:
                            st.warning(f"⚠️ Validare eșuată cu cheia {token_index + 1}, trecem la următoarea...")
                            break

                    except Exception as e:
                        print(f"[SESSION {session_id}] ❌ TOKEN {token_index + 1} Unexpected Error during Pydantic/Data processing: {e}")  # ⭕ LOG
                        import traceback
                        traceback.print_exc()
                        break
                
                # Handle specific API errors
                elif response.status_code == 401:
                    print(f"[SESSION {session_id}] ❌ TOKEN {token_index + 1} INVALID (401)")  # ⭕ LOG
                    st.error(f"❌ Cheia {token_index + 1} este invalidă (401)!")
                    break  # Trecem la următoarea cheie
                elif response.status_code == 429:
                    print(f"[SESSION {session_id}] ⚠️ TOKEN {token_index + 1} RATE LIMITED (429)")  # ⭕ LOG
                    st.warning(f"⚠️ Rate limit atins pentru cheia {token_index + 1} (429).")
                    break  # Trecem la următoarea cheie
                elif response.status_code == 503:
                    print(f"[SESSION {session_id}] ⚠️ TOKEN {token_index + 1} Service Unavailable (503): {model}")  # ⭕ LOG
                    break  # Trecem la următoarea cheie
                else:
                    print(f"[SESSION {session_id}] ⚠️ TOKEN {token_index + 1} Unexpected status code: {model}")  # ⭕ LOG
                    break
            
            except requests.exceptions.Timeout:
                print(f"[SESSION {session_id}] ⏱️ TIMEOUT TOKEN {token_index + 1}")  # ⭕ LOG
                break  # Trecem la următoarea cheie
            except Exception as e:
                print(f"[SESSION {session_id}] ❌ Unknown EXCEPTION TOKEN {token_index + 1}: {e}")  # ⭕ LOG
                import traceback
                traceback.print_exc()
                break
    print(f"[SESSION {session_id}] ❌ ALL TOKENS FAILED")  # ⭕ LOG
    # Dacă am epuizat toate cheile
    return NarrativeResponse(
        narrative=f"Toate conexiunile magice au eșuat. (Verifică {len(tokens)} GROQ_API_KEY în .env)",
        game_over=True
    )

    
def generate_narrative_with_progress(prompt: str, use_api: bool = True) -> NarrativeResponse:
    """
    Generează narativ cu bară de progres animată și returnează NarrativeResponse.
    Păstrează experiența "Scribii lui Vlad scriu..." în timp ce API-ul lucrează.
    """
    result_container = {"response": None, "error": None}
    
    def run_gen():
        try:
            result_container["response"] = generate_with_api(prompt, use_api)
        except Exception as e:
            result_container["error"] = str(e)
            print(f"❌ Eroare în thread-ul de generare: {e}")
    
    # Pornește thread-ul de generare în background
    t = threading.Thread(target=run_gen, daemon=True)
    add_script_run_ctx(t)
    t.start()
    
    # 🔥 UI de progres - animația vizibilă
    progress_container = st.empty()
    status_text = st.empty()
    
    with progress_container:
        progress_bar = st.progress(0)
        progress = 0
        
        # Actualizează progresul cât timp thread-ul rulează
        while t.is_alive():
            time.sleep(0.1)
            if progress < 85:
                progress = min(progress + random.randint(1, 5), 85)
                progress_bar.progress(progress)
                status_text.markdown(
                    f'<div class="progress-text">⚔️ Scribii lui Vlad scriu... {progress}%</div>',
                    unsafe_allow_html=True
                )
        
        # Așteaptă finalizarea thread-ului
        t.join()
        
        # Completează animația la 100%
        for i in range(progress, 101):
            progress_bar.progress(i)
            time.sleep(0.005)
        
        # Curăță textul de status
        status_text.empty()
    
    # Curăță containerul de progres
    progress_container.empty()
    
    # 🔥 Procesează rezultatul
    if result_container["error"]:
        st.error(f"🧙 NARATOR: **Eroare Critică**: {result_container['error']}")
        return NarrativeResponse(
            narrative="Conexiunea cu tărâmul magic s-a întrerupt. (Verifică Token-ul)",
            game_over=True
        )
    
    response = result_container["response"]
    if not response:
        return NarrativeResponse(
            narrative="Nu am putut genera un răspuns valid.",
            game_over=False
        )
    
    return response

def generate_local(prompt: str) -> str:
    tokenizer, model = load_local_model()
    if not tokenizer or not model:
        st.error("❌ Modelul local nu este disponibil. Instalează `distilgpt2` manual.")
        return "Conexiunea cu tărâmul magic s-a întrerupt. (Verifică Token-ul)"
    try:
        context_prompt = f"Fantasy story: {prompt}"
        inputs = tokenizer(context_prompt, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=80, do_sample=True, temperature=0.9, pad_token_id=tokenizer.eos_token_id)
        text = tokenizer.decode(out[0], skip_special_tokens=True)
        result = clean_ai_response(text.replace(context_prompt, ""))
        return result
    except Exception as e:
        st.error(f"❌ Eroare la generarea locală: {e}")
        return "Ceva a tulburat liniștea..."

def generate_story_text(prompt: str, use_api: bool = True) -> str:
    if use_api:
        if validate_groq_token():
            res = generate_with_api(prompt)
            if res != "api_fail": return res
            st.warning("⚠️ API a eșuat complet. Folosesc modelul local...")
        else:
            st.warning("⚠️ Token invalid. Folosesc modelul local...")
    return generate_local(prompt)

def generate_story_text_with_progress(prompt: str, use_api: bool = True) -> str:
    result_container = {"text": "", "done": False, "error": None}
    def run_gen():
        try:
            result_container["text"] = generate_story_text(prompt, use_api)
        except Exception as e:
            result_container["error"] = str(e)
        finally:
            result_container["done"] = True
    t = threading.Thread(target=run_gen)
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
                status_text.markdown(f'<div class="progress-text">⚔️ Scribii lui Vlad scriu... {progress}%</div>', unsafe_allow_html=True)
        t.join()
        for i in range(progress, 101):
            progress_bar.progress(i)
            time.sleep(0.005)
        status_text.empty()
    progress_container.empty()
    if result_container["error"]:
        st.error(f"🧙 NARATOR: **CRITICAL ERROR**: {result_container['error']}")
        return "Conexiunea cu tărâmul magic s-a întrerupt. (Verifică Token-ul)"
    final = result_container["text"]
    if not final or final in ["api_fail", ""]:
        st.error("🧙 NARATOR: **CRITICAL ERROR**: No model available. Check GROQ_API_KEY and internet.")
        return "Conexiunea cu tărâmul magic s-a întrerupt. (Verifică Token-ul)"
    return final