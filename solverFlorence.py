from solverBase import SolverBase

MODEL_ID = "microsoft/Florence-2-large"

class SolverFlorence(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Florence2"
        self.model = None
        self.processor = None

    def load_model(self):
        if self.model is not None and self.processor is not None:
            return
        from transformers import AutoProcessor, AutoModelForCausalLM
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=self.torch_dtype,
            trust_remote_code=True,
            revision="main",  # or a specific commit hash for reproducibility
        ).to(self.device)
        self.processor = AutoProcessor.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            revision="main",
        )
        self.model.eval()

    def recognize_page(self, image) -> str:
        import torch
        prompt = "<OCR>"
        inputs = self.processor(
            text=prompt, images=image, return_tensors="pt"
        ).to(self.device, self.torch_dtype)
        with torch.no_grad():
            generated_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=4096,
                num_beams=3,
                do_sample=False,
            )
        generated_text = self.processor.batch_decode(
            generated_ids, skip_special_tokens=False)[0]
        parsed_answer = self.processor.post_process_generation(
            generated_text, task=prompt, image_size=(image.width, image.height))
        return parsed_answer[prompt]