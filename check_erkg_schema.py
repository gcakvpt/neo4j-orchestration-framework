"""
Check what relationships exist in your ERKG for blast radius analysis
"""
import getpass
from neo4j import GraphDatabase

uri = input("Enter your Neo4j Aura URI: ")
username = input("Enter username (default: neo4j): ") or "neo4j"
password = getpass.getpass("Enter password: ")

driver = GraphDatabase.driver(uri, auth=(username, password))

print("\n" + "="*70)
print("ERKG SCHEMA ANALYSIS")
print("="*70)

with driver.session() as session:
    # Check Control relationships
    print("\n1. Control Relationships:")
    result = session.run("""
        MATCH (c:Control)-[r]-(other)
        RETURN type(r) as rel_type, labels(other)[0] as connected_to, count(*) as count
        ORDER BY count DESC
        LIMIT 10
    """)
    for record in result:
        print(f"   {record['rel_type']:30} → {record['connected_to']:20} ({record['count']} connections)")
    
    # Check sample Control properties
    print("\n2. Sample Control:")
    result = session.run("MATCH (c:Control) RETURN c LIMIT 1")
    record = result.single()
    if record:
        control = record['c']
        print(f"   Properties: {list(control.keys())[:10]}")
    
    # Check what's connected to Controls
    print("\n3. What Controls are connected to:")
    result = session.run("""
        MATCH (c:Control)-[r]-(n)
        RETURN DISTINCT labels(n)[0] as entity_type, count(*) as count
        ORDER BY count DESC
    """)
    for record in result:
        print(f"   {record['entity_type']:20} ({record['count']} connections)")

driver.close()
