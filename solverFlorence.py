import os
from pathlib import Path
from PIL import Image
from solverBase import SolverBase
from digiHandEnums import InputType
from digiHandTools import DigiHandTools

class SolverFlorence(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Florence2"

    def get_model_and_processor(self):
        from transformers import AutoProcessor, AutoModelForCausalLM 
        model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Florence-2-large",
            torch_dtype= self.torch_dtype,
            trust_remote_code=True,
            revision="main"  # or a specific commit hash for reproducibility
        ).to(self.device)

        processor = AutoProcessor.from_pretrained(
            "microsoft/Florence-2-large",
            trust_remote_code=True,
            revision="main"
        )
        return [model, processor]

    def recognize_text(self, model, processor, image) -> str:
        prompt = "<OCR>"
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(self.device, self.torch_dtype)
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=4096,
            num_beams=3,
            do_sample=False
        )

        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = processor.post_process_generation(generated_text, task=prompt, image_size=(image.width, image.height))

        return parsed_answer[prompt]

    def save_file(self, page_num, output_folder, text):
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        output_path = output_folder / f"page_{page_num}.txt"
        output_path.write_text(text, encoding="utf-8")


    def run(self, input_type: InputType, input: str, output: str, on_file_saved=None, on_progress=None):
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

        for i, page in enumerate(pages, 1):
            text = self.recognize_text(model, processor, page)
            self.save_file(i, folder_out, text)
            msg = f"Saved page {i}.txt"
            print(msg)                                  # still prints to console
            if on_file_saved:
                on_file_saved(msg)                      # ← this reaches the dialog
            if on_progress:
                on_progress(int(100 * i / len(pages)), msg)

        self.result = f"Florence output for prompt: {input}"
        
        return self.result