from solverBase import SolverBase

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

    def load_model(self):
        if self.model is not None and self.processor is not None:
            return

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

    def recognize_page(self, image) -> str:
        import torch
        from qwen_vl_utils import process_vision_info

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }
        ]

        text_prompt = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = self.processor(
            text=[text_prompt],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=2048)

        # Trim the prompt tokens off the front of the generated output
        trimmed_ids = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            trimmed_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        return output_text.strip()