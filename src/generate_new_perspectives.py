import json
import uuid
import time
from pathlib import Path


def generate_bloom_perspective(name, categories_config, relationships_config, output_file, all_known_relationships=None, all_known_labels=None):
    timestamp = int(time.time() * 1000)

    # Calculate hidden relationships
    used_rels = [r["type"] for r in relationships_config]
    hidden_rels = []
    if all_known_relationships:
        hidden_rels = [
            r for r in all_known_relationships if r not in used_rels]

    # Base structure
    perspective = {
        "name": name,
        "version": "2.21.0",
        "id": str(uuid.uuid4()),
        "createdAt": timestamp,
        "lastEditedAt": timestamp,
        "type": "STANDARD_PERSPECTIVE",
        "hideUncategorisedData": False,
        "maxLimitToastMsgEnabled": False,
        "parentPerspectiveId": None,
        "categories": [],
        "labels": {},
        "relationshipTypes": [],
        "templates": [],
        "sceneActions": [],
        "hiddenRelationshipTypes": hidden_rels,
        "palette": {
            "colors": [
                "#FFE081", "#C990C0", "#F79767", "#57C7E3", "#F16667", "#D9C8AE",
                "#8DCC93", "#ECB5C9", "#4C8EDA", "#FFC454", "#DA7194", "#569480",
                "#959AA1", "#D9D9D9"
            ],
            "currentIndex": 0
        },
        "metadata": {
            "pathSegments": [],
            "indexes": []
        }
    }

    # Process Labels (Schema) - Populate with all known labels if provided
    if all_known_labels:
        for label, props in all_known_labels.items():
            perspective["labels"][label] = [
                {"propertyKey": p["name"], "type": label, "dataType": p["dataType"]} for p in props
            ]

    # Process Categories
    for i, cat_conf in enumerate(categories_config):
        label = cat_conf["label"]
        cat_name = cat_conf.get("name", label)
        color = cat_conf.get("color", "#CCCCCC")
        # List of {"name": "prop", "dataType": "string"}
        properties = cat_conf.get("properties", [])

        # Category Object
        category = {
            "id": i + 1,
            "name": cat_name,
            "labels": [label],
            "properties": [{"name": p["name"], "exclude": False, "dataType": p["dataType"]} for p in properties],
            "createdAt": timestamp,
            "lastEditedAt": timestamp,
            "color": color,
            "icon": "no-icon",  # You might want to map this to actual Bloom icon UUIDs if known
            "size": 1,
            "textSize": 1,
            "textAlign": "top",
            "captions": [],
            "captionKeys": [],
            "styleRules": []
        }

        # Add a default caption if properties exist
        if properties:
            category["captions"].append({
                "key": properties[0]["name"],
                "type": "property",
                "isCaption": True,
                "inTooltip": True,
                "styles": [],
                "isGdsData": False
            })

        perspective["categories"].append(category)

        # Ensure label is in labels dict (if not already added via all_known_labels)
        if label not in perspective["labels"]:
            perspective["labels"][label] = [
                {"propertyKey": p["name"], "type": label, "dataType": p["dataType"]} for p in properties
            ]

        # Metadata Indexes
        perspective["metadata"]["indexes"].append({
            "label": label,
            "type": "native",
            "propertyKeys": [{"key": p["name"], "metadataProp": False} for p in properties]
        })

    # Process Relationships
    for i, rel_conf in enumerate(relationships_config):
        rel_type = rel_conf["type"]

        rel_obj = {
            "id": rel_type,
            "name": rel_type,
            "color": "#A5ABB6",
            "properties": [],
            "size": 1,  # CRITICAL FIELD
            "textSize": 1,
            "textAlign": "top",
            "captions": [{
                "key": rel_type,
                "type": "relationship",
                "isCaption": True,
                "inTooltip": True,
                "styles": []
            }],
            "captionKeys": [],
            "styleRules": []
        }
        perspective["relationshipTypes"].append(rel_obj)

    # Add hidden relationships to relationshipTypes as well, but marked as hidden in root
    for hidden_rel in hidden_rels:
        rel_obj = {
            "id": hidden_rel,
            "name": hidden_rel,
            "color": "#959AA1",
            "properties": [],
            "size": 1,
            "textSize": 1,
            "textAlign": "top",
            "captions": [{
                "key": hidden_rel,
                "type": "relationship",
                "isCaption": True,
                "inTooltip": True,
                "styles": []
            }],
            "captionKeys": [],
            "styleRules": []
        }
        perspective["relationshipTypes"].append(rel_obj)

    # Write to file
    with open(output_file, 'w') as f:
        json.dump(perspective, f, indent=2)
    print(f"Created perspective: {output_file}")


# Example Usage: Create "Seller Performance" Perspective
seller_nodes = [
    {
        "label": "Seller",
        "color": "#C990C0",
        "properties": [
            {"name": "seller_id", "dataType": "string"},
            {"name": "seller_city", "dataType": "string"},
            {"name": "seller_state", "dataType": "string"}
        ]
    },
    {
        "label": "OrderItem",
        "color": "#F16667",
        "properties": [
            {"name": "order_item_id", "dataType": "bigint"},
            {"name": "price", "dataType": "number"},
            {"name": "freight_value", "dataType": "number"}
        ]
    },
    {
        "label": "Product",
        "color": "#569480",
        "properties": [
            {"name": "product_id", "dataType": "string"},
            {"name": "product_category_name", "dataType": "string"}
        ]
    }
]

seller_rels = [
    {"type": "SOLD_BY"},
    {"type": "OF_PRODUCT"}
]

# List of ALL relationships in your database that you want to explicitly HIDE
all_db_relationships = [
    "SOLD_BY", "OF_PRODUCT", "HAS_PAYMENT", "CONTAINS_ITEM",
    "HAS_REVIEW", "LOCATED_IN", "OPERATES_IN", "PLACED", "BOUGHT"
]

# List of ALL labels in your database (Schema Definition)
all_db_labels = {
    "Customer": [
        {"name": "customer_id", "dataType": "string"},
        {"name": "customer_unique_id", "dataType": "string"},
        {"name": "customer_zip_code_prefix", "dataType": "bigint"},
        {"name": "customer_city", "dataType": "string"},
        {"name": "customer_state", "dataType": "string"}
    ],
    "GeoLocation": [
        {"name": "geolocation_zip_code_prefix", "dataType": "bigint"},
        {"name": "geolocation_lat", "dataType": "number"},
        {"name": "geolocation_lng", "dataType": "number"},
        {"name": "geolocation_city", "dataType": "string"},
        {"name": "geolocation_state", "dataType": "string"}
    ],
    "Order": [
        {"name": "order_id", "dataType": "string"},
        {"name": "order_status", "dataType": "string"},
        {"name": "order_purchase_timestamp", "dataType": "string"},
        {"name": "order_approved_at", "dataType": "string"},
        {"name": "order_delivered_customer_date", "dataType": "string"},
        {"name": "order_estimated_delivery_date", "dataType": "string"}
    ],
    "OrderItem": [
        {"name": "order_item_id", "dataType": "bigint"},
        {"name": "shipping_limit_date", "dataType": "string"},
        {"name": "price", "dataType": "number"},
        {"name": "freight_value", "dataType": "number"}
    ],
    "Payment": [
        {"name": "payment_type", "dataType": "string"},
        {"name": "payment_installments", "dataType": "bigint"},
        {"name": "payment_value", "dataType": "number"}
    ],
    "Product": [
        {"name": "product_id", "dataType": "string"},
        {"name": "product_category_name", "dataType": "string"},
        {"name": "product_weight_g", "dataType": "bigint"},
        {"name": "product_length_cm", "dataType": "bigint"},
        {"name": "product_height_cm", "dataType": "bigint"},
        {"name": "product_width_cm", "dataType": "bigint"}
    ],
    "Review": [
        {"name": "review_id", "dataType": "string"},
        {"name": "review_score", "dataType": "bigint"},
        {"name": "review_creation_date", "dataType": "string"}
    ],
    "Seller": [
        {"name": "seller_id", "dataType": "string"},
        {"name": "seller_zip_code_prefix", "dataType": "bigint"},
        {"name": "seller_city", "dataType": "string"},
        {"name": "seller_state", "dataType": "string"}
    ]
}

output_dir = Path(r"v:\Pdf\Project\Prajnaa\neo4j\bloom_automation\output")
output_dir.mkdir(exist_ok=True, parents=True)

generate_bloom_perspective(
    "Seller Performance",
    seller_nodes,
    seller_rels,
    output_dir / "Seller_Performance.json",
    all_known_relationships=all_db_relationships,
    all_known_labels=all_db_labels
)
