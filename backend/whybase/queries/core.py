"""Parameterized Cypher used by WHYBASE investigations."""

BLAST_RADIUS = """
MATCH p=(s:Service {id: $service})-[:DEPENDS_ON*1..5]-(related:Service)
WHERE length(p) <= $depth
RETURN related.id AS id, related.name AS name, length(p) AS hops
ORDER BY hops, name LIMIT $cap
"""

TRACE_INCIDENT = """
MATCH (i:Incident {id: $incident})-[:CAUSED_BY]->(d:Decision)
OPTIONAL MATCH (p:Person)-[:DECIDED]->(d)
OPTIONAL MATCH (d)-[:AFFECTS]->(s:Service)
OPTIONAL MATCH (t:Team)-[:OWNS]->(s)
RETURN i, d, p, s, t
"""

WHO_OWNED = """
MATCH (t:Team)-[o:OWNS]->(s:Service {id: $service})
WHERE o.valid_from <= $as_of AND (o.valid_to IS NULL OR o.valid_to >= $as_of)
RETURN t.id AS team_id, t.name AS team, o.valid_from AS valid_from, o.valid_to AS valid_to
"""

DECISION_LINEAGE = """
MATCH p=(d:Decision {id: $decision})-[:SUPERSEDES*0..8]->(older:Decision)
OPTIONAL MATCH (author:Person)-[:DECIDED]->(d)
OPTIONAL MATCH (d)-[:DOCUMENTED_IN]->(doc:Document)
RETURN d, older, author, doc, length(p) AS hops
ORDER BY hops LIMIT $cap
"""

ABSENCE_CHECK = """
MATCH (a {id: $subject})
OPTIONAL MATCH p=(a)-[*1..5]-(b {id: $scope})
WHERE length(p) <= $depth
RETURN count(p) AS connecting_paths, count(a) AS scanned_subjects
"""
