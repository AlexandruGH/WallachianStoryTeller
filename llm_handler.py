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
from huggingface_hub import get_token
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

class ModelRouter:
    def __init__(self):
        self.api_models = [
            "meta-llama/Llama-3.1-8B-Instruct:novita",
            "meta-llama/Llama-3.1-70B-Instruct:fireworks-ai",
            "Qwen/Qwen2.5-VL-72B-Instruct:nebius"
        ]
        self.current_index = 0
    def get_next_api_model(self):
        model = self.api_models[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_models)
        return model

model_router = ModelRouter()

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

def get_hf_token():
    token = os.getenv("HF_TOKEN")
    if token: return token
    try:
        if "HF_TOKEN" in st.secrets:
            token = st.secrets["HF_TOKEN"]
            os.environ["HF_TOKEN"] = token
            return token
    except: pass
    token = get_token()
    return token

def validate_hf_token():
    token = get_hf_token()
    if not token:
        st.error("🔑 **HF_TOKEN lipsește!**")
        st.info("Adaugă-l în fișierul `.env` (local) sau în `Secrets` (Cloud):")
        st.code("HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", language="bash")
        return False
    if not token.startswith("hf_"):
        st.warning("⚠️ Tokenul nu pare valid (trebuie să înceapă cu 'hf_')")
    return True

def clean_ai_response(text: str) -> str:
    if not text: return ""
    markers = ["<|im_start|>", "<|im_end|>", "user", "assistant", "system", "System:", "User:", "Assistant:"]
    for m in markers: text = text.replace(m, "")
    return text.strip()

def extract_prompts_from_formatted_prompt(fp: str):
    parts = fp.split("<|im_start|>")
    system_block = next(p for p in parts if p.startswith("system"))
    user_block = next(p for p in parts if p.startswith("user"))
    system_text = system_block.replace("system\n", "").replace("<|im_end|>", "").strip()
    user_text = user_block.replace("user\n", "").replace("<|im_end|>", "").strip()
    return system_text, user_text

def generate_with_api(prompt: str) -> str:
    token = get_hf_token()
    if not token:
        return "api_fail"

    formatted_prompt = (
        f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{prompt}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    # ⇢  folosim PRIMUL model din listă până când obținem eroare
    model = model_router.api_models[0]
    api_url = "https://router.huggingface.co/v1/chat/completions"
    system_prompt, user_prompt = extract_prompts_from_formatted_prompt(formatted_prompt)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.85,
        "top_p": 0.92,
        "repetition_penalty": 1.2,
        "return_full_text": False
    }

    try:
        print(f"🌐 Apel API: {model}")
        response = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=25
        )

        if response.status_code == 200:
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            cleaned = clean_ai_response(raw_text)
            if len(cleaned) > 10:
                print(f"✅ Succes: {model}")
                return cleaned
            print(f"⚠️ Răspuns prea scurt, încerc fallback...")
        elif response.status_code == 401:
            st.error("❌ Token invalid! Status 401")
            return "api_fail"
        elif response.status_code == 503:
            print(f"⚠️ Model ocupat (503): {model}")
            time.sleep(2)
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout: {model}")
    except Exception as e:
        print(f"❌ Excepție la {model}: {e}")

    # ⇢  doar DACĂ primul model a eșuat trecem la următorul
    st.warning("⚠️ Primul model a eșuat – activăm fallback...")
    for _ in range(1, len(model_router.api_models)):
        model = model_router.get_next_api_model()
        payload["model"] = model
        try:
            response = requests.post(
                api_url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=25
            )
            if response.status_code == 200:
                data = response.json()
                raw_text = data["choices"][0]["message"]["content"]
                cleaned = clean_ai_response(raw_text)
                if len(cleaned) > 10:
                    print(f"✅ Succes fallback: {model}")
                    return cleaned
        except:
            continue

    print("❌ Toate modelele API au eșuat!")
    return "api_fail"

def generate_local(prompt: str) -> str:
    tokenizer, model = load_local_model()
    if not tokenizer or not model:
        st.error("❌ Modelul local nu este disponibil. Instalează `distilgpt2` manual.")
        return "Conexiunea cu tărâmul magic s-a întrerupt. (Verifică Token-ul HF)"
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
        if validate_hf_token():
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
        return "Conexiunea cu tărâmul magic s-a întrerupt. (Verifică Token-ul HF)"
    final = result_container["text"]
    if not final or final in ["api_fail", ""]:
        st.error("🧙 NARATOR: **CRITICAL ERROR**: No model available. Check HF_TOKEN and internet.")
        return "Conexiunea cu tărâmul magic s-a întrerupt. (Verifică Token-ul HF)"
    return final