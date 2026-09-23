import os
from pathlib import Path
from PIL import Image
# from transformers import AutoProcessor, AutoModelForCausalLM 

# class solverBase(ABC):
class SolverBase():
    """Base abstract solver class, defines shared interface."""
    def __init__(self):
        self.result = None

    # @abstractmethod
    def run(self, prompt: str, image_path: str = None):
        """
        Abstract method to run model inference.
        Must be implemented by solverQwen and solverFlorence.
        """
        pass

    def get_result(self):
        """Shared helper: return last inference result."""
        return self.result

    def clear_result(self):
        """Shared helper: reset stored result."""
        self.result = None