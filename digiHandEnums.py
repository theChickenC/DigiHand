from enum import Enum

class SolverType(Enum):
    # Keep in sync with DlgSolver.SOLVER_CLASSES and the combo box in main.py
    FLORENCE  = 0
    MOONDREAM = 1
    QWEN2_5   = 2
    QWEN3_5   = 3

class InputType(Enum):
    PDF = 0
    IMAGES = 1