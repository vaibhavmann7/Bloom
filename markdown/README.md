# Neo4j Bloom Perspective Automation

## ✅ Working Solution

Successfully automated Neo4j Bloom Perspective generation using both LLM-based and programmatic approaches.

## Key Findings

### Critical Fields for Bloom Import

After extensive testing and comparison with working examples, these fields are **REQUIRED**:

1. **Relationships must have `size` field**: `"size": 1` in `relationshipTypes`
2. **Icon field**: Use `"icon": "no-icon"` (UUID icons are not required)
3. **Complete schema in `labels` dict**: All node labels must be defined at root level
4. **Metadata structure**: Must include `pathSegments` (can be empty `[]`) and `indexes`
5. **Template structure**: Use `cypher` (not `query`), `text` (not `description`)
6. **All optional fields**: `sceneActions`, `hiddenRelationshipTypes`, `maxLimitToastMsgEnabled`, `parentPerspectiveId`

### Two Working Approaches

#### 1. LLM-Based Generation (`perspective_generator.py`)

- Uses Gemini 2.5 Pro to generate perspectives
- Loads schema from Neo4j (cached locally)
- Uses example files for few-shot learning
- Automatically hydrates with required fields
- **Best for**: Complex perspectives with search phrases and business logic

#### 2. Programmatic Generation (`generate_new_perspectives.py`)

- Direct JSON construction without LLM
- Full control over structure
- Simpler and faster
- **Best for**: Focused perspectives with specific categories

## Project Structure

```
bloom_automation/
├── .env                                    # Neo4j + Gemini credentials
├── requirements.txt                        # Python dependencies
├── src/
│   ├── perspective_generator.py            # LLM-based generator (Gemini)
│   ├── generate_new_perspectives.py        # Programmatic generator
│   ├── schema_fetcher.py                   # Schema fetcher (simple format)
│   ├── schema_fetcher_full.py              # Schema fetcher (with constraints/indexes)
│   ├── prompts.py                          # LLM system prompts
│   ├── schema.json                         # Cached schema (simple)
│   └── schema_full.json                    # Cached schema (full)
├── example/
│   ├── Customer Purchase Journey.json      # Working example for few-shot learning
│   ├── Logistics & Delivery.json
│   ├── Product Performance.json
│   └── Review Network.json
└── output/
    ├── Customer_360_View.json              # LLM-generated example
    ├── Order_Fulfillment__Logistics.json   # LLM-generated example
    └── Seller_Performance.json             # Programmatically generated ✅
```

## Setup & Installation

1.  **Prerequisites**:

    - Python 3.8+
    - Neo4j Database (running)

2.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**:
    Create a `.env` file in the `bloom_automation` folder with the following variables:
    ```env
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USERNAME=neo4j
    NEO4J_PASSWORD=your_password
    GEMINI_API_KEY=your_gemini_api_key
    GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    GEMINI_MODEL=gemini-2.0-flash
    ```

## Usage

### LLM-Based Generation (Recommended)

Generates 4-5 distinct, "locked-down" perspectives based on your schema.

```bash
python src/perspective_generator.py
```

**Output**: Multiple JSON files in `output/` folder (e.g., `Customer_360_View.json`, `Risk_Analysis.json`).

### Programmatic Generation

Edit `src/generate_new_perspectives.py` to define:

- Categories (nodes to show)
- Relationships (connections to show)
- Hidden relationships (to hide from view)

Then run:

```bash
python src/generate_new_perspectives.py
```

### Schema Fetching

```bash
# Simple schema (labels, properties, relationships)
python src/schema_fetcher.py

# Full schema (with constraints and indexes)
python src/schema_fetcher_full.py
```

## Validation Checklist

Before importing to Bloom, verify JSON has:

- [x] `size: 1` in all `relationshipTypes` items
- [x] `icon: "no-icon"` in all `categories`
- [x] Root-level `labels` dictionary with ALL node types
- [x] `metadata.pathSegments` (can be empty array)
- [x] `metadata.indexes` with proper structure
- [x] `templates` use `cypher` and `text` keys
- [x] `sceneActions` array (can be empty)
- [x] `hiddenRelationshipTypes` array
- [x] All timestamps are consistent

## Success Metrics

- ✅ `Seller_Performance.json` imports without errors
- ✅ Schema caching eliminates connection issues
- ✅ Both programmatic and LLM approaches work
- ✅ Proper field structure matches Bloom requirements
