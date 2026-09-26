import os
from pathlib import Path
from PIL import Image
from solverBase import SolverBase

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

    def recognize_text(self, model, processor, image_file_path: str) -> str:
        image = Image.open(image_file_path).convert("RGB")
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

    def save_file(self, image_path, output_folder, text):
        image_path = Path(image_path)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        output_path = output_folder / f"{image_path.stem}-Florence.txt"
        output_path.write_text(text, encoding="utf-8")


    # def run(self, image_path: str = None, output: str = None):
    #     # print(f"Running {self.model_name} | input: {image_path}, output: {output}")
    #     # return
    #     import torch
    #     self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
    #     self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    #     print(f"Using device: {self.device} with dtype: {self.torch_dtype}")


    #     folder = Path(image_path)
    #     output_folder = Path(output)
    #     model, processor = self.get_model_and_processor()

    #     for file in folder.glob("*.png"):
    #         text = self.recognize_text(model, processor, file)
    #         self.save_file(file, output_folder, text)
    #         print(f"Saved {file.stem}.txt")

    #     self.result = f"Florence output for prompt: {input}"
    #     return self.result
    def run(self, image_path=None, output=None, on_file_saved=None, on_progress=None):
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        print(f"Using device: {self.device} with dtype: {self.torch_dtype}")

        folder = Path(image_path)
        output_folder = Path(output)
        output_folder.mkdir(parents=True, exist_ok=True)

        files = [f for f in folder.iterdir()
                if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]   # ← see #2
        files.sort()
        if not files:
            print(f"WARNING: no images found in {folder}")
        if on_progress and files:
            on_progress(5, f"found {len(files)} files")

        model, processor = self.get_model_and_processor()

        for i, file in enumerate(files, 1):
            text = self.recognize_text(model, processor, file)
            self.save_file(file, output_folder, text)
            msg = f"Saved {file.stem}.txt"
            print(msg)                                  # still prints to console
            if on_file_saved:
                on_file_saved(msg)                      # ← this reaches the dialog
            if on_progress:
                on_progress(int(100 * i / len(files)), msg)

        self.result = f"Florence output for prompt: {image_path}"
        return self.result