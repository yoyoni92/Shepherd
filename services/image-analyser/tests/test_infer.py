import torch
import PIL.Image
from model import build_model
from infer import infer, infer_batch


def _blank(color=(128, 128, 128)):
    return PIL.Image.new("RGB", (224, 224), color=color)


def test_infer_schema():
    model = build_model()
    model.eval()
    result = infer(_blank(), model)
    assert set(result.keys()) == {"doc_type", "confidence"}
    assert isinstance(result["confidence"], float)
    assert isinstance(result["doc_type"], str)


def test_infer_uncertain_below_threshold():
    model = build_model()
    model.eval()
    # threshold=1.0 forces uncertain always
    result = infer(_blank(), model, threshold=1.0)
    assert result["doc_type"] == "uncertain"
    assert 0.0 < result["confidence"] <= 1.0


def test_infer_confident_above_threshold():
    model = build_model()
    model.eval()
    # threshold=0.0 forces confident always
    result = infer(_blank(), model, threshold=0.0)
    assert result["doc_type"] != "uncertain"
    assert result["doc_type"] in ["annual_license", "insurance_cert", "other",
                                   "traffic_ticket", "vehicle_photo"]


def test_batch_parity():
    """Batch slot i must match a single-image call using the same seed (seed=i)."""
    import torch
    from data.augment import augment

    model = build_model()
    model.eval()
    imgs = [_blank((i * 50, i * 50, i * 50)) for i in range(3)]
    batch_results = infer_batch(imgs, model)
    for i, img in enumerate(imgs):
        # Replicate what infer_batch does for slot i: augment with seed=i
        tensor = augment(img, seed=i).unsqueeze(0)
        with torch.no_grad():
            logits = model(tensor)
        probs = torch.softmax(logits, dim=-1)
        conf, argmax = torch.max(probs, dim=-1)
        assert abs(batch_results[i]["confidence"] - conf.item()) < 1e-5
