
import os
import sys
import json
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())

load_dotenv(override=True)

from database import Database
from models import GameState

# Setup DB
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("❌ Missing DB credentials")
    sys.exit(1)

db = Database(SUPABASE_URL, SUPABASE_ANON_KEY)

# Target Session
TARGET_SESSION_ID = "6bfadc6a-14eb-4f8e-8081-652f55612760_d7efb77d28d6"

print(f"🔍 Inspecting session: {TARGET_SESSION_ID}")

try:
    # 1. Get raw data first to check size
    response = db.client.table('game_sessions').select('*').eq('session_id', TARGET_SESSION_ID).execute()
    
    if not response.data:
        print("❌ Session not found!")
        sys.exit(1)
        
    session_data = response.data[0]
    
    story_data = session_data.get('story_data', [])
    inventory_data = session_data.get('inventory', [])
    
    print(f"✅ Session found.")
    print(f"Story length: {len(story_data)} messages")
    print(f"Inventory items: {len(inventory_data)}")
    
    # Calculate size of story
    story_json = json.dumps(story_data)
    size_mb = len(story_json) / (1024 * 1024)
    print(f"Story JSON size: {size_mb:.2f} MB")
    
    # Check for images in story
    image_count = 0
    total_image_size = 0
    for msg in story_data:
        if msg.get('image'):
            image_count += 1
            # Image might be bytes or base64 string or url
            img = msg['image']
            if isinstance(img, str):
                total_image_size += len(img)
            elif isinstance(img, bytes): # unlikely in JSON loaded from DB unless decoded
                total_image_size += len(img)
                
    print(f"Messages with images: {image_count}")
    print(f"Approx image data size: {total_image_size / (1024*1024):.2f} MB")
    
    if size_mb > 50:
        print("⚠️ WARNING: Story size is very large! This might cause Streamlit session issues.")

    # 2. Try to load as GameState to check validation
    print("\nAttempting to load as GameState...")
    game_state = db.load_game_session(TARGET_SESSION_ID)
    
    if game_state:
        print("✅ GameState loaded successfully (Pydantic validation passed)")
    else:
        print("❌ Failed to load GameState")

except Exception as e:
    print(f"❌ Error during inspection: {e}")
    import traceback
    traceback.print_exc()
