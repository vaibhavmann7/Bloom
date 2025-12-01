import os
import json
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SCHEMA_CACHE_PATH = Path(__file__).parent / "schema.json"

def fetch_schema(use_cache=True):
    """
    Connects to the Neo4j database using credentials from environment variables
    and fetches the schema (labels, relationships, and properties).
    
    If use_cache is True and schema.json exists, loads from file instead.
    """
    if use_cache and SCHEMA_CACHE_PATH.exists():
        print(f"   📂 Loading schema from cache: {SCHEMA_CACHE_PATH}")
        try:
            with open(SCHEMA_CACHE_PATH, "r", encoding="utf-8") as f:
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
        "labels": {},
        "relationships": []
    }

    try:
        print(f"   Connecting to {uri}...")
        driver.verify_connectivity()
        print("   ✅ Connection established.")

        with driver.session() as session:
            # 1. Fetch Node Labels and Properties
            # db.schema.nodeTypeProperties() returns nodeType, propertyName, propertyTypes, mandatory
            print("   Fetching node properties...")
            result_props = session.run("CALL db.schema.nodeTypeProperties()")
            
            for record in result_props:
                node_type = record["nodeType"]
                # nodeType is usually ":Label" or ":Label1:Label2"
                # We'll simplisticly take the first label if multiple, removing the leading colon
                labels = [l for l in node_type.split(":") if l]
                
                for label in labels:
                    if label not in schema_data["labels"]:
                        schema_data["labels"][label] = []
                    
                    prop_name = record["propertyName"]
                    prop_type = record["propertyTypes"] # This is a list of types
                    
                    if prop_name:
                        schema_data["labels"][label].append({
                            "name": prop_name,
                            "type": prop_type[0] if prop_type else "String" # Default to String
                        })

            # 2. Fetch Relationships
            # db.schema.visualization() returns nodes and relationships in the schema
            print("   Fetching relationships...")
            result_viz = session.run("CALL db.schema.visualization()")
            
            # The result contains a single record with 'nodes' and 'relationships' lists
            # But these are schema objects, not data nodes.
            # Actually, db.schema.visualization returns graph objects.
            # A better way for pure schema might be db.schema.relTypeProperties() or just parsing visualization.
            
            # Let's use a Cypher query to get distinct relationships with start/end labels
            # This is more reliable for "What connects to what"
            rel_query = """
            MATCH (a)-[r]->(b)
            RETURN DISTINCT labels(a) AS start_node, type(r) AS rel_type, labels(b) AS end_node
            """
            result_rels = session.run(rel_query)
            
            for record in result_rels:
                start_labels = record["start_node"]
                rel_type = record["rel_type"]
                end_labels = record["end_node"]
                
                # Handle multiple labels by creating a connection for each combination or just the first one
                # For simplicity, let's assume primary labels or take all combinations
                for start in start_labels:
                    for end in end_labels:
                        # Avoid duplicates if possible, but list is fine
                        rel_entry = {
                            "start": start,
                            "type": rel_type,
                            "end": end
                        }
                        if rel_entry not in schema_data["relationships"]:
                            schema_data["relationships"].append(rel_entry)
        
        # Save to cache
        try:
            with open(SCHEMA_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(schema_data, f, indent=2)
            print(f"   💾 Schema saved to cache: {SCHEMA_CACHE_PATH}")
        except Exception as e:
            print(f"   ⚠️ Failed to save cache: {e}")

    except Exception as e:
        print(f"❌ Error fetching schema: {e}")
        # Re-raise to let the caller know it failed
        raise e
    finally:
        driver.close()

    return schema_data

if __name__ == "__main__":
    # Test the fetcher
    try:
        schema = fetch_schema()
        print("\n--- Schema Fetched Successfully ---")
        print(f"Labels found: {list(schema['labels'].keys())}")
        print(f"Relationships found: {len(schema['relationships'])}")
        # print(json.dumps(schema, indent=2)) 
    except Exception as e:
        print(f"Failed: {e}")
