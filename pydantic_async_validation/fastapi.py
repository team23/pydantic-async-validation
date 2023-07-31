from collections.abc import Callable
from typing import Any, Type, Union

from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


class ensure_request_validation_errors():
    """
    Converter for `ValidationError` to `RequestValidationError`.

    This will convert any ValidationError's inside the called code into
    RequestValidationErrors which will trigger HTTP 422 responses in
    FastAPI. This is useful for when you want to do extra validation in
    your code that is not covered by FastAPI's normal request parameter
    handling.

    Usage examples:

    ```python
    # Use as a decorator
    @ensure_request_validation_errors
    def some_func():
        some_code_doing_extra_validation()  # for example async validation
    ```

    ```python
    # Use as a context manager
    with ensure_request_validation_errors():
        some_code_doing_extra_validation()  # for example async validation
    ```
    """

    func: Union[Callable, None]

    def __init__(self, func: Union[Callable, None] = None) -> None:
        self.func = func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.func is None:
            raise RuntimeError("No func given")

        with self:
            return self.func(*args, **kwargs)

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: Union[Type[Exception], None],
        exc_value: Union[Exception, None],
        traceback: Any,
    ) -> None:
        if exc_value is None:
            return

        if isinstance(exc_value, ValidationError):
            raise RequestValidationError(errors=exc_value.errors())
