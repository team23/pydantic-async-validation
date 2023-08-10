from contextlib import contextmanager
from typing import Generator

from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


@contextmanager
def ensure_request_validation_errors() -> Generator[None, None, None]:
    """
    Converter for `ValidationError` to `RequestValidationError`.

    This will convert any ValidationError's inside the called code into
    RequestValidationErrors which will trigger HTTP 422 responses in
    FastAPI. This is useful for when you want to do extra validation in
    your code that is not covered by FastAPI's normal request parameter
    handling.

    Usage examples:

    ```python
    # Use as a context manager
    with ensure_request_validation_errors():
        some_code_doing_extra_validation()  # for example async validation
    ```
    """

    try:
        yield
    except ValidationError as O_o:
        raise RequestValidationError(errors=O_o.errors()) from O_o
