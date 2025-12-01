from elevenlabs.client import ElevenLabs
from elevenlabs import play

client = ElevenLabs(
    api_key="sk_118120ce30f5d47ca2a919d2ac07099a05da82cc45240627"
)

audio = client.text_to_speech.convert(
    text="The first move is what sets everything in motion.",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

play(audio)