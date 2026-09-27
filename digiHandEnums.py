from enum import Enum

class SolverType(Enum):
    FLORENCE  = 0
    MOONBEAM  = 1
    QWEN      = 2

class InputType(Enum):
    PDF = 0
    IMAGES = 1