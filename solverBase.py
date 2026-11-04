from pathlib import Path
from abc import ABC, abstractmethod

from PIL import Image

from digiHandEnums import InputType
from digiHandTools import DigiHandTools


class SolverBase(ABC):
    """Shared OCR pipeline: enumerate pages, transcribe each, save page_N.txt.

    Concrete solvers implement load_model() and recognize_page() only.
    The page loop, device selection, progress reporting and saving live
    here so all backends behave identically.
    """

    def __init__(self):
        self.result = None
        self.model_name = ""
        self.device = None
        self.torch_dtype = None

    # ---- provided by concrete solvers ---------------------------------

    @abstractmethod
    def load_model(self):
        """Load (or reuse) model + processor. Must be cheap to call twice."""

    @abstractmethod
    def recognize_page(self, image) -> str:
        """Return the transcription for one PIL image."""

    # ---- shared helpers -------------------------------------------------

    def setup_device(self):
        import torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    @staticmethod
    def image_files(folder_in):
        # sorted() so pages come out in a stable, predictable order
        return sorted(
            f for f in Path(folder_in).iterdir()
            if f.suffix.lower() in (".png", ".jpg", ".jpeg")
        )

    def page_count(self, input_type, folder_in):
        if input_type == InputType.PDF:
            return DigiHandTools.pdf_page_count(folder_in)
        if input_type == InputType.IMAGES:
            return len(self.image_files(folder_in))
        return 0

    def iter_pages(self, input_type, folder_in, initPage=0):
        """Yield (page_number_0based, PIL.Image) lazily.

        Pages before initPage are skipped without being rendered or
        decoded, so memory stays O(1) per page instead of O(pages).
        """
        if input_type == InputType.PDF:
            yield from DigiHandTools.pdf_page_images(folder_in, start=initPage)
        else:
            for i, file in enumerate(self.image_files(folder_in)):
                if i < initPage:
                    continue
                yield i, Image.open(file).convert("RGB")

    def save_file(self, page_num, output_folder, text):
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        output_path = output_folder / f"page_{page_num}.txt"
        output_path.write_text(text, encoding="utf-8")

    def get_result(self):
        """Shared helper: return last inference result."""
        return self.result

    def clear_result(self):
        """Shared helper: reset stored result."""
        self.result = None

    # ---- shared run(): the whole OCR pass, identical for every backend --

    def run(self, input_type, input, output, initPage,
            on_file_saved=None, on_progress=None):
        log = on_file_saved if on_file_saved else (lambda msg: print(msg))
        self.setup_device()
        log(f"Using device: {self.device} with dtype: {self.torch_dtype}")

        if input_type not in (InputType.PDF, InputType.IMAGES):
            return "Not a supported input file(s)."

        folder_in = Path(input)
        folder_out = Path(output)
        folder_out.mkdir(parents=True, exist_ok=True)

        # Count before loading the model: an unreadable input fails fast,
        # before any large model download/load.
        total = self.page_count(input_type, folder_in)
        if total == 0:
            log(f"WARNING: no input pages found in {folder_in}")
        if on_progress and total:
            on_progress(5, f"found {total} files")

        self.load_model()

        todo = max(0, total - initPage)
        done = 0
        for page_num, image in self.iter_pages(input_type, folder_in, initPage):
            text = self.recognize_page(image)
            self.save_file(page_num, folder_out, text)
            msg = f"Saved page {page_num}.txt"
            log(msg)
            done += 1
            if on_progress and todo:
                on_progress(min(100, int(100 * done / todo)), msg)

        self.result = f"{self.model_name} output for prompt: {input}"
        return self.result