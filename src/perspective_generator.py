import os
import json
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Import our local modules
from schema_fetcher import fetch_schema
from prompts import BLOOM_PERSPECTIVE_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Load environment variables
load_dotenv()


def get_llm_client():
    """Configures and returns the OpenAI client for Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    base_url = os.getenv("GEMINI_BASE_URL")

    if not api_key or not base_url:
        raise ValueError("Missing GEMINI_API_KEY or GEMINI_BASE_URL in .env")

    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )


def load_example_perspective():
    """Loads the Customer Purchase Journey.json as a few-shot example."""
    # Go up one level from src to bloom_automation, then into example
    example_path = Path(__file__).parent.parent / \
        "example" / "Customer Purchase Journey.json"
    try:
        with open(example_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ Warning: Could not load example file: {e}")
        return ""


def clean_label(label):
    """Removes backticks from label names. Handles lists by taking the first element."""
    if isinstance(label, list):
        if not label:
            return ""
        return clean_label(label[0])
    return str(label).replace("`", "")


def generate_metadata(schema):
    """Generates the required metadata section (pathSegments, indexes) from the schema."""
    path_segments = []
    indexes = []

    # Generate Path Segments from relationships
    for rel in schema["relationships"]:
        path_segments.append({
            "source": clean_label(rel["start"]),
            "relationshipType": clean_label(rel["type"]),
            "target": clean_label(rel["end"])
        })

    # Generate Indexes from labels and properties
    for label, props in schema["labels"].items():
        clean_lbl = clean_label(label)
        prop_keys = []
        for p in props:
            prop_keys.append({
                "key": p["name"],
                "metadataProp": False  # Default
            })

        indexes.append({
            "label": clean_lbl,
            "type": "native",
            "propertyKeys": prop_keys
        })

    return {
        "pathSegments": path_segments,
        "indexes": indexes
    }


def hydrate_perspective(raw_perspective, schema, all_db_rels):
    """
    Fills in missing default fields and fixes structure to match Bloom requirements.
    Applies the "Lock Down" logic by hiding unused relationships.
    """
    timestamp = int(time.time() * 1000)

    # 1. Top Level Fields
    if "id" not in raw_perspective:
        raw_perspective["id"] = str(uuid.uuid4())
    raw_perspective["createdAt"] = timestamp
    raw_perspective["lastEditedAt"] = timestamp
    raw_perspective["version"] = "2.21.0"
    raw_perspective["type"] = "STANDARD_PERSPECTIVE"

    # --- THE LOCK DOWN FIX ---
    # Ensure hideUncategorisedData is False (as per working examples)
    raw_perspective["hideUncategorisedData"] = False
    raw_perspective["maxLimitToastMsgEnabled"] = False
    raw_perspective["parentPerspectiveId"] = None

    # Calculate Hidden Relationships
    # 1. Identify relationships used in this perspective
    used_rels = set()
    for r in raw_perspective.get("relationshipTypes", []):
        if isinstance(r, dict):
            used_rels.add(clean_label(r.get("name", "")))
        else:
            used_rels.add(clean_label(r))

    # 2. Subtract used from ALL known DB relationships
    hidden_rels = list(all_db_rels - used_rels)
    raw_perspective["hiddenRelationshipTypes"] = hidden_rels
    # -------------------------

    # 2. Metadata (CRITICAL)
    raw_perspective["metadata"] = generate_metadata(schema)

    # 3. Palette
    if "palette" not in raw_perspective:
        raw_perspective["palette"] = {
            "colors": [
                "#FFE081", "#C990C0", "#F79767", "#57C7E3", "#F16667",
                "#D9C8AE", "#8DCC93", "#ECB5C9", "#4C8EDA", "#FFC454",
                "#DA7194", "#569480", "#959AA1", "#D9D9D9"
            ],
            "currentIndex": 0
        }

    # 4. Categories
    # Bloom likes integer IDs for categories
    for idx, cat in enumerate(raw_perspective.get("categories", [])):
        cat["id"] = idx + 1  # 1-based index
        cat["createdAt"] = timestamp
        cat["lastEditedAt"] = timestamp
        cat["size"] = 1
        cat["icon"] = "no-icon"  # Use "no-icon" - this works fine
        cat["styleRules"] = []

        # Missing fields identified by comparison
        cat["textSize"] = 1
        cat["textAlign"] = "top"
        cat["captionKeys"] = []

        # Clean labels
        if "labels" in cat:
            cat["labels"] = [clean_label(l) for l in cat["labels"]]

        # Ensure properties structure
        if "properties" in cat:
            new_props = []
            for p in cat["properties"]:
                if isinstance(p, str):
                    new_props.append(
                        {"name": p, "exclude": False, "dataType": "string"})
                else:
                    new_props.append(p)
            cat["properties"] = new_props

        # Captions
        if "captions" not in cat or not cat["captions"]:
            key = cat["properties"][0]["name"] if cat.get("properties") else (
                cat["labels"][0] if cat.get("labels") else "id")
            cat["captions"] = [{
                "key": key,
                "type": "property" if cat.get("properties") else "label",
                "isCaption": True,
                "inTooltip": True,
                "styles": [],
                "isGdsData": False
            }]
        else:
            # Ensure styles and isGdsData exist
            for cap in cat["captions"]:
                if "styles" not in cap:
                    cap["styles"] = []
                if "isGdsData" not in cap and cap.get("type") == "property":
                    cap["isGdsData"] = False

    # 5. Relationship Types
    for rel in raw_perspective.get("relationshipTypes", []):
        rel["id"] = clean_label(rel["name"])
        rel["name"] = clean_label(rel["name"])
        if "properties" not in rel:
            rel["properties"] = []
        if "styleRules" not in rel:
            rel["styleRules"] = []

        # CRITICAL: size field is required
        rel["size"] = 1
        # Missing fields for relationships
        rel["textSize"] = 1
        rel["textAlign"] = "top"
        rel["captionKeys"] = []

        if "captions" not in rel:
            rel["captions"] = [{
                "key": rel["name"],
                "type": "relationship",
                "isCaption": True,
                "inTooltip": True,
                "styles": []
            }]

    # 6. Templates (Search Phrases)
    for tmpl in raw_perspective.get("templates", []):
        if "id" not in tmpl:
            tmpl["id"] = f"tmpl:{timestamp + uuid.uuid4().int % 100000}"
        if "createdAt" not in tmpl:
            tmpl["createdAt"] = timestamp

        # Fix keys to match example
        if "query" in tmpl and "cypher" not in tmpl:
            tmpl["cypher"] = tmpl.pop("query")
        if "description" in tmpl and "text" not in tmpl:
            # Bloom uses 'text' for description/display
            tmpl["text"] = tmpl.pop("description")
        elif "text" not in tmpl:
            tmpl["text"] = tmpl.get("name", "Search Phrase")

        # Add missing template fields
        tmpl["isUpdateQuery"] = None
        tmpl["isWriteTransactionChecked"] = None
        tmpl["hasCypherErrors"] = False

        # Ensure params have correct fields
        if "params" in tmpl:
            for p in tmpl["params"]:
                if "collapsed" not in p:
                    p["collapsed"] = False
                if "suggestionBoolean" not in p:
                    p["suggestionBoolean"] = False
                if "suggestionLabel" in p:
                    p["suggestionLabel"] = clean_label(p["suggestionLabel"])
                if "cypher" not in p:
                    p["cypher"] = None

    # 7. Labels Dictionary (Root Level)
    # Ensure keys are clean
    if "labels" in raw_perspective:
        new_labels = {}
        for k, v in raw_perspective["labels"].items():
            clean_k = clean_label(k)
            new_labels[clean_k] = v
            for prop in v:
                prop["type"] = clean_k  # Ensure type matches key
        raw_perspective["labels"] = new_labels

    # 8. Ensure other top-level fields
    if "sceneActions" not in raw_perspective:
        raw_perspective["sceneActions"] = []
    if "hiddenRelationshipTypes" not in raw_perspective:
        raw_perspective["hiddenRelationshipTypes"] = []
    if "hideUncategorisedData" not in raw_perspective:
        raw_perspective["hideUncategorisedData"] = False

    return raw_perspective


def main():
    print("🚀 Starting Bloom Perspective Generator...")

    # 1. Fetch Schema
    print("📊 Fetching schema from Neo4j...")
    try:
        schema = fetch_schema()
        print(
            f"   Found {len(schema['labels'])} labels and {len(schema['relationships'])} relationships.")
    except Exception as e:
        print(f"❌ Failed to fetch schema: {e}")
        return

    # 2. Prepare Prompt with Example
    schema_json = json.dumps(schema, indent=2)
    example_json = load_example_perspective()

    prompt_content = USER_PROMPT_TEMPLATE.format(schema_json=schema_json)

    messages = [
        {"role": "system", "content": BLOOM_PERSPECTIVE_SYSTEM_PROMPT}
    ]

    if example_json:
        print("📚 Loaded 'Customer Purchase Journey.json' as a few-shot example.")
        messages.append(
            {"role": "user", "content": "Here is an example of a perfect Neo4j Bloom Perspective JSON:"})
        messages.append({"role": "user", "content": example_json})

    messages.append({"role": "user", "content": prompt_content})

    # 3. Call LLM
    print("🤖 Asking Gemini to generate perspectives (this may take a moment)...")
    client = get_llm_client()
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2
        )

        content = response.choices[0].message.content

        # Clean up potential markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Parse JSON
        perspectives_data = json.loads(content)

        # Ensure it's a list
        if isinstance(perspectives_data, dict):
            perspectives_data = [perspectives_data]

    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse LLM response as JSON: {e}")
        print(f"Response was: {content[:500]}...")
        return
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return

    # 4. Hydrate and Save
    print(f"✨ Processing {len(perspectives_data)} perspectives...")

    # Extract ALL DB relationships from schema for the "Lock Down" logic
    all_db_rels = set(r["type"] for r in schema["relationships"])

    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    for i, p_data in enumerate(perspectives_data):
        # Pass schema AND all_db_rels to hydrate function
        final_perspective = hydrate_perspective(p_data, schema, all_db_rels)

        # Generate filename from perspective name
        safe_name = "".join([c for c in final_perspective["name"]
                            if c.isalnum() or c in (' ', '-', '_')]).strip()
        safe_name = safe_name.replace(" ", "_")
        output_path = output_dir / f"{safe_name}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            # Minify JSON to match Bloom's preferred format
            json.dump(final_perspective, f, separators=(',', ':'))

        print(f"✅ Saved: {output_path}")

    print("👉 You can now import these files into Neo4j Bloom.")


if __name__ == "__main__":
    main()
