import os
from pathlib import Path
from PIL import Image
import pymupdf # only needed for PDF input
from solverBase import SolverBase
from digiHandEnums import InputType

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
            dtype=self.torch_dtype,
        ).to(self.device)
        self.model.eval()
        # assign to self.tokenizer, otherwise the cache check above never hits
        # and the tokenizer is rebuilt (and the model reloaded) on every call
        self.tokenizer = AutoTokenizer.from_pretrained(
            "vikhyatk/moondream2", revision=MODEL_REVISION
        )
        return self.model, self.tokenizer

    def recognize_text(self, model, tokenizer, image) -> str:
        import torch

        with torch.no_grad():
            result = model.query(image, OCR_PROMPT)
        # Newer moondream revisions return a dict like {"answer": "..."}
        if isinstance(result, dict):
            return result.get("answer", "")
        return str(result)

    def run(self, input_type: InputType, input: str, output: str, initPage: int,
            on_file_saved=None, on_progress=None):
        import torch
        from digiHandTools import DigiHandTools
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        if on_file_saved:
            on_file_saved(f"Using device: {self.device} with dtype: {self.torch_dtype}")

        folder_in = Path(input)
        output_folder = Path(output)
        output_folder.mkdir(parents=True, exist_ok=True)
        model, tokenizer = self.get_model_and_tokenizer()

        pages = []
        if input_type == InputType.PDF:
            pages = DigiHandTools.pdf_pages_to_images(folder_in)
            if not pages:
                print(f"WARNING: no images converted from {folder_in}")
        elif input_type == InputType.IMAGES:
            images = sorted(
                f for f in folder_in.iterdir()
                if f.suffix.lower() in (".png", ".jpg", ".jpeg")
            )
            for file in images:
                pages.append(Image.open(file).convert("RGB"))
        else:
            return "Not a supported input file(s)."

        if on_progress and pages:
            on_progress(5, f"found {len(pages)} files")

        todo = pages[initPage:]
        for i, page in enumerate(todo):
            text = self.recognize_text(model, tokenizer, page)
            self.save_file(i + initPage, output_folder, text)
            msg = f"Saved page {initPage + i}.txt"
            print(msg)
            if on_file_saved:
                on_file_saved(msg)
            if on_progress and todo:
                on_progress(min(100, int(100 * (i + 1) / len(todo))), msg)

        self.result = f"Moondream output for prompt: {input}"
        return self.result