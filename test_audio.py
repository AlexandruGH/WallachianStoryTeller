#!/usr/bin/env python3
"""
Simple test script to verify audio functionality
"""

from audio_manager import get_audio_manager

def test_audio():
    """Test audio playback"""
    print("Testing Wallachia Audio System...")
    print("=" * 50)

    # Get audio manager
    audio_mgr = get_audio_manager()

    print(f"Audio Manager initialized:")
    print(f"  - Muted: {audio_mgr.is_muted}")
    print(f"  - Master Volume: {audio_mgr.master_volume}")
    print(f"  - Music Volume: {audio_mgr.music_volume}")
    print(f"  - SFX Volume: {audio_mgr.sfx_volume}")
    print()

    # Test SFX playback
    print("Testing Sound Effects...")
    sfx_tests = [
        "gold_received",  # Should play coins.mp3
        "quest_new",      # Should play quest_new.mp3
        "decision_important",  # Should play decision_important.mp3
        "door_open"       # Should play door_open.mp3
    ]

    for sfx in sfx_tests:
        print(f"  Playing SFX: {sfx}")
        audio_mgr.play_sfx(sfx, force=True)  # Force play to ignore cooldowns
        # Small delay between sounds
        import time
        time.sleep(0.5)

    print()

    # Test music playback
    print("Testing Background Music...")
    print("  Starting calm ambient music...")
    audio_mgr.play_music("calm_ambient")

    # Let music play for a few seconds
    time.sleep(3)

    print("  Stopping music...")
    audio_mgr.stop_music()

    print()
    print("Audio test completed!")
    print("If you heard sounds, the audio system is working correctly.")
    print("Note: Audio may not play in all environments (headless servers, etc.)")

if __name__ == "__main__":
    test_audio()
