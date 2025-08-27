# Glossary expansion, NER, clause splitting
import yaml
import spacy

def load_glossary(path="data/terminology.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def expand_glossary(text, glossary):
    for abbr, full in glossary.items():
        text = text.replace(abbr, f"{abbr} ({full})")
    return text

def tag_geography(text):
    geo_entities = ["EU", "EEA", "France", "CA", "FL", "UT", "KR", "US", "BR"]
    found = [g for g in geo_entities if g in text]
    return found

def normalize_feature(feature):
    glossary = load_glossary()
    desc = feature.get("feature_description", "")
    desc_expanded = expand_glossary(desc, glossary)
    geo_tags = tag_geography(desc_expanded)
    feature["feature_description"] = desc_expanded
    feature["geo_tags"] = geo_tags
    return feature
