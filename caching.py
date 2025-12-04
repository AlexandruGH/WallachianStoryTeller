import os
import json
import hashlib
import threading
from typing import Optional, Dict, Any
from models import NarrativeResponse

class CacheManager:
    CACHE_DIR = "cache"
    MEMORY_CACHE = {}
    SOURCE_CACHE = {}  # Cache for exact text match (User Action -> Response)

    @classmethod
    def _ensure_cache_dir(cls):
        if not os.path.exists(cls.CACHE_DIR):
            os.makedirs(cls.CACHE_DIR)

    @classmethod
    def _get_hash(cls, key: str) -> str:
        return hashlib.sha512(key.encode('utf-8')).hexdigest()

    @classmethod
    def _get_path(cls, key: str) -> str:
        """Generate file path from prompt hash."""
        cls._ensure_cache_dir()
        hashed_key = cls._get_hash(key)
        return os.path.join(cls.CACHE_DIR, f"{hashed_key}.json")

    @classmethod
    def get(cls, prompt: str) -> Optional[NarrativeResponse]:
        """Retrieve narrative response from cache if exists."""
        # 1. Check Memory Cache (Hash based)
        hashed_key = cls._get_hash(prompt)
        if hashed_key in cls.MEMORY_CACHE:
            try:
                return NarrativeResponse(**cls.MEMORY_CACHE[hashed_key])
            except Exception as e:
                print(f"[CACHE] Memory cache error: {e}")

        # 2. Check Disk Cache
        filepath = os.path.join(cls.CACHE_DIR, f"{hashed_key}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return NarrativeResponse(**data)
            except Exception as e:
                print(f"[CACHE] Error reading disk cache: {e}")
                
        return None

    @classmethod
    def get_by_text(cls, user_text: str) -> Optional[NarrativeResponse]:
        """Retrieve response by EXACT user text match (from Source Cache)."""
        if not user_text:
            return None
            
        # Try exact match
        if user_text in cls.SOURCE_CACHE:
            print(f"[CACHE] HIT by text match: '{user_text[:20]}...'")
            try:
                return NarrativeResponse(**cls.SOURCE_CACHE[user_text])
            except Exception as e:
                print(f"[CACHE] Text cache parse error: {e}")
                
        # Try stripped match
        stripped = user_text.strip()
        if stripped in cls.SOURCE_CACHE:
             print(f"[CACHE] HIT by stripped text match: '{stripped[:20]}...'")
             try:
                return NarrativeResponse(**cls.SOURCE_CACHE[stripped])
             except Exception as e:
                print(f"[CACHE] Text cache parse error: {e}")
                
        return None

    @classmethod
    def set(cls, prompt: str, response: NarrativeResponse):
        """Save narrative response to cache."""
        # Save to disk mainly
        filepath = cls._get_path(prompt)
        try:
            data = response.model_dump()
            
            # Update memory too
            hashed_key = cls._get_hash(prompt)
            cls.MEMORY_CACHE[hashed_key] = data
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[CACHE] Error writing to cache: {e}")

    @classmethod
    def exists(cls, prompt: str) -> bool:
        """Check if prompt is already cached."""
        hashed_key = cls._get_hash(prompt)
        if hashed_key in cls.MEMORY_CACHE:
            return True
        return os.path.exists(os.path.join(cls.CACHE_DIR, f"{hashed_key}.json"))

    @classmethod
    def clear_memory(cls):
        """Clear the in-memory cache."""
        count = len(cls.MEMORY_CACHE)
        cls.MEMORY_CACHE.clear()
        cls.SOURCE_CACHE.clear()
        print(f"[CACHE] Cleared {count} items from memory.")

    @classmethod
    def load_pack(cls, pack_path: str, clear_previous: bool = False):
        """Load a story pack into the MEMORY cache."""
        if clear_previous:
            cls.clear_memory()

        if not os.path.exists(pack_path):
            print(f"[CACHE] Pack not found: {pack_path}")
            return
            
        try:
            with open(pack_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            cache_data = data.get("cache_data", {})
            count = 0
            for key_hash, response_dict in cache_data.items():
                cls.MEMORY_CACHE[key_hash] = response_dict
                count += 1
            
            print(f"[CACHE] Loaded {count} entries from pack into memory.")
        except Exception as e:
            print(f"[CACHE] Error loading pack: {e}")

    @classmethod
    def load_source_pack(cls, source_path: str):
        """Load a source pack (UserText -> Response) into SOURCE_CACHE."""
        if not os.path.exists(source_path):
            # print(f"[CACHE] Source pack not found: {source_path}") 
            # Silent fail as it is optional
            return
            
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            for user_text, response_dict in data.items():
                cls.SOURCE_CACHE[user_text] = response_dict
                count += 1
            
            print(f"[CACHE] Loaded {count} entries from source pack: {os.path.basename(source_path)}")
        except Exception as e:
            print(f"[CACHE] Error loading source pack: {e}")
