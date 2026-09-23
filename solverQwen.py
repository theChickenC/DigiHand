from solverBase import SolverBase

class SolverQwen(SolverBase):
    """Qwen vision/language solver, inherits solverBase."""
    def __init__(self):
        super().__init__()
        self.model_name = "Qwen"

    def run(self, prompt: str, image_path: str = None):
        # Replace with your actual Qwen inference code
        print(f"Running {self.model_name} | prompt: {prompt}, image: {image_path}")
        self.result = f"Qwen output for prompt: {prompt}"
        return self.result