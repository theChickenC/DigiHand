from solverBase import SolverBase

MODEL_REVISION = "2025-01-09"  # pin a known-good revision; update as needed

# Prompt used for transcription. Moondream doesn't have a dedicated <OCR> tag
# like Florence-2 -- you drive it with natural-language instructions via
# model.query(). This phrasing tends to work well for handwriting.
OCR_PROMPT = (
    "Transcribe all the handwritten text in this image exactly as written, "
    "preserving line breaks. Do not summarize or correct spelling."
)

class SolverMoondream(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Moondream2"
        self.model = None
        self.tokenizer = None

    def load_model(self):
        if self.model is not None and self.tokenizer is not None:
            return

        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model = AutoModelForCausalLM.from_pretrained(
            "vikhyatk/moondream2",
            revision=MODEL_REVISION,
            trust_remote_code=True,
            dtype=self.torch_dtype,
        ).to(self.device)
        self.model.eval()
        # assign to self.tokenizer, otherwise the cache check above never hits
        # and the tokenizer is rebuilt (and the model reloaded) on every call
        self.tokenizer = AutoTokenizer.from_pretrained(
            "vikhyatk/moondream2", revision=MODEL_REVISION
        )

    def recognize_page(self, image) -> str:
        import torch

        with torch.no_grad():
            result = self.model.query(image, OCR_PROMPT)
        # Newer moondream revisions return a dict like {"answer": "..."}
        if isinstance(result, dict):
            return result.get("answer", "")
        return str(result)