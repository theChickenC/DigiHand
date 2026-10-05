import os
import pymupdf
from pathlib import Path
from PIL import Image
from solverBase import SolverBase
from digiHandEnums import InputType
from digiHandTools import DigiHandTools

MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
OCR_PROMPT = (
    "Transcribe all the handwritten text in this image exactly as written, "
    "preserving line breaks. Do not summarize, translate, or correct spelling. "
    "Output only the transcription, nothing else."
)
MIN_PIXELS = 256 * 28 * 28
MAX_PIXELS = 1280 * 28 * 28

class SolverQwen2_5(SolverBase):
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
            dtype=self.torch_dtype,
            device_map=self.device,
        )
        self.model.eval()
        self.processor = AutoProcessor.from_pretrained(
            MODEL_ID,
            min_pixels=MIN_PIXELS,
            max_pixels=MAX_PIXELS,
        )
        return self.model, self.processor

    def recognize_text(self, model, processor, image) -> str:
        import torch
        from qwen_vl_utils import process_vision_info
        # image = Image.open(image_file_path).convert("RGB")
    
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


    def run(self, input_type: InputType, input: str, output: str, initPage: int, on_file_saved=None, on_progress=None):
        # print(f"Running {self.model_name} | input: {image_path}, output: {output}")
        # return
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
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
            #Warning: Does not parse the image folder in the correct order
            images = [f for f in folder_in.iterdir() if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]
            print(images)
            # images.sort()
            if not images:
                print(f"WARNING: no images found in {folder_in}")
            if on_progress and images:
                on_progress(5, f"found {len(images)} files")
            for i, file in enumerate(images, 1):
                image = Image.open(file).convert("RGB")
                pages.append(image)
        else:
            return "Not a supported input file(s)."
        
        for i, page in enumerate(pages[initPage:]):                    # i = 1-based index
            text = self.recognize_text(model, processor, page) # pass the path, not an Image
            self.save_file(i+initPage, folder_out, text)
            msg = f"Saved page {initPage + i}.txt"
            print(msg)                                  # still prints to console
            if on_file_saved:
                on_file_saved(msg)                      # ← this reaches the dialog
            if on_progress:
                on_progress(int(100 * i / (len(pages)) + initPage ), msg)

        self.result = f"Qwen output for prompt: {input}"
        return self.result