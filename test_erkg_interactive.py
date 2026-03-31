"""
Interactive test against your ERKG - prompts for credentials
"""
import getpass
from neo4j import GraphDatabase
from neo4j_orchestration.planning.classifier import QueryIntentClassifier
from neo4j_orchestration.planning.generator import CypherQueryGenerator

def test_with_erkg():
    print("=" * 70)
    print("TESTING GENERIC OPERATIONS WITH YOUR LIVE ERKG")
    print("=" * 70)
    
    # Get credentials
    uri = input("\nEnter your Neo4j Aura URI (e.g., neo4j+s://xxxxx.databases.neo4j.io): ")
    username = input("Enter username (default: neo4j): ") or "neo4j"
    password = getpass.getpass("Enter password: ")
    
    classifier = QueryIntentClassifier()
    generator = CypherQueryGenerator()
    
    # Test queries tailored to your ERKG
    test_queries = [
        "list all vendors",
        "show assessments",
        "count controls",
        "filter vendors",
    ]
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    try:
        # First, verify connection
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
            print("\n✅ Connected to ERKG successfully!\n")
        
        for query in test_queries:
            print(f"\n{'='*70}")
            print(f"Natural Language: '{query}'")
            print(f"{'='*70}")
            
            # Classify
            intent = classifier.classify(query)
            print(f"\n1️⃣  CLASSIFICATION:")
            print(f"   QueryType: {intent.query_type.value}")
            print(f"   Is Generic: {intent.query_type.is_generic}")
            print(f"   Entities: {[e.value for e in intent.entities]}")
            
            # Generate
            cypher, params = generator.generate(intent)
            print(f"\n2️⃣  GENERATED CYPHER:")
            print(f"   {cypher.strip()}")
            if params:
                print(f"   Parameters: {params}")
            
            # Execute
            print(f"\n3️⃣  EXECUTION:")
            try:
                with driver.session() as session:
                    result = session.run(cypher, params)
                    records = list(result)
                    print(f"   ✅ SUCCESS: {len(records)} records returned")
                    
                    # Show first 3 results
                    if records:
                        print(f"\n   Sample results:")
                        for i, record in enumerate(records[:3], 1):
                            print(f"      {i}. {dict(record)}")
                        if len(records) > 3:
                            print(f"      ... and {len(records)-3} more")
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
        
        print(f"\n{'='*70}")
        print("✅ LIVE ERKG TEST COMPLETE!")
        print(f"{'='*70}")
        
    finally:
        driver.close()

if __name__ == "__main__":
    test_with_erkg()
