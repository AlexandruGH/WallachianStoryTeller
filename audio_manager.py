"""
Audio Manager for Wallachia RPG - Dynamic Sound System
Handles SFX, background music, and audio context from LLM responses
"""

import os
import json
import streamlit as st
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class AudioEvent:
    """Represents an audio event with timing and priority"""
    event_type: str
    timestamp: float
    priority: int = 1  # 1=low, 2=medium, 3=high

class AudioManager:
    """Manages all audio playback for the Wallachia RPG"""

    # Audio file mappings - Updated to match actual downloaded files
    SFX_MAP = {
        "gold_received": "coins.mp3",
        "mysterious_location": "whisper_wind.mp3",
        "combat_start": "sword_draw.mp3",
        "hit": "hit.mp3",
        "victory": "victory_horn.mp3",
        "defeat": "defeat_drum.mp3",
        "quest_new": "quest_new.mp3",
        "decision_important": "decision_important.mp3",
        "door_open": "door_open.mp3",
        "horse": "horse_hooves.mp3",
        "forest_ambient": "forest_ambient.mp3",
        "castle_ambient": "castle_ambient.mp3"
    }

    MUSIC_MAP = {
        "calm_ambient": "dark_forest.mp3",
        "court_intrigue": "court_intrigue.mp3",
        "dark_forest": "dark_forest.mp3",
        "battle_low": "battle_high.mp3",
        "battle_high": "battle_high.mp3"
    }

    def __init__(self):
        self.audio_dir = "audio"
        self.sfx_dir = os.path.join(self.audio_dir, "sfx")
        self.music_dir = os.path.join(self.audio_dir, "music")

        # Audio state
        self.current_music: Optional[str] = None
        self.is_muted = False
        self.master_volume = 0.7
        self.music_volume = 0.3
        self.sfx_volume = 0.8

        # Cooldown tracking (event_type -> last_play_time)
        self.sfx_cooldowns: Dict[str, float] = {}
        self.min_cooldown = 3.0  # seconds between same SFX

        # Recent events queue
        self.recent_events: List[AudioEvent] = []

        # Initialize session state for audio preferences
        self._init_session_state()

    def _init_session_state(self):
        """Initialize audio preferences in session state"""
        if "audio_muted" not in st.session_state:
            st.session_state.audio_muted = False
        if "audio_master_volume" not in st.session_state:
            st.session_state.audio_master_volume = 0.7
        if "audio_music_volume" not in st.session_state:
            st.session_state.audio_music_volume = 0.3
        if "audio_sfx_volume" not in st.session_state:
            st.session_state.audio_sfx_volume = 0.8

        # Sync instance variables
        self.is_muted = st.session_state.audio_muted
        self.master_volume = st.session_state.audio_master_volume
        self.music_volume = st.session_state.audio_music_volume
        self.sfx_volume = st.session_state.audio_sfx_volume

    def _update_session_state(self):
        """Update session state with current audio settings"""
        st.session_state.audio_muted = self.is_muted
        st.session_state.audio_master_volume = self.master_volume
        st.session_state.audio_music_volume = self.music_volume
        st.session_state.audio_sfx_volume = self.sfx_volume

    def _get_audio_path(self, filename: str, audio_type: str) -> Optional[str]:
        """Get full path to audio file, checking multiple extensions"""
        base_dir = self.sfx_dir if audio_type == "sfx" else self.music_dir
        
        # Try exact match first
        path = os.path.join(base_dir, filename)
        if os.path.exists(path) and not path.endswith('.placeholder'):
            return path
            
        # Try swapping extension (mp3 <-> ogg <-> wav)
        name_no_ext = os.path.splitext(filename)[0]
        for ext in ['.mp3', '.ogg', '.wav']:
            path = os.path.join(base_dir, name_no_ext + ext)
            if os.path.exists(path) and not path.endswith('.placeholder'):
                return path
                
        return None

    def _can_play_sfx(self, event_type: str) -> bool:
        """Check if SFX can be played (cooldown check)"""
        if event_type not in self.sfx_cooldowns:
            return True

        time_since_last = time.time() - self.sfx_cooldowns[event_type]
        return time_since_last >= self.min_cooldown

    def toggle_mute(self):
        """Toggle master mute"""
        self.is_muted = not self.is_muted
        self._update_session_state()

        if self.is_muted:
            self.stop_music()
        else:
            # Resume current music if there was any
            if self.current_music:
                self.play_music(self.current_music)

    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)"""
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_session_state()

    def set_music_volume(self, volume: float):
        """Set music volume (0.0 to 1.0)"""
        self.music_volume = max(0.0, min(1.0, volume))
        self._update_session_state()

    def set_sfx_volume(self, volume: float):
        """Set SFX volume (0.0 to 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, volume))
        self._update_session_state()

    def play_sfx(self, event_type: str, force: bool = False):
        """
        Play a sound effect based on event type
        Args:
            event_type: Type of event (e.g., 'gold_received', 'combat_start')
            force: If True, ignore cooldown and mute settings
        """
        if not force and (self.is_muted or event_type not in self.SFX_MAP):
            return

        # Check cooldown
        if not force and not self._can_play_sfx(event_type):
            return

        filename = self.SFX_MAP[event_type]
        audio_path = self._get_audio_path(filename, "sfx")

        if audio_path:
            try:
                # Calculate effective volume
                effective_volume = self.sfx_volume * self.master_volume

                # Try multiple methods for audio playback in Streamlit
                audio_b64 = self._get_base64_audio(audio_path)
                if audio_b64:
                    # Determine mime type
                    mime_type = "audio/mp3"
                    if audio_path.endswith(".ogg"):
                        mime_type = "audio/ogg"
                    elif audio_path.endswith(".wav"):
                        mime_type = "audio/wav"

                    # Method 1: HTML5 audio with JavaScript
                    audio_html = f"""
                    <div id="audio-container-{event_type}" style="display: none;">
                        <audio id="audio-{event_type}" preload="auto" volume="{effective_volume}">
                            <source src="data:{mime_type};base64,{audio_b64}" type="{mime_type}">
                        </audio>
                    </div>
                    <script>
                        (function() {{
                            var audio = document.getElementById('audio-{event_type}');
                            if (audio) {{
                                audio.volume = {effective_volume};
                                audio.currentTime = 0;
                                var playPromise = audio.play();
                                if (playPromise !== undefined) {{
                                    playPromise.then(function() {{
                                        console.log('SFX {event_type} started');
                                    }}).catch(function(error) {{
                                        console.log('SFX {event_type} failed:', error);
                                    }});
                                }}
                            }}
                        }})();
                    </script>
                    """
                    st.components.v1.html(audio_html, height=0)

                    # Update cooldown
                    self.sfx_cooldowns[event_type] = time.time()

                    # Track recent event
                    self.recent_events.append(AudioEvent(event_type, time.time(), 2))
                    # Keep only recent events
                    self.recent_events = [e for e in self.recent_events
                                        if time.time() - e.timestamp < 30]  # 30 seconds

                    print(f"[AUDIO] Played SFX: {event_type}")

            except Exception as e:
                print(f"[AUDIO] Error playing SFX {event_type}: {e}")

    def play_music(self, music_type: str):
        """
        Play background music
        Args:
            music_type: Type of music (e.g., 'calm_ambient', 'battle_low')
        """
        if self.is_muted or music_type not in self.MUSIC_MAP:
            return

        # Don't restart if already playing
        if self.current_music == music_type:
            return

        # Stop current music first
        self.stop_music()

        filename = self.MUSIC_MAP[music_type]
        audio_path = self._get_audio_path(filename, "music")

        if audio_path:
            try:
                effective_volume = self.music_volume * self.master_volume

                # Create looping background music
                audio_b64 = self._get_base64_audio(audio_path)
                
                # Determine mime type
                mime_type = "audio/mp3"
                if audio_path.endswith(".ogg"):
                    mime_type = "audio/ogg"
                elif audio_path.endswith(".wav"):
                    mime_type = "audio/wav"

                music_html = f"""
                <audio id="bgmusic" autoplay loop style="display: none;" volume="{effective_volume}">
                    <source src="data:{mime_type};base64,{audio_b64}" type="{mime_type}">
                </audio>
                <script>
                    // Set volume after load
                    document.getElementById('bgmusic').volume = {effective_volume};
                    document.getElementById('bgmusic').play();
                </script>
                """
                st.components.v1.html(music_html, height=0)

                self.current_music = music_type
                print(f"[AUDIO] Started music: {music_type}")

            except Exception as e:
                print(f"[AUDIO] Error playing music {music_type}: {e}")

    def stop_music(self):
        """Stop current background music"""
        if self.current_music:
            try:
                stop_html = """
                <script>
                    var bgmusic = document.getElementById('bgmusic');
                    if (bgmusic) {
                        bgmusic.pause();
                        bgmusic.currentTime = 0;
                    }
                </script>
                """
                st.components.v1.html(stop_html, height=0)
                print(f"[AUDIO] Stopped music: {self.current_music}")
            except Exception as e:
                print(f"[AUDIO] Error stopping music: {e}")

        self.current_music = None

    def _get_base64_audio(self, file_path: str) -> str:
        """Convert audio file to base64 for HTML playback"""
        try:
            import base64
            with open(file_path, "rb") as audio_file:
                audio_data = audio_file.read()
                return base64.b64encode(audio_data).decode()
        except Exception as e:
            print(f"[AUDIO] Error encoding audio file {file_path}: {e}")
            return ""

    def process_audio_context(self, audio_context: List[str], music_context: Optional[str] = None):
        """
        Process audio context from LLM response
        Args:
            audio_context: List of SFX event types
            music_context: Background music type (optional)
        """
        if self.is_muted:
            return

        # Handle music first (lower priority)
        if music_context and music_context != self.current_music:
            self.play_music(music_context)

        # Handle SFX events
        for event in audio_context:
            if event in self.SFX_MAP:
                self.play_sfx(event)

    def get_audio_controls_html(self) -> str:
        """Get HTML for audio control panel"""
        mute_icon = "🔇" if self.is_muted else "🔊"

        controls_html = f"""
        <div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;
                    background: rgba(0,0,0,0.8); border: 1px solid #5a3921;
                    border-radius: 10px; padding: 10px; font-size: 14px; color: #e8d8c3;">

            <div style="display: flex; align-items: center; gap: 10px;">
                <button onclick="toggleMute()" style="background: none; border: none; color: #e8d8c3; font-size: 18px; cursor: pointer;">
                    {mute_icon}
                </button>

                <div style="display: flex; flex-direction: column; gap: 5px;">
                    <div>
                        <label style="font-size: 10px; color: #b8860b;">Master</label>
                        <input type="range" min="0" max="1" step="0.1" value="{self.master_volume}"
                               onchange="setMasterVolume(this.value)" style="width: 60px;">
                    </div>
                    <div>
                        <label style="font-size: 10px; color: #b8860b;">Music</label>
                        <input type="range" min="0" max="1" step="0.1" value="{self.music_volume}"
                               onchange="setMusicVolume(this.value)" style="width: 60px;">
                    </div>
                    <div>
                        <label style="font-size: 10px; color: #b8860b;">SFX</label>
                        <input type="range" min="0" max="1" step="0.1" value="{self.sfx_volume}"
                               onchange="setSFXVolume(this.value)" style="width: 60px;">
                    </div>
                </div>
            </div>
        </div>

        <script>
        function toggleMute() {{
            // This will trigger a Streamlit rerun to update state
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                data: {{action: 'toggle_mute'}}
            }}, '*');
        }}

        function setMasterVolume(value) {{
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                data: {{action: 'set_master_volume', value: parseFloat(value)}}
            }}, '*');
        }}

        function setMusicVolume(value) {{
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                data: {{action: 'set_music_volume', value: parseFloat(value)}}
            }}, '*');
        }}

        function setSFXVolume(value) {{
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                data: {{action: 'set_sfx_volume', value: parseFloat(value)}}
            }}, '*');
        }}
        </script>
        """

        return controls_html

# Global audio manager instance
_audio_manager = None

def get_audio_manager() -> AudioManager:
    """Get singleton audio manager instance"""
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioManager()
    return _audio_manager
