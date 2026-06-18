import numpy as np

from app.embed import embed


def test_multilingual_similarity():
    he = "מה הסטטוס של הרכב?"
    en = "What is the vehicle status?"
    vecs = embed([he, en])
    assert len(vecs[0]) == len(vecs[1]), "embedding dim must be stable"
    sim = float(np.dot(vecs[0], vecs[1]))
    assert sim > 0.6, f"HE/EN paraphrase similarity too low: {sim:.3f}"


def test_embed_dim_stable():
    short = embed(["hello"])[0]
    long_text = "vehicle plate 123-45-678 insurance expiring next month maintenance due"
    long = embed([long_text])[0]
    assert len(short) == len(long)
