from solverBase import SolverBase

MODEL_ID = "Qwen/Qwen3.5-4B"
OCR_PROMPT = (
    "Transcribe all the handwritten text in this image exactly as written. "
    "Do not keep line breaks, put it into paragraph form. "
    "Do not summarize, translate, or correct spelling. "
    "Output only the transcription, nothing else."
)
MIN_PIXELS = 256 * 28 * 28
MAX_PIXELS = 1280 * 28 * 28


class SolverQwen3_5(SolverBase):
    def __init__(self):
        super().__init__()
        self.model_name = "Qwen3.5-4B"
        self.model = None
        self.processor = None

    def load_model(self):
        import torch
        if self.model is not None and self.processor is not None:
            return

        # Qwen3.5 is a vision-language model, so it must be loaded with
        # AutoModelForImageTextToText (AutoModelForCausalLM drops the vision side).
        from transformers import AutoModelForImageTextToText, AutoProcessor

        # 4-bit quantization keeps this on an RTX 2070 Super, but
        # bitsandbytes is an optional dependency: without it, fall back to
        # fp16 instead of crashing the whole solve.
        quantization_config = None
        try:
            import bitsandbytes  # noqa: F401
            from transformers import BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        except ImportError:
            print("WARNING: bitsandbytes not installed; loading Qwen3.5 "
                  "unquantized (needs more VRAM). pip install bitsandbytes for the 4-bit path.")

        load_kwargs = {"device_map": self.device}
        if quantization_config is not None:
            load_kwargs["quantization_config"] = quantization_config
        else:
            load_kwargs["dtype"] = self.torch_dtype

        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID, **load_kwargs)
        self.model.eval()

        # Limit image resolution to keep VRAM in check; if this processor
        # build rejects the kwargs, retry with defaults rather than failing.
        try:
            self.processor = AutoProcessor.from_pretrained(
                MODEL_ID, min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS)
        except TypeError:
            self.processor = AutoProcessor.from_pretrained(MODEL_ID)

    def recognize_page(self, image) -> str:
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
        text_prompt = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self.processor(
            text=[text_prompt],
            images=[image],
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            # Pass ALL inputs (including pixel_values etc.) so the model sees the image
            generated_ids = self.model.generate(**inputs, max_new_tokens=2048)

        # generate() returns prompt + new tokens; strip the prompt before decoding
        trimmed = generated_ids[:, inputs["input_ids"].shape[1]:]
        output_text = self.processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        return output_text.strip()