import pymupdf
from pathlib import Path
from PIL import Image
from solverBase import SolverBase
import pymupdf # only needed for PDF input

MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
OCR_PROMPT = (
    "Transcribe all the handwritten text in this image exactly as written, "
    "preserving line breaks. Do not summarize, translate, or correct spelling. "
    "Output only the transcription, nothing else."
)
MIN_PIXELS = 256 * 28 * 28
MAX_PIXELS = 1280 * 28 * 28

class SolverQwen(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Qwen2.5"
        self.model = None
        self.processor = None

    def get_model_and_processor(self):
        if self.model is not None and self.processor is not None:
            return self.model, self.processor
    
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL_ID,
            torch_dtype=self.torch_dtype,
            device_map=self.device,
        )
        self.model.eval()
        self.processor = AutoProcessor.from_pretrained(
            MODEL_ID,
            min_pixels=MIN_PIXELS,
            max_pixels=MAX_PIXELS,
        )
        return self.model, self.processor

    def recognize_text(self, model, processor, image_file_path: str) -> str:
        import torch
        from qwen_vl_utils import process_vision_info
        image = Image.open(image_file_path).convert("RGB")
    
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }
        ]
    
        text_prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
    
        inputs = processor(
            text=[text_prompt],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self.device)
    
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=2048)
    
        # Trim the prompt tokens off the front of the generated output
        trimmed_ids = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            trimmed_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        return output_text.strip()

    # wait this is good (multipage pdf to single page)
    # def pdf_to_images(self, pdf_path: Path, dpi: int = 300):
    #     doc = fitz.open(pdf_path)
    #     zoom = dpi / 72  # PDF default is 72 dpi
    #     matrix = fitz.Matrix(zoom, zoom)
    #     for i, page in enumerate(doc):
    #         pix = page.get_pixmap(matrix=matrix)
    #         img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    #         yield i, img
    #     doc.close()

    # def pdf_to_images(pdf_path: Path, dpi: int = 300):
    #     """Yield (page_index, PIL.Image) for each page of a PDF, rendered at dpi."""
    #     doc = fitz.open(pdf_path)
    #     zoom = dpi / 72  # PDF default is 72 dpi
    #     matrix = fitz.Matrix(zoom, zoom)
    #     for i, page in enumerate(doc):
    #         pix = page.get_pixmap(matrix=matrix)
    #         img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    #         yield i, img
    #     doc.close()

    def save_file(self, image_path, output_folder, text):
        image_path = Path(image_path)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        output_path = output_folder / f"{image_path.stem}-Qwen.txt"
        output_path.write_text(text, encoding="utf-8")

    def run(self, image_path: str = None, output: str = None, on_file_saved=None, on_progress=None):
        # print(f"Running {self.model_name} | input: {image_path}, output: {output}")
        # return
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        print(f"Using device: {self.device} with dtype: {self.torch_dtype}")

        folder = Path(image_path)
        output_folder = Path(output)
        model, processor = self.get_model_and_processor()

        files = [f for f in folder.iterdir()
                if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]   # ← see #2
        files.sort()
        if not files:
            print(f"WARNING: no images found in {folder}")
        if on_progress and files:
            on_progress(5, f"found {len(files)} files")

        for i, file in enumerate(files, 1):                    # i = 1-based index
            text = self.recognize_text(model, processor, file) # pass the path, not an Image
            self.save_file(file, output_folder, text)
            msg = f"Saved {file.stem}.txt"
            print(msg)                                          # console only
            if on_file_saved:
                on_file_saved(msg)                              # reaches the dialog
            if on_progress:
                on_progress(int(100 * i / len(files)), msg)

        self.result = f"Qwen output for prompt: {image_path}"
        return self.result