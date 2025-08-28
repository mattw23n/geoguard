import os
# Hybrid search (BM25 + vector)
def retrieve_feature_clauses(feature):
    # Placeholder for clause-level retrieval
        # For MVP: split description into sentences
        desc = feature.get("feature_description", "")
        return [s.strip() for s in desc.split('.') if s.strip()]

def retrieve_regulation_sections(feature):
    # Placeholder for regulation retrieval
        # For MVP: return all regulation snippets
        reg_dir = "data/regulations"
        sections = []
        for fname in os.listdir(reg_dir):
            with open(os.path.join(reg_dir, fname), "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        sections.append(line.strip())
        return sections[:5]  # top-5 for demo
