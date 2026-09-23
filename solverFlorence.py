import os
from pathlib import Path
from PIL import Image
# import torch
from solverBase import SolverBase

class SolverFlorence(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Florence"

    def get_model_and_processor(self):
        from transformers import AutoProcessor, AutoModelForCausalLM 
        model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Florence-2-large",
            torch_dtype=torch_dtype,
            trust_remote_code=True,
            revision="main"  # or a specific commit hash for reproducibility
        ).to(device)

        processor = AutoProcessor.from_pretrained(
            "microsoft/Florence-2-large",
            trust_remote_code=True,
            revision="main"
        )
        return [model, processor]

    def recognize_text(self, model, processor, image_file_path: str) -> str:
        image = Image.open(image_file_path).convert("RGB")
        prompt = "<OCR>"
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(device, torch_dtype)
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

    def save_file(self, image_path, output_folder, text):
        image_path = Path(image_path)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        output_path = output_folder / f"{image_path.stem}-Florence.txt"
        output_path.write_text(text, encoding="utf-8")


    def run(self, image_path: str = None, output: str = None):
        print(f"Running {self.model_name} | input: {image_path}, output: {output}")
        # device = "cuda:0" if torch.cuda.is_available() else "cpu"
        # torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        # print(f"Using device: {device} with dtype: {torch_dtype}")


        folder = Path(image_path)
        output_folder = Path(output)
        model, processor = self.get_model_and_processor()

        for file in folder.glob("*.png"):
            text = self.recognize_text(model, processor, file)
            self.save_file(file, output_folder, text)
            print(f"Saved {file.stem}.txt")

        self.result = f"Florence output for prompt: {input}"
        return self.result
    