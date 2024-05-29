from contextlib import contextmanager
from typing import Generator, List, Optional, Tuple, Union

from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from pydantic_core import ErrorDetails


def _prefix_request_errors(
    prefix: Tuple[Union[int, str], ...],
    errors: List[ErrorDetails],
) -> List[ErrorDetails]:
    """Add prefix to errors in preparation for request validation error conversion."""

    return [
        {
            **error,
            # Just add prefix
            'loc': (*prefix, *error.get('loc', [])),
        }
        for error
        in errors
    ]


@contextmanager
def ensure_request_validation_errors(
    prefix: Optional[Union[Tuple[Union[int, str], ...], str]] = None,
) -> Generator[None, None, None]:
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
        prepared_errors = O_o.errors(include_url=False)

        if prefix is None:
            raise RequestValidationError(errors=prepared_errors) from O_o

        if isinstance(prefix, str):
            prefix = (prefix,)

        raise RequestValidationError(
            errors=_prefix_request_errors(prefix, prepared_errors),
        ) from O_o
