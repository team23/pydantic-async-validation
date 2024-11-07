from types import FunctionType
from typing import TYPE_CHECKING, Any, Callable, Optional

from pydantic.errors import PydanticUserError

from pydantic_async_validation.constants import ASYNC_FIELD_VALIDATOR_CONFIG_KEY, ASYNC_MODEL_VALIDATOR_CONFIG_KEY
from pydantic_async_validation.utils import make_generic_field_validator, make_generic_model_validator

if TYPE_CHECKING:  # pragma: no cover
    from inspect import Signature  # noqa

    from pydantic.main import BaseConfig
    from pydantic.types import ModelOrDc

    ValidatorCallable = Callable[
        [
            Optional[ModelOrDc],
            Any,
            dict[str, Any],
            str,
            type[BaseConfig],
        ],
        Any,
    ]

    ValidatorsList = list[ValidatorCallable]
    ValidatorListDict = "dict[str, list[Validator]]"


class ValidationInfo:
    """Helper / data class to store validator information."""

    __slots__ = ('func', 'extra')

    def __init__(
        self,
        func: Callable,
        *,
        extra: Optional[dict[str, Any]] = None,

    ) -> None:
        self.func = func
        self.extra = extra if extra is not None else {}


def async_field_validator(
    __field_name: str,
    /,
    *additional_field_names: str,
    **extra: Any,
) -> Callable[[Callable], Callable]:
    """
    Decorate methods on a model indicating that they should be used to validate data.

    This decorator allows you to assign your validation
    function to a list of fields.
    """

    if isinstance(__field_name, FunctionType):
        raise PydanticUserError(
            "Validators should be used with fields and keyword arguments, "
            "not bare. "
            "E.g. usage should be `@async_field_validator('<field_name>', ...)`",
            code='validator-instance-method',
        )

    field_names: tuple[str, ...] = __field_name, *additional_field_names

    def dec(func: Callable) -> Callable:
        setattr(
            func,
            ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
            (
                field_names,
                ValidationInfo(
                    func=make_generic_field_validator(func),
                    extra=extra,
                ),
            ),
        )
        return func

    return dec


def async_model_validator(
    **extra: Any,
) -> Callable[[Callable], Callable]:
    """
    Decorate methods on a model indicating that they should be used to validate data.

    This decorator allows you to assign your validation
    function to the whole model (root validator).
    """

    def dec(func: Callable) -> Callable:
        setattr(
            func,
            ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
            ValidationInfo(
                func=make_generic_model_validator(func),
                extra=extra,
            ),
        )
        return func

    return dec
