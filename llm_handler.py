import os
import sys
import streamlit as st
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import requests
import threading
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


SYSTEM_PROMPT = (
    "Ești Naratorul Tărâmului Valah în veacul al XV-lea, în zilele domniei lui Vlad Țepeș (Drăculea). "
    "Tonul tău este medieval românesc: grav, aspru, veridic și autentic, folosind expresii arhaice și un vocabular variat specific epocii (ex: zăbavă, hrisov, pârcălab, ienicer, podoabă, tăinuind). "
    "Nu folosi obiecte, noțiuni sau emoții moderne (ex: puști, singurătate, frică excesivă) și evită orice meta-comentariu. "

    "Mecanica narativă și coerența: "
    "1. **Anti-Repetiție Strictă:** Variează structura propozițiilor, descrierile (vânt/umbre) și verbele. Nu repeta descrieri similare în două răspunsuri consecutive. "
    "2. **Realism Medieval:** Respectă coerența locurilor (cetăți, sate, codri, mănăstiri, drumuri de negoț) și a personajelor (boieri, călăreți ai curții, țărani, monahi, negustori). "
    "3. **Firul Narativ:** Povestea se leagă de isprăvi domnești, slujbe trimise de Vlad Vodă, sau întâlniri ce dezvăluie secrete și primejdii ale vremii (ex: atacuri otomane, comploturi boierești, legende locale). "
    "4. **Descriere Scenă:** Păstrează firul narativ: locație, obiecte găsite/pierdute, NPC-uri, starea eroului. "
    "5. **Lungime și Stil:** Scrie **strict 2-4 propoziții** vii, direct legate de acțiunea jucătorului, evitând pasajele lungi sau divagațiile. "
    "6. **Opțiuni:** Oferă **mereu 2-3 opțiuni clare** de acțiune jucătorului la final. Fă-le concise și distincte."
)


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
    Generează răspuns folosind Groq API și returnează obiect Pydantic validat.
    Forcează format JSON și aplică corecții automate, cu 2 retry-uri pe erori JSON.
    """
    token = get_groq_token()
    if not token:
        return NarrativeResponse(
            narrative="Conexiunea cu tărâmul magic s-a întrerupt. (Verifică GROQ_API_KEY în .env)",
            game_over=True
        )

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    model = "openai/gpt-oss-120b"
    max_retries = 3  # Încercarea inițială + 2 reîncercări
    
    for attempt in range(max_retries):
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": (
                        "Ești un sistem JSON de joc D&D. Returnează EXCLUSIV JSON valid conform schemei, "
                        "fără markdown, fără comentarii, fără text suplimentar. "
                        "Asigură-te că 'narrative' este în română medievală corectă."
                    )
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
                
                # Parse JSON
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
                    
                    print(f"\n{'='*40} LLM RAW RESPONSE {'='*40}")
                    print(f"JSON RAW Content: {content}") 
                    print(f"Câmp 'suggestions' există: {'suggestions' in json_data}")
                    if 'suggestions' in json_data:
                        print(f"Valoare sugestii: {json_data['suggestions']}")
                    print(f"{'='*90}\n")
                    
                    # 🔥 Validează și returnează Pydantic model - SUCCESS EXIT POINT
                    return NarrativeResponse(**json_data)
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON Decode Error: {e} - Reîncercare {attempt + 1}/{max_retries - 1}...")
                    time.sleep(1) # Pauză scurtă înainte de reîncercare
                    continue # Mergi la următoarea încercare
                    
                except ValidationError as e:
                    print(f"❌ Pydantic Validation Error: {e} - Reîncercare {attempt + 1}/{max_retries - 1}...")
                    print(f"📄 JSON data (Validation Failed): {json_data}") 
                    time.sleep(1) # Pauză scurtă înainte de reîncercare
                    continue # Mergi la următoarea încercare

                except Exception as e:
                    print(f"❌ Unexpected Error during Pydantic/Data processing: {e}")
                    import traceback
                    traceback.print_exc()
                    break # Ieși din buclă la eroare neașteptată
            
            # 🔥 Handle specific API errors (401, 429, 503) - These should break or return immediately
            elif response.status_code == 401:
                st.error("❌ Token invalid! Status 401 - Verifică GROQ_API_KEY")
                return NarrativeResponse(narrative="Autentificare eșuată. Token-ul API este invalid sau expirat.", game_over=True)
            elif response.status_code == 429:
                st.warning("⚠️ Rate limit atins.")
                if attempt < max_retries - 1:
                    time.sleep(random.randint(2, 5))
                    continue
                else:
                    return NarrativeResponse(narrative="API-ul este ocupat.", game_over=False)
            elif response.status_code == 503:
                print(f"⚠️ Service Unavailable (503): {model}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    return NarrativeResponse(narrative="Serviciul este temporar indisponibil.", game_over=False)
            else:
                print(f"⚠️ Unexpected status code: {response.status_code}")
                break # Ieși din buclă la alte erori HTTP
        
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout la {model} (45s)")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                return NarrativeResponse(narrative="Cererea a expirat. Verifică conexiunea la internet.", game_over=False)
        except Exception as e:
            print(f"❌ Excepție neașteptată în REQUEST: {e}")
            import traceback
            traceback.print_exc()
            break # Ieși din buclă la erori de rețea sau altele
            
    # Dacă bucla s-a terminat fără succes (din cauza JSON/Pydantic errors sau break)
    return NarrativeResponse(
        narrative="Naratorul este epuizat. Nu a putut genera un răspuns valid după multiple încercări.",
        game_over=False
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