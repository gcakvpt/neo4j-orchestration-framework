"""
Advanced ERKG testing with better queries
"""
import getpass
from neo4j import GraphDatabase
from neo4j_orchestration.planning.classifier import QueryIntentClassifier
from neo4j_orchestration.planning.generator import CypherQueryGenerator

def test_advanced():
    print("=" * 70)
    print("ADVANCED GENERIC OPERATIONS TEST - YOUR ERKG")
    print("=" * 70)
    
    # Get credentials
    uri = input("\nEnter your Neo4j Aura URI: ")
    username = input("Enter username (default: neo4j): ") or "neo4j"
    password = getpass.getpass("Enter password: ")
    
    classifier = QueryIntentClassifier()
    generator = CypherQueryGenerator()
    
    # Better test queries for your ERKG
    test_queries = [
        "list all vendors",
        "count controls",
        "show high risk vendors",
        "list critical service providers",
        "count vendors by status",
        "show vendors with foreign risk",
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
            print(f"\n🔍 Classification:")
            print(f"   Type: {intent.query_type.value} ({'GENERIC' if intent.query_type.is_generic else 'LEGACY'})")
            print(f"   Entities: {[e.value for e in intent.entities]}")
            if intent.filters:
                print(f"   Filters: {[(f.field, f.value) for f in intent.filters]}")
            
            # Generate
            try:
                cypher, params = generator.generate(intent)
                print(f"\n⚙️  Cypher:")
                for line in cypher.strip().split('\n'):
                    print(f"   {line}")
                if params:
                    print(f"   Params: {params}")
                
                # Execute
                with driver.session() as session:
                    result = session.run(cypher, params)
                    records = list(result)
                    
                    print(f"\n✅ Results: {len(records)} records")
                    
                    if records and len(records) <= 5:
                        for i, record in enumerate(records, 1):
                            data = dict(record)
                            # Show just the node name if it's a node
                            if 'v' in data:
                                print(f"   {i}. {data['v'].get('name', data['v'])}")
                            elif 'c' in data:
                                print(f"   {i}. {data['c'].get('name', data['c'])}")
                            else:
                                print(f"   {i}. {data}")
                    elif records:
                        print(f"   (Showing first 3 of {len(records)})")
                        for i, record in enumerate(records[:3], 1):
                            data = dict(record)
                            if 'v' in data:
                                print(f"   {i}. {data['v'].get('name', 'Vendor')}")
                            else:
                                print(f"   {i}. {data}")
                        
            except ValueError as e:
                print(f"\n⚠️  Generation skipped: {e}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        print(f"\n{'='*70}")
        print("🎉 ADVANCED TEST COMPLETE!")
        print(f"{'='*70}")
        
    finally:
        driver.close()

if __name__ == "__main__":
    test_advanced()
