import json
import os

def generate_markdown():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.join(script_dir, '../../')
    
    source_path = os.path.join(root_dir, "story_packs/episode_1/strajer_source.json")
    output_path = os.path.join(root_dir, "docs/strajer_draculesti_ep1_flow.md")
    
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        return

    lines = []
    lines.append("# Străjer Drăculești - Episodul 1: Umbra Carului Negru")
    lines.append("")
    lines.append("## Flux Narativ (Hash Cache Keys)")
    lines.append("Acest document prezintă toate ramurile narative pre-generate pentru clasa Străjer în Episodul 1.")
    lines.append("")
    
    # Group by "Start Nodes" vs "Follow-up Nodes" is hard without graph traversal.
    # I'll list them alphabetically or try to group them logically?
    # Alphabetical is easiest for a flat list, but a graph walk is better.
    # Let's try to build a simple graph representation.
    
    # Find root nodes (those not suggested by anyone else?)
    # Actually, just listing them as expandable details might be cleaner.
    
    for key, node in data.items():
        narrative = node.get("narrative", "").replace("\n", " ")
        suggestions = node.get("suggestions", [])
        
        lines.append(f"### 🔹 Acțiune: `{key}`")
        lines.append(f"**Narativ:** {narrative}")
        lines.append("")
        
        if suggestions:
            lines.append("**Sugestii Următoare:**")
            for sug in suggestions:
                # Check if suggestion exists as a key
                status = "✅ (Definit)" if sug in data else "❌ (Lipsă - Fallback)"
                lines.append(f"- `{sug}` {status}")
        else:
            lines.append("*Final de ramură sau nod terminal.*")
            
        if node.get("win_condition"):
            lines.append("\n🏆 **Condiție de Victorie**")
        if node.get("game_over"):
            lines.append("\n💀 **Game Over**")
            
        lines.append("\n---")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    
    print(f"Documentation generated at {output_path}")

if __name__ == "__main__":
    generate_markdown()
