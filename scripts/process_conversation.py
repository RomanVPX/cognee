import cognee
import asyncio
import json
import os
import argparse
from cognee.api.v1.visualize.visualize import visualize_graph
from cognee.tasks.graph.models import GraphOntology, OntologyNode
from cognee.infrastructure.llm.prompts import read_query_prompt
from cognee.infrastructure.llm.get_llm_client import get_llm_client
from cognee.infrastructure.llm.config import get_llm_config

# Try to import RDFLib for more efficient RDF handling
try:
    import rdflib
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False

async def update_ontology(ontology_path, new_ontology):
    """Update existing ontology with new data."""
    if not RDFLIB_AVAILABLE:
        print("RDFLib not available, cannot update ontology. Will overwrite instead.")
        return False

    try:
        # Load existing ontology
        existing_g = rdflib.Graph()
        existing_g.parse(ontology_path, format="xml")

        # Load new ontology
        new_g = rdflib.Graph()
        for node in new_ontology.nodes:
            # Extract clean name and determine node type
            clean_name = node.name.lower()
            if "topic:" in node.name.lower():
                node_type = rdflib.URIRef("http://example.org/ontology#Topic")
                clean_name = node.name.replace("Topic:", "").replace("topic:", "").strip().lower()
            elif "concept:" in node.name.lower():
                node_type = rdflib.URIRef("http://example.org/ontology#Concept")
                clean_name = node.name.replace("Concept:", "").replace("concept:", "").strip().lower()
            elif "message:" in node.name.lower():
                node_type = rdflib.URIRef("http://example.org/ontology#Message")
                clean_name = node.name.replace("Message:", "").replace("message:", "").strip().lower()
            elif "participant:" in node.name.lower():
                node_type = rdflib.URIRef("http://example.org/ontology#Participant")
                clean_name = node.name.replace("Participant:", "").replace("participant:", "").strip().lower()
            else:
                # If no explicit prefix, try to determine type by context
                if "topic" in node.name.lower():
                    node_type = rdflib.URIRef("http://example.org/ontology#Topic")
                elif "message" in node.name.lower():
                    node_type = rdflib.URIRef("http://example.org/ontology#Message")
                elif "participant" in node.name.lower():
                    node_type = rdflib.URIRef("http://example.org/ontology#Participant")
                else:
                    node_type = rdflib.URIRef("http://example.org/ontology#Concept")
                clean_name = node.name.lower()

            # Create a standardized ID without colons and with proper formatting
            node_id = clean_name.replace(" ", "_")
            node_uri = rdflib.URIRef(f"http://example.org/ontology#{node_id}")

            # Skip if this is a duplicate of Roman or AI
            if (clean_name.lower() == "roman" or clean_name.lower() == "ai") and "participant" in str(node_type).lower():
                continue

            # Add node to graph if it doesn't exist
            if (node_uri, None, None) not in existing_g:

                existing_g.add((node_uri, rdflib.RDF.type, node_type))
                existing_g.add((node_uri, rdflib.RDFS.label, rdflib.Literal(clean_name)))
                if node.description:
                    existing_g.add((node_uri, rdflib.RDFS.comment, rdflib.Literal(node.description)))

        # Add relationships
        for edge in new_ontology.edges:
            # Extract clean names for source and target
            source_clean_name = edge.source_id.lower()
            target_clean_name = edge.target_id.lower()

            # Handle prefixed names
            if "topic:" in source_clean_name:
                source_clean_name = source_clean_name.replace("Topic:", "").replace("topic:", "").strip()
            elif "concept:" in source_clean_name:
                source_clean_name = source_clean_name.replace("Concept:", "").replace("concept:", "").strip()
            elif "message:" in source_clean_name:
                source_clean_name = source_clean_name.replace("Message:", "").replace("message:", "").strip()
            elif "participant:" in source_clean_name:
                source_clean_name = source_clean_name.replace("Participant:", "").replace("participant:", "").strip()

            if "topic:" in target_clean_name:
                target_clean_name = target_clean_name.replace("Topic:", "").replace("topic:", "").strip()
            elif "concept:" in target_clean_name:
                target_clean_name = target_clean_name.replace("Concept:", "").replace("concept:", "").strip()
            elif "message:" in target_clean_name:
                target_clean_name = target_clean_name.replace("Message:", "").replace("message:", "").strip()
            elif "participant:" in target_clean_name:
                target_clean_name = target_clean_name.replace("Participant:", "").replace("participant:", "").strip()

            # Create standardized IDs
            source_id = source_clean_name.replace(" ", "_")
            target_id = target_clean_name.replace(" ", "_")
            relation_type = edge.relationship_type.lower().replace(" ", "_")

            source_uri = rdflib.URIRef(f"http://example.org/ontology#{source_id}")
            target_uri = rdflib.URIRef(f"http://example.org/ontology#{target_id}")
            relation_uri = rdflib.URIRef(f"http://example.org/ontology#{relation_type}")

            # Add relationship type if it doesn't exist
            if (relation_uri, rdflib.RDF.type, rdflib.OWL.ObjectProperty) not in existing_g:
                existing_g.add((relation_uri, rdflib.RDF.type, rdflib.OWL.ObjectProperty))
                existing_g.add((relation_uri, rdflib.RDFS.label, rdflib.Literal(relation_type)))

            # Add the relationship if it doesn't exist
            if (source_uri, relation_uri, target_uri) not in existing_g:
                existing_g.add((source_uri, relation_uri, target_uri))

        # Save updated ontology
        existing_g.serialize(destination=ontology_path, format="xml")
        print(f"Ontology updated successfully at {ontology_path}")
        return True
    except Exception as e:
        print(f"Error updating ontology: {str(e)}")
        return False

async def process_conversation_from_json(file_path, prune=False, generate_ontology=False, prompt_type="guided"):
    """
    Process a conversation from a JSON file and update the ontology.

    Args:
        file_path (str): Path to the JSON file containing the conversation
        prune (bool): Whether to reset previous data before processing
        generate_ontology (bool): Whether to generate a completely new ontology
        prompt_type (str): Type of prompt to use for ontology extraction
            - 'guided': Detailed prompt with specific instructions
            - 'simple': Simplified prompt
            - 'basic': Basic prompt with minimal instructions

    Returns:
        str: Status message indicating the result of processing
    """
    # Reset previous data only if prune flag is set
    if prune:
        print("Performing data pruning...")
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)

    # Read and parse JSON file
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Convert to formatted text
    formatted_conversation = ""
    for message in data["messages"]:
        author = "roman" if message["author"] == "user" else "ai"
        content = message["content"]["text"]
        formatted_conversation += f"{author}: {content}\n\n"

    print(f"\nPrepared conversation with {len(formatted_conversation)} characters")

    # Add and process in Cognee
    await cognee.add(formatted_conversation)
    print("Data added to Cognee")

    # Define ontology path - use the common ontology directory in the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ontology_dir = os.path.join(project_root, "ontology")
    os.makedirs(ontology_dir, exist_ok=True)
    ontology_path = os.path.join(ontology_dir, "dialog_ontology.owl")

    # Generate ontology if requested, if it doesn't exist, or if we want to update it
    should_update_ontology = generate_ontology or not os.path.exists(ontology_path)

    # Always try to update existing ontology with new data from the conversation
    if os.path.exists(ontology_path) and not should_update_ontology:
        print("Attempting to update existing ontology with new data from the conversation...")
        should_update_ontology = True  # Set to True to trigger ontology generation

    if should_update_ontology:
        print(f"{'Generating' if generate_ontology else 'Creating/Updating'} ontology from conversation data...")

        # Use built-in extract_ontology function to create ontology
        try:
            # Get LLM client and config
            llm_client = get_llm_client()
            llm_config = get_llm_config()

            # Select the appropriate prompt based on the prompt_type parameter
            if prompt_type == "guided":
                system_prompt = read_query_prompt("generate_graph_prompt_guided.txt")
            elif prompt_type == "simple":
                system_prompt = read_query_prompt("generate_graph_prompt.txt")
            else:
                system_prompt = read_query_prompt("extract_ontology.txt")

            # Create dialog-specific context for the ontology extraction
            dialog_context = format(formatted_conversation)

            # Create a custom GraphOntology with dialog-specific structure
            dialog_ontology = GraphOntology(
                nodes=[
                    # Add base participant nodes - without prefixes to avoid duplication
                    OntologyNode(id="roman", name="roman", description="The human participant in the dialog"),
                    OntologyNode(id="ai", name="ai", description="The AI assistant in the dialog")
                ],
                edges=[]
            )

            # Extract ontology using the selected prompt and the dialog context
            ontology = await llm_client.acreate_structured_output(dialog_context, system_prompt, GraphOntology)

            # Merge the extracted ontology with the base dialog ontology
            for node in ontology.nodes:
                # Skip if we already have this node (like Roman or AI)
                if any(base_node.id == node.id for base_node in dialog_ontology.nodes):
                    continue
                dialog_ontology.nodes.append(node)

            for edge in ontology.edges:
                dialog_ontology.edges.append(edge)

            # Now create the RDF/OWL ontology
            if RDFLIB_AVAILABLE:
                # Check if ontology already exists and we're not forcing a new generation
                create_new_ontology = True  # Flag to control whether to create a new ontology
                if os.path.exists(ontology_path) and not generate_ontology:
                    updated = await update_ontology(ontology_path, dialog_ontology)
                    if updated:
                        print(f"Existing ontology updated at {ontology_path}")
                        create_new_ontology = False  # Don't create a new ontology if update was successful
                    else:
                        # If update failed, create a new ontology
                        print("Creating new ontology...")
                else:
                    # If ontology doesn't exist or generate_ontology is True, create a new ontology
                    print("Creating new ontology...")

                # Create a new ontology only if needed
                if create_new_ontology:
                    # Use RDFLib to create ontology
                    g = rdflib.Graph()

                    # Define namespaces
                    ns = rdflib.Namespace("http://example.org/ontology#")
                    rdf = rdflib.namespace.RDF
                    rdfs = rdflib.namespace.RDFS
                    owl = rdflib.namespace.OWL

                    # Add main classes
                    g.add((ns.Participant, rdf.type, owl.Class))
                    g.add((ns.Participant, rdfs.label, rdflib.Literal("participant")))

                    g.add((ns.Message, rdf.type, owl.Class))
                    g.add((ns.Message, rdfs.label, rdflib.Literal("message")))

                    g.add((ns.Topic, rdf.type, owl.Class))
                    g.add((ns.Topic, rdfs.label, rdflib.Literal("topic")))

                    g.add((ns.Concept, rdf.type, owl.Class))
                    g.add((ns.Concept, rdfs.label, rdflib.Literal("concept")))

                    # Add participants
                    g.add((ns.Roman, rdf.type, ns.Participant))
                    g.add((ns.Roman, rdfs.label, rdflib.Literal("roman")))

                    g.add((ns.AI, rdf.type, ns.Participant))
                    g.add((ns.AI, rdfs.label, rdflib.Literal("ai")))

                    # Add nodes from generated ontology
                    for node in dialog_ontology.nodes:
                        # Extract clean name and determine node type based on its name
                        node_type = ns.Concept  # Default to Concept
                        clean_name = node.name.lower()

                        # Process nodes with explicit type prefixes
                        if "topic:" in node.name.lower():
                            node_type = ns.Topic
                            clean_name = node.name.replace("Topic:", "").replace("topic:", "").strip().lower()
                        elif "concept:" in node.name.lower():
                            node_type = ns.Concept
                            clean_name = node.name.replace("Concept:", "").replace("concept:", "").strip().lower()
                        elif "message:" in node.name.lower():
                            node_type = ns.Message
                            clean_name = node.name.replace("Message:", "").replace("message:", "").strip().lower()
                        elif "participant:" in node.name.lower():
                            node_type = ns.Participant
                            clean_name = node.name.replace("Participant:", "").replace("participant:", "").strip().lower()
                        else:
                            # If no explicit prefix, try to determine type by context
                            if "topic" in node.name.lower():
                                node_type = ns.Topic
                            elif "message" in node.name.lower():
                                node_type = ns.Message
                            elif "participant" in node.name.lower():
                                node_type = ns.Participant

                        # Create a standardized ID without colons and with proper formatting
                        node_id = clean_name.replace(" ", "_")
                        node_uri = ns[node_id]

                        # Skip if this is a duplicate of Roman or AI
                        if (clean_name.lower() == "roman" or clean_name.lower() == "ai") and node_type == ns.Participant:
                            continue

                        g.add((node_uri, rdf.type, node_type))
                        g.add((node_uri, rdfs.label, rdflib.Literal(clean_name)))
                        if node.description:
                            g.add((node_uri, rdfs.comment, rdflib.Literal(node.description)))

                    # First determine all relationship types
                    relation_types = set()
                    for edge in dialog_ontology.edges:
                        # Convert to lower_snake_case
                        relation_type = edge.relationship_type.lower().replace(" ", "_")
                        relation_types.add(relation_type)

                    # Add relationship type definitions
                    for relation_type in relation_types:
                        relation_uri = ns[relation_type]
                        g.add((relation_uri, rdf.type, owl.ObjectProperty))
                        g.add((relation_uri, rdfs.label, rdflib.Literal(relation_type)))

                    # Add relationships from generated ontology
                    for edge in dialog_ontology.edges:
                        # Extract clean names for source and target
                        source_clean_name = edge.source_id.lower()
                        target_clean_name = edge.target_id.lower()

                        # Handle prefixed names
                        if "topic:" in source_clean_name:
                            source_clean_name = source_clean_name.replace("Topic:", "").replace("topic:", "").strip()
                        elif "concept:" in source_clean_name:
                            source_clean_name = source_clean_name.replace("Concept:", "").replace("concept:", "").strip()
                        elif "message:" in source_clean_name:
                            source_clean_name = source_clean_name.replace("Message:", "").replace("message:", "").strip()
                        elif "participant:" in source_clean_name:
                            source_clean_name = source_clean_name.replace("Participant:", "").replace("participant:", "").strip()

                        if "topic:" in target_clean_name:
                            target_clean_name = target_clean_name.replace("Topic:", "").replace("topic:", "").strip()
                        elif "concept:" in target_clean_name:
                            target_clean_name = target_clean_name.replace("Concept:", "").replace("concept:", "").strip()
                        elif "message:" in target_clean_name:
                            target_clean_name = target_clean_name.replace("Message:", "").replace("message:", "").strip()
                        elif "participant:" in target_clean_name:
                            target_clean_name = target_clean_name.replace("Participant:", "").replace("participant:", "").strip()

                        # Create standardized IDs
                        source_id = source_clean_name.replace(" ", "_")
                        target_id = target_clean_name.replace(" ", "_")
                        relation_type = edge.relationship_type.lower().replace(" ", "_")

                        source_uri = ns[source_id]
                        target_uri = ns[target_id]
                        relation_uri = ns[relation_type]

                        g.add((source_uri, relation_uri, target_uri))

                    # Save RDF/XML to file
                    g.serialize(destination=ontology_path, format="xml")

                    print(f"Ontology saved to {ontology_path}")
                else:
                    print("No RDFLIB available, skipping ontology generation.")

            # Use generated ontology for cognify
            await cognee.cognify(ontology_file_path=ontology_path)
        except Exception as e:
            print(f"Error generating ontology: {str(e)}")
            print("Continuing without ontology...")
            await cognee.cognify()
    else:
        # Check if ontology already exists
        if os.path.exists(ontology_path):
            print(f"Using existing ontology: {ontology_path}")
            await cognee.cognify(ontology_file_path=ontology_path)
        else:
            print("Ontology not found, continuing without it")
            await cognee.cognify()

    print("Processing completed")

    # Save visualization
    current_dir = os.getcwd()
    visualization_dir = os.path.join(current_dir, "visualizations")
    os.makedirs(visualization_dir, exist_ok=True)
    visualization_file = os.path.join(visualization_dir, "graph_visualization.html")

    _ = await visualize_graph(destination_file_path=visualization_file)

    print(f"Visualization saved to {visualization_file}")

    return "Processing completed successfully"

if __name__ == '__main__':
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description='Process conversation from JSON file and update ontology')
    parser.add_argument('file_path', help='Path to JSON file with conversation')
    parser.add_argument('--prune', action='store_true', help='Reset previous data before processing')
    parser.add_argument('--generate-ontology', action='store_true',
                      help='Generate a completely new ontology (otherwise will update existing one)')
    parser.add_argument('--prompt-type', choices=['guided', 'simple', 'basic'], default='basic',
                      help='Type of prompt to use for ontology extraction: guided (detailed), simple, or basic')
    args = parser.parse_args()

    # Run processing with flags
    asyncio.run(process_conversation_from_json(args.file_path, args.prune, args.generate_ontology, args.prompt_type))