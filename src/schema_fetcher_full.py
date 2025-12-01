import os
import json
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SCHEMA_FULL_PATH = Path(__file__).parent / "schema_full.json"

def fetch_schema_full(use_cache=True):
    """
    Connects to Neo4j and fetches the full schema using db.schema.visualization()
    Returns nodes and relationships with constraints and indexes metadata.
    
    If use_cache is True and schema_full.json exists, loads from file instead.
    """
    if use_cache and SCHEMA_FULL_PATH.exists():
        print(f"   📂 Loading full schema from cache: {SCHEMA_FULL_PATH}")
        try:
            with open(SCHEMA_FULL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"   ⚠️ Failed to load cache: {e}. Fetching live...")

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not all([uri, username, password]):
        raise ValueError("Missing Neo4j credentials in .env file")

    driver = GraphDatabase.driver(uri, auth=(username, password))

    schema_data = {
        "nodes": [],
        "relationships": []
    }

    try:
        print(f"   Connecting to {uri}...")
        driver.verify_connectivity()
        print("   ✅ Connection established.")

        with driver.session() as session:
            # Fetch schema visualization
            print("   Fetching schema visualization...")
            result = session.run("CALL db.schema.visualization()")
            
            for record in result:
                # Process nodes
                for node in record["nodes"]:
                    node_data = {
                        "identity": node.id,
                        "labels": list(node.labels),
                        "properties": dict(node),  # Node properties from visualization
                        "elementId": node.element_id
                    }
                    schema_data["nodes"].append(node_data)
                
                # Process relationships
                for rel in record["relationships"]:
                    rel_data = {
                        "identity": rel.id,
                        "start": rel.start_node.id,
                        "end": rel.end_node.id,
                        "type": rel.type,
                        "properties": dict(rel),
                        "elementId": rel.element_id,
                        "startNodeElementId": rel.start_node.element_id,
                        "endNodeElementId": rel.end_node.element_id
                    }
                    schema_data["relationships"].append(rel_data)
        
        # Save to cache
        try:
            with open(SCHEMA_FULL_PATH, "w", encoding="utf-8") as f:
                json.dump(schema_data, f, indent=2)
            print(f"   💾 Full schema saved to cache: {SCHEMA_FULL_PATH}")
        except Exception as e:
            print(f"   ⚠️ Failed to save cache: {e}")

    except Exception as e:
        print(f"❌ Error fetching schema: {e}")
        raise e
    finally:
        driver.close()

    return schema_data

if __name__ == "__main__":
    print("🔍 Fetching full Neo4j schema...")
    
    try:
        schema = fetch_schema_full(use_cache=False)
        
        print(f"\n✅ Schema fetched successfully!")
        print(f"   Nodes: {len(schema['nodes'])}")
        print(f"   Relationships: {len(schema['relationships'])}")
        
        # Display nodes
        print("\n📋 Nodes:")
        for node in schema['nodes']:
            labels = ', '.join(node['labels'])
            name = node['properties'].get('name', labels)
            indexes = node['properties'].get('indexes', [])
            constraints = node['properties'].get('constraints', [])
            print(f"   - {name}")
            if indexes:
                print(f"      Indexes: {', '.join(indexes)}")
            if constraints:
                print(f"      Constraints: {len(constraints)}")
        
        # Display relationships
        print("\n🔗 Relationships:")
        for rel in schema['relationships']:
            print(f"   - {rel['type']}")
        
        print(f"\n💾 Schema cached in: {SCHEMA_FULL_PATH}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
