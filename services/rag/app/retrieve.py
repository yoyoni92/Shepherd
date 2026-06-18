def query(collection, question: str, caller_context: dict, top_k: int = 3) -> list[dict]:
    where = _build_where(caller_context)
    kwargs: dict = dict(
        query_texts=[question],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where
    try:
        results = collection.query(**kwargs)
    except Exception:
        return []
    docs = results.get("documents") or [[]]
    metas = results.get("metadatas") or [[]]
    return [{"document": d, "metadata": m} for d, m in zip(docs[0], metas[0])]


def _build_where(caller_context: dict) -> dict | None:
    role = caller_context.get("role", "admin")
    if role == "admin":
        return None
    vehicle_ids = caller_context.get("vehicle_ids", [])
    if not vehicle_ids:
        # ponytail: block-all sentinel - driver with no vehicles sees nothing
        return {"vehicle_id": {"$eq": "__none__"}}
    if len(vehicle_ids) == 1:
        return {"vehicle_id": {"$eq": vehicle_ids[0]}}
    return {"vehicle_id": {"$in": vehicle_ids}}
