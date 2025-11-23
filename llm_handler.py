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
from dotenv import load_dotenv

load_dotenv()

def load_env_file():
    possible_paths = ['.env', os.path.join(os.path.dirname(__file__), '.env'), os.path.join(os.getcwd(), '.env')]
    for env_path in possible_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            return True
    return False

load_env_file()

if os.name == 'nt':
    os.environ["HF_HOME"] = "D:/huggingface_cache"
    os.makedirs("D:/huggingface_cache", exist_ok=True)

SYSTEM_PROMPT = (
    "Ești un Narator D&D în limba română. "
    "Păstrează firul narativ: locație, obiecte, NPC-uri, starea eroului. "
    "Nu repeta replici. 2-3 propoziții vii, medievale, fără meta-comentarii. "
    "Oferă mereu 2-3 opțiuni clare de acțiune jucătorului la final, precedate de "
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
    markers = ["<|im_start|>", "<|im_end|>", "user", "assistant", "system", "System:", "User:", "Assistant:", "*"]
    for m in markers: text = text.replace(m, "")
    return text.strip()

def generate_with_api(prompt: str) -> str:
    token = get_groq_token()
    if not token:
        return "api_fail"

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    model = "openai/gpt-oss-120b"#"llama-3.3-70b-versatile"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 1,
        "max_completion_tokens": 1024,
        "top_p": 1,
        "stream": True,
        "stop": None
    }

    try:
        print(f"🌐 Apel API: {model}")
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30,
            stream=True
        )

        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get('choices', [])
                            if choices:
                                delta = choices[0].get('delta', {})
                                content = delta.get('content')
                                if content:
                                    full_response += content
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Eroare la parsarea JSON: {e}")
                            continue
            
            cleaned = clean_ai_response(full_response)
            if len(cleaned) > 10:
                print(f"✅ Succes: {model}")
                return cleaned
            print(f"⚠️ Răspuns prea scurt, folosim fallback...")
            return "api_fail"
        elif response.status_code == 401:
            st.error("❌ Token invalid! Status 401")
            return "api_fail"
        elif response.status_code == 503:
            print(f"⚠️ Model ocupat (503): {model}")
            time.sleep(2)
            return "api_fail"
        else:
            print(f"⚠️ Status code neașteptat: {response.status_code}")
            return "api_fail"
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout: {model}")
        return "api_fail"
    except Exception as e:
        print(f"❌ Excepție la {model}: {e}")
        return "api_fail"

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