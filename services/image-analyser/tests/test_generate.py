from data.generate import generate


def test_generate_deterministic():
    imgs1, labels1 = generate(seed=42, n_per_class=10)
    imgs2, labels2 = generate(seed=42, n_per_class=10)
    assert labels1 == labels2
    for a, b in zip(imgs1, imgs2):
        assert list(a.getdata()) == list(b.getdata())


def test_generate_all_classes():
    imgs, labels = generate(seed=42, n_per_class=10)
    CLASSES = {"insurance_cert", "annual_license", "traffic_ticket", "vehicle_photo", "other"}
    assert set(labels) == CLASSES


def test_generate_count():
    imgs, labels = generate(seed=42, n_per_class=10)
    from collections import Counter
    counts = Counter(labels)
    for cls in counts:
        assert counts[cls] >= 10
