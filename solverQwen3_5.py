import os
import pymupdf
from pathlib import Path
from PIL import Image
from solverBase import SolverBase
from digiHandEnums import InputType
from digiHandTools import DigiHandTools

MODEL_ID = "Qwen/Qwen3.5-4B"
OCR_PROMPT = (
    "Transcribe all the handwritten text in this image exactly as written. "
    "Do not keep line breaks, put it into paragraph form. "
    "Do not summarize, translate, or correct spelling. "
    "Output only the transcription, nothing else."
)


class SolverQwen3_5(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Qwen3.5-4B"
        self.model = None
        self.processor = None
        # Initialize device + dtype HERE so they always exist
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    def get_model_and_processor(self):
        import torch
        if self.model is not None and self.processor is not None:
            return self.model, self.processor

        # Qwen3.5 is a vision-language model, so it must be loaded with
        # AutoModelForImageTextToText (AutoModelForCausalLM drops the vision side).
        from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

        # 4bit quantization config for RTX2070 Super
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID,
            quantization_config=bnb_config,
            dtype=self.torch_dtype,
            device_map=self.device,
        )
        self.model.eval()

        # Default processor settings. If you run out of VRAM, limit image size,
        # e.g. AutoProcessor.from_pretrained(MODEL_ID, min_pixels=256*28*28,
        # max_pixels=1280*28*28) -- check the model card for the exact kwargs.
        self.processor = AutoProcessor.from_pretrained(MODEL_ID)
        return self.model, self.processor

    def recognize_text(self, model, processor, image) -> str:
        import torch
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
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = processor(
            text=[text_prompt],
            images=[image],
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            # Pass ALL inputs (including pixel_values etc.) so the model sees the image
            generated_ids = model.generate(**inputs, max_new_tokens=2048)

        # generate() returns prompt + new tokens; strip the prompt before decoding
        trimmed = generated_ids[:, inputs["input_ids"].shape[1]:]
        output_text = processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        return output_text.strip()

    def run(self, input_type: InputType, input: str, output: str, initPage: int, on_file_saved=None, on_progress=None):
        if on_file_saved:
            on_file_saved(f"Using device: {self.device} with dtype: {self.torch_dtype}")
        folder_in = Path(input)
        folder_out = Path(output)
        folder_out.mkdir(parents=True, exist_ok=True)
        model, processor = self.get_model_and_processor()
        pages = []
        if input_type == InputType.PDF:
            pages = DigiHandTools.pdf_pages_to_images(folder_in)
            if not pages:
                print(f"WARNING: no images converted from {folder_in}")
            if on_progress and pages:
                on_progress(5, f"found {len(pages)} files")
        elif input_type == InputType.IMAGES:
            # sorted() so pages come out in a stable, predictable order
            images = sorted(
                f for f in folder_in.iterdir()
                if f.suffix.lower() in ('.png', '.jpg', '.jpeg')
            )
            print(images)
            if not images:
                print(f"WARNING: no images found in {folder_in}")
            if on_progress and images:
                on_progress(5, f"found {len(images)} files")
            for file in images:
                image = Image.open(file).convert("RGB")
                pages.append(image)
        else:
            return "Not a supported input file(s)."

        for i, page in enumerate(pages[initPage:]):
            text = self.recognize_text(model, processor, page)
            self.save_file(i + initPage, folder_out, text)
            msg = f"Saved page {initPage + i}.txt"
            print(msg)
            if on_file_saved:
                on_file_saved(msg)
            if on_progress:
                total_index = i + initPage
                progress_pct = int(100 * total_index / len(pages))
                on_progress(progress_pct, msg)
        self.result = f"Qwen3.5-4B output for prompt: {input}"
        return self.result