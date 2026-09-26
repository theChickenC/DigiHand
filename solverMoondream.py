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

class SolverMoondream(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Moondream2"
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

    def recognize_text(self, model, tokenizer, image_file_path: str) -> str:
        import torch
        image = Image.open(image_file_path).convert("RGB")

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

        output_path = output_folder / f"{image_path.stem}-Moondream.txt"
        output_path.write_text(text, encoding="utf-8")

    def run(self, image_path: str = None, output: str = None, on_file_saved=None, on_progress=None):
        # print(f"Running {self.model_name} | input: {image_path}, output: {output}")
        # return
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        on_file_saved(f"Using device: {self.device} with dtype: {self.torch_dtype}")

        folder = Path(image_path)
        output_folder = Path(output)
        model, tokenizer = self.get_model_and_tokenizer()

        files = [f for f in folder.iterdir()
                if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]   # ← see #2
        files.sort()
        if not files:
            print(f"WARNING: no images found in {folder}")
        if on_progress and files:
            on_progress(5, f"found {len(files)} files")

        for i, file in enumerate(files, 1):                    # i = 1-based index
            text = self.recognize_text(model, tokenizer, file) # pass the path, not an Image
            self.save_file(file, output_folder, text)
            msg = f"Saved {file.stem}.txt"
            print(msg)                                          # console only
            if on_file_saved:
                on_file_saved(msg)                              # reaches the dialog
            if on_progress:
                on_progress(int(100 * i / len(files)), msg)

        self.result = f"Moondream output for prompt: {input}"
        return self.result