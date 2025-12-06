import json
import os

def validate_and_graph(source_path, output_mermaid_path):
    print(f"Loading {source_path}...")
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    # 1. Identify all reachable nodes and missing links
    # Root nodes are those that are not targets of any suggestion? 
    # Or we assume specific roots based on Campaign intro. 
    # For now, let's just check consistency of ALL nodes.
    
    defined_nodes = set(data.keys())
    referenced_nodes = set()
    missing_links = {} # source_node -> [missing_suggestions]
    
    graph_edges = [] # (from, to, label)

    for node_key, content in data.items():
        suggestions = content.get("suggestions", [])
        for sug in suggestions:
            referenced_nodes.add(sug)
            graph_edges.append((node_key, sug, sug))
            
            if sug not in defined_nodes:
                if node_key not in missing_links:
                    missing_links[node_key] = []
                missing_links[node_key].append(sug)

    # 2. Report Missing Links
    print("\n=== MISSING BRANCHES ===")
    if missing_links:
        count = 0
        for src, missing in missing_links.items():
            for m in missing:
                src_safe = src.encode('ascii', 'ignore').decode('ascii')
                m_safe = m.encode('ascii', 'ignore').decode('ascii')
                print(f"[MISSING] From '{src_safe}' -> Suggestion '{m_safe}' is undefined.")
                count += 1
        print(f"Total missing nodes: {count}")
    else:
        print("No missing branches found! Graph is fully connected.")

    # 3. Generate Mermaid
    print(f"\nGenerating Mermaid diagram to {output_mermaid_path}...")
    mermaid_lines = ["graph TD"]
    mermaid_lines.append("classDef default fill:#1a0f0b,stroke:#d4af37,color:#e8d8c3;")
    mermaid_lines.append("classDef missing fill:#ff0000,stroke:#333,color:#fff;")
    
    # Add nodes
    for node_key in defined_nodes:
        # Escape quotes
        safe_id = abs(hash(node_key))
        short_desc = data[node_key].get("narrative", "")[:30].replace('"', "'") + "..."
        mermaid_lines.append(f'    {safe_id}["{node_key}<br/>{short_desc}"]')

    # Add missing nodes
    all_missing = set()
    for m_list in missing_links.values():
        all_missing.update(m_list)
        
    for m_node in all_missing:
        safe_id = abs(hash(m_node))
        mermaid_lines.append(f'    {safe_id}["{m_node} (MISSING)"]:::missing')

    # Add edges
    for src, tgt, label in graph_edges:
        src_id = abs(hash(src))
        tgt_id = abs(hash(tgt))
        # shorten label if too long
        short_label = (label[:20] + "..") if len(label) > 20 else label
        mermaid_lines.append(f'    {src_id} -->|"{short_label}"| {tgt_id}')

    with open(output_mermaid_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(mermaid_lines))
    print("Done.")

if __name__ == "__main__":
    validate_and_graph(
        "story_packs/episode_1/strajer_source.json",
        "docs/strajer_flow_diagram.mermaid"
    )
