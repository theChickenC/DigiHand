import os
from pathlib import Path
from PIL import Image
import pymupdf # only needed for PDF input
from solverBase import SolverBase

MODEL_REVISION = "2025-01-09"  # pin a known-good revision; update as needed
 
# Prompt used for transcription. Moondream doesn't have a dedicated <OCR> tag
# like Florence-2 -- you drive it with natural-language instructions via
# model.query(). This phrasing tends to work well for handwriting.
OCR_PROMPT = (
    "Transcribe all the handwritten text in this image exactly as written, "
    "preserving line breaks. Do not summarize or correct spelling."
)

class SolverMoonbeam(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Moonbeam"
        self.model = None
        self.tokenizer = None

    
    def get_model_and_tokenizer(self):
        if self.model is not None and self.tokenizer is not None:
            return self.model, self.tokenizer
    
        from transformers import AutoModelForCausalLM, AutoTokenizer        

        self.model = AutoModelForCausalLM.from_pretrained(
            "vikhyatk/moondream2",
            revision=MODEL_REVISION,
            trust_remote_code=True,
            torch_dtype=self.torch_dtype,
        ).to(self.device)
        self.model.eval()
        tokenizer = AutoTokenizer.from_pretrained(
            "vikhyatk/moondream2", revision=MODEL_REVISION
        )
        return self.model, self.tokenizer

    def recognize_text(self, model, tokenizer, image: Image.Image) -> str:
        import torch
        image = image.convert("RGB")
        with torch.no_grad():
            result = model.query(image, OCR_PROMPT)
        # Newer moondream revisions return a dict like {"answer": "..."}
        if isinstance(result, dict):
            return result.get("answer", "")
        return str(result)

    def save_file(self, image_path, output_folder, text):
        image_path = Path(image_path)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        output_path = output_folder / f"{image_path.stem}-Moonbeam.txt"
        output_path.write_text(text, encoding="utf-8")

    def run(self, image_path: str = None, output: str = None):
        import torch
        
        print(f"Running {self.model_name} | input: {image_path}, output: {output}")
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        print(f"Using device: {self.device} with dtype: {self.torch_dtype}")

        folder = Path(image_path)
        output_folder = Path(output)
        model, tokenizer = self.get_model_and_tokenizer()

        for file in folder.glob("*.png"):
            image = Image.open(file)
            text = self.recognize_text(model, tokenizer, image)
            self.save_file(file, output_folder, text)
            print(f"Saved {file.stem}.txt")

        self.result = f"Moonbeam output for prompt: {input}"
        return self.result