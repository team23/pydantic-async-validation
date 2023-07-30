from types import FunctionType
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Union

from pydantic.errors import PydanticUserError

from pydantic_async_validation.constants import ASYNC_FIELD_VALIDATOR_CONFIG_KEY, ASYNC_MODEL_VALIDATOR_CONFIG_KEY
from pydantic_async_validation.utils import make_generic_validator, prepare_validator


class Validator:
    """Helper / data class to store validator information."""

    __slots__ = ('func', 'skip_on_failure')

    def __init__(
        self,
        func: Callable,
        skip_on_failure: bool = False,
    ) -> None:
        self.func = func
        self.skip_on_failure = skip_on_failure


if TYPE_CHECKING:
    from inspect import Signature  # noqa

    from pydantic.main import BaseConfig  # noqa
    from pydantic.types import ModelOrDc  # noqa

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
    ValidatorListDict = dict[str, list[Validator]]


def async_field_validator(
    __field_name: str,
    /,
    *additional_field_names: str,
    allow_reuse: bool = False,
) -> Callable[[Callable], classmethod]:
    """
    Decorate methods on a model indicating that they should be used to validate data.

    This decorator allows you to assign your validation
    function to a list of fields.
    """

    if isinstance(__field_name, FunctionType):
        raise PydanticUserError(
            "validators should be used with fields and keyword arguments, "
            "not bare. "
            "E.g. usage should be `@async_field_validator('<field_name>', ...)`",
            code='validator-instance-method',
        )

    field_names: Tuple[str, ...] = __field_name, *additional_field_names

    def dec(func: Callable) -> classmethod:
        f_cls = prepare_validator(func, allow_reuse)
        setattr(
            f_cls,
            ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
            (
                field_names,
                Validator(
                    func=make_generic_validator(f_cls.__func__),
                ),
            ),
        )
        return f_cls

    return dec


def async_model_validator(
    *,
    allow_reuse: bool = False,
    skip_on_failure: bool = False,
) -> Union[classmethod, Callable[[Callable], classmethod]]:
    """
    Decorate methods on a model indicating that they should be used to validate data.

    This decorator allows you to assign your validation
    function to the whole model (root validator).
    """

    def dec(func: Callable) -> classmethod:
        f_cls = prepare_validator(func, allow_reuse)
        setattr(
            f_cls,
            ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
            Validator(
                func=f_cls.__func__,
                skip_on_failure=skip_on_failure,
            ),
        )
        return f_cls

    return dec
