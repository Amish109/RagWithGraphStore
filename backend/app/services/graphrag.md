Summary of all 4 GraphRAG improvements
1. Graph context enabled by default
schemas.py: include_graph_context now defaults to True instead of False
retrieval_service.py: Same default flip on retrieve_relevant_context()
Effect: Every query now automatically gets entity relationship context — no frontend changes needed
2. Hybrid retrieval (vector + graph entity lookup)
retrieval_service.py: Both retrieve_relevant_context() and retrieve_for_documents() now run vector search (Qdrant) and graph entity lookup (Neo4j) in parallel
_merge_and_rerank(): Deduplicates chunks found by both methods. Chunks found by BOTH get a 1.2x score boost ("hybrid" method). Graph-only chunks get a 0.7 base score. Final results sorted by score
_safe_graph_entity_lookup(): Wraps the graph lookup with error handling so LLM/Neo4j failures don't break vector search
Previously dead code get_entity_chunks_for_query() is now called on every query
3. True multi-hop traversal
graphrag_service.py: MULTI_HOP_QUERY now uses [:RELATES_TO*1..2] (variable-length paths) instead of [:RELATES_TO] (1-hop only)
Returns hop_distance per relationship so the LLM knows direct vs indirect connections
Bumped results from 10 to 15 per chunk to accommodate the richer multi-hop data
generation_service.py: Formats hop distance in the LLM context (e.g., (hop 2) for indirect relationships)
4. Community-aware retrieval (entity co-occurrence)
graphrag_service.py: Added three new functions:
get_entity_co_occurrences() — finds "bridge entities" that appear across 2+ documents
get_co_occurrence_chunks() — gets chunks where bridge entities appear
Both filter by user_id for multi-tenant safety
queries.py: New GET /api/v1/query/graph/entities endpoint exposes cross-document entities
Multi-tenant fix: All entity lookup queries now filter by user_id via d.user_id IN $user_ids (previously had no user filtering)
Cross-cutting improvements
generation_service.py: Extracted _assemble_context() to eliminate code duplication between generate_answer() and stream_answer(). Enhanced to show matched entity info and hop distances. System prompt updated to instruct LLM to synthesize cross-document entity information
graphrag_service.py: get_entity_chunks_for_query() now accepts user_id and optional document_ids for proper multi-tenant + document-scoped filtering
done??
Yes, all 4 improvements are done. Here's the quick recap:

#	Improvement	Status
1	Graph context ON by default	include_graph_context flipped to True
2	Hybrid retrieval	Vector + graph entity lookup run in parallel, merged & re-ranked
3	True multi-hop	Cypher now uses [:RELATES_TO*1..2] with hop distance
4	Community-aware	Co-occurrence queries + GET /graph/entities endpoint
The previously dead get_entity_chunks_for_query() is now called on every query, multi-tenant filtering was fixed on all graph queries, and the generation service formats the richer context for the LLM.

