import json

source_path = "story_packs/episode_1/strajer_source.json"

def inject_items():
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. Add Platoșă to a Victory Node
        if "Du-l la Căpitan (Final Bun)." in data:
            node = data["Du-l la Căpitan (Final Bun)."]
            # Add Platoșă if not present
            has_platosa = any(i['name'] == "Platoșă de Străjer" for i in node.get("items_gained", []))
            if not has_platosa:
                if "items_gained" not in node:
                    node["items_gained"] = []
                node["items_gained"].append({
                    "name": "Platoșă de Străjer",
                    "type": "diverse",
                    "value": 20,
                    "quantity": 1
                })
                print("Added Platoșă to 'Du-l la Căpitan (Final Bun).'")

        # 2. Add specific Archery/Skill context if needed
        # (The rewritten story already has 'Trage cu arcul', etc.)

        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully injected items.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inject_items()
