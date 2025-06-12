import numpy as np
from sklearn.preprocessing import LabelEncoder

from src.infer import predict_intent


class DummyTokenizer:
    class _Encoding(dict):
        """Simple dict subclass mirroring HF BatchEncoding `.to()` behaviour."""

        def to(self, device):  # noqa: D401
            return self

    def __call__(self, text, **kwargs):
        # Return minimal encoding with required keys
        return self._Encoding(
            {
                "input_ids": np.zeros((1, 5), dtype=np.int64),
                "attention_mask": np.ones((1, 5), dtype=np.int64),
            }
        )


class DummyModel:
    def __init__(self, logits):
        import torch

        self._logits = torch.tensor(logits, dtype=torch.float32)

    def __call__(self, **kwargs):
        class Output:  # noqa: D401
            def __init__(self, logits):
                self.logits = logits

        return Output(self._logits)



def test_low_confidence_returns_clarify():
    """If max prob < threshold, intent should be fallback label."""
    # Two-class dummy encoder
    le = LabelEncoder()
    le.fit(["intent_a", "intent_b"])

    # Logits such that softmax probs = [0.6, 0.4] (<0.65 threshold)
    logits = [[1.0, 0.0]]

    tokenizer = DummyTokenizer()
    model = DummyModel(logits)

    cfg = {"confidence_threshold": 0.65, "fallback_intent": "clarify"}

    intent = predict_intent(
        "dummy query",
        tokenizer,
        model,
        le,
        device="cpu",
        cfg=cfg,
        return_probs=False,
    )
    assert intent == "clarify" 