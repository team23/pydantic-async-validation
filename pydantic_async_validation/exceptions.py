from typing import List, Type

import pydantic
from pydantic_core import ErrorDetails


class AsyncValidationError(ValueError):
    def __init__(self, errors: List[ErrorDetails], model: Type[pydantic.BaseModel]) -> None:
        self._errors = errors
        self._model = model

    def errors(self) -> List[ErrorDetails]:
        return self._errors
