import io
import os
from pathlib import Path
from PIL import Image
from digiHandEnums import InputType
from abc import ABC, abstractmethod
# from transformers import AutoProcessor, AutoModelForCausalLM 

# class solverBase(ABC):
class SolverBase():
    """Base abstract solver class, defines shared interface."""
    def __init__(self):
        self.result = None

    @abstractmethod
    def run(self, input_type: InputType, input: str, output: str, on_file_saved=None, on_progress=None):
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