"""
Test blast radius queries - shows the power of generic operations
"""
import getpass
from neo4j import GraphDatabase
from neo4j_orchestration.planning.classifier import QueryIntentClassifier
from neo4j_orchestration.planning.generator import CypherQueryGenerator

def test_blast_radius():
    print("=" * 70)
    print("🎯 BLAST RADIUS ANALYSIS - TESTING GENERIC OPERATIONS")
    print("=" * 70)
    
    # Get credentials
    uri = input("\nEnter your Neo4j Aura URI: ")
    username = input("Enter username (default: neo4j): ") or "neo4j"
    password = getpass.getpass("Enter password: ")
    
    classifier = QueryIntentClassifier()
    generator = CypherQueryGenerator()
    
    # Blast radius and risk analysis queries
    test_queries = [
        "analyze control blast radius",
        "show control failures",
        "list controls with high impact",
        "analyze vendor dependencies",
        "show critical controls",
        "count controls by effectiveness",
        "list failed controls",
    ]
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    try:
        print("\n✅ Connected to ERKG!\n")
        
        for query in test_queries:
            print(f"\n{'='*70}")
            print(f"📝 Query: '{query}'")
            print(f"{'='*70}")
            
            # Classify
            intent = classifier.classify(query)
            
            # Show what type was detected
            is_generic = intent.query_type.is_generic
            type_marker = "🔥 GENERIC" if is_generic else "📌 LEGACY"
            
            print(f"\n{type_marker} Classification:")
            print(f"   QueryType: {intent.query_type.value}")
            print(f"   Entities: {[e.value for e in intent.entities]}")
            if intent.filters:
                print(f"   Filters: {[(f.field, f.operator.value, f.value) for f in intent.filters]}")
            if intent.aggregations:
                print(f"   Aggregations: {[a.type.value for a in intent.aggregations]}")
            
            # Generate
            try:
                cypher, params = generator.generate(intent)
                print(f"\n⚙️  Generated Cypher:")
                for line in cypher.strip().split('\n'):
                    print(f"   {line}")
                if params:
                    print(f"   Parameters: {params}")
                
                # Execute
                with driver.session() as session:
                    result = session.run(cypher, params)
                    records = list(result)
                    
                    print(f"\n✅ Execution Result: {len(records)} records")
                    
                    # Smart display based on query type
                    if records:
                        if len(records) <= 5:
                            for i, record in enumerate(records, 1):
                                display_record(record, i)
                        else:
                            print(f"   (Showing first 5 of {len(records)})")
                            for i, record in enumerate(records[:5], 1):
                                display_record(record, i)
                        
            except ValueError as e:
                print(f"\n⚠️  Cannot generate: {e}")
            except Exception as e:
                print(f"\n❌ Execution error: {str(e)[:200]}")
        
        print(f"\n{'='*70}")
        print("🎉 BLAST RADIUS TEST COMPLETE!")
        print("=" * 70)
        print("\n📊 Summary:")
        print("   This demonstrates how generic operations work with")
        print("   ANY entity type in your knowledge graph!")
        print("=" * 70)
        
    finally:
        driver.close()

def display_record(record, index):
    """Smart display of different record types"""
    data = dict(record)
    
    # Handle different return types
    if 'c' in data:  # Control node
        node = data['c']
        if hasattr(node, 'get'):
            name = node.get('name', node.get('control_id', 'Control'))
            effectiveness = node.get('effectiveness', 'N/A')
            print(f"   {index}. {name} (Effectiveness: {effectiveness})")
        else:
            print(f"   {index}. {node}")
    elif 'v' in data:  # Vendor node
        node = data['v']
        if hasattr(node, 'get'):
            name = node.get('name', 'Vendor')
            risk = node.get('inherent_risk_rating', 'N/A')
            print(f"   {index}. {name} (Risk: {risk})")
        else:
            print(f"   {index}. {node}")
    elif len(data) == 1 and isinstance(list(data.values())[0], (int, float)):
        # Aggregation result
        key = list(data.keys())[0]
        value = list(data.values())[0]
        print(f"   {key}: {value}")
    else:
        # Generic display
        print(f"   {index}. {data}")

if __name__ == "__main__":
    test_blast_radius()
