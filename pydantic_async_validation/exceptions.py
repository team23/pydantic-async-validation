from typing import List, Type

import pydantic
from pydantic_core import ErrorDetails


class AsyncValidationError(ValueError):
    def __init__(self, errors: List[ErrorDetails], model: Type[pydantic.BaseModel]) -> None:
        self.errors = errors
        self.model = model
