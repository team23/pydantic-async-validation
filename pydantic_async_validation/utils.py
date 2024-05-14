from functools import wraps
from inspect import Signature, signature
from typing import Callable, List, Tuple, Union, cast

from pydantic import PydanticUserError
from pydantic_core import ErrorDetails, InitErrorDetails, PydanticCustomError


def make_generic_field_validator(validator_func: Callable) -> Callable:
    """
    Make a generic function which calls a field validator with the right arguments.
    """

    sig = signature(validator_func)
    args = list(sig.parameters.keys())
    first_arg = args.pop(0)
    if first_arg == 'cls':
        raise PydanticUserError(
            f'Invalid signature for validator {validator_func}: {sig},'
            f'"cls" not permitted as first argument, '
            f'should be: (self, value, field, config), '
            f'"value", "field" and "config" are all optional.',
            code='validator-signature',
        )
    return wraps(validator_func)(
        generic_field_validator_wrapper(
            validator_func,
            sig,
            set(args),
        ),
    )


all_field_validator_kwargs = {'value', 'field', 'config'}


def generic_field_validator_wrapper(
    validator_func: Callable,
    sig: 'Signature',
    args: set[str],
) -> Callable:
    """
    Return a helper function to wrap a method to be called with its defined parameters.
    """
    # assume the first argument is value
    has_kwargs = False
    if 'kwargs' in args:
        has_kwargs = True
        args -= {'kwargs'}

    if not args.issubset(all_field_validator_kwargs):
        raise PydanticUserError(
            f'Invalid signature for validator {validator_func}: {sig}, '
            f'should be: '
            f'(self, value, field, config), '
            f'"value", "field" and "config" are all optional.',
            code='validator-signature',
        )

    if has_kwargs:
        return lambda self, value, field, config: validator_func(
            self, value=value, field=field, config=config,
        )
    if args == set():
        return lambda self, value, field, config: validator_func(  # noqa: ARG005
            self,
        )
    if args == {'value'}:
        return lambda self, value, field, config: validator_func(  # noqa: ARG005
            self, value=value,
        )
    if args == {'field'}:
        return lambda self, value, field, config: validator_func(  # noqa: ARG005
            self, field=field,
        )
    if args == {'value', 'field'}:
        return lambda self, value, field, config: validator_func(  # noqa: ARG005
            self, value=value, field=field,
        )
    if args == {'config'}:
        return lambda self, value, field, config: validator_func(  # noqa: ARG005
            self, config=config,
        )
    if args == {'value', 'config'}:
        return lambda self, value, field, config: validator_func(  # noqa: ARG005
            self, value=value, config=config,
        )
    if args == {'field', 'config'}:
        return lambda self, value, field, config: validator_func(  # noqa: ARG005
            self, field=field, config=config,
        )

    # args == {'value', 'field', 'config'}
    return lambda self, value, field, config: validator_func(
        self, value=value, field=field, config=config,
    )


def make_generic_model_validator(validator_func: Callable) -> Callable:
    """
    Make a generic function which calls a model validator with the right arguments.
    """

    sig = signature(validator_func)
    args = list(sig.parameters.keys())
    first_arg = args.pop(0)
    if first_arg == 'cls':
        raise PydanticUserError(
            f'Invalid signature for validator {validator_func}: {sig},'
            f'"cls" not permitted as first argument, '
            f'should be: (self, config), '
            f'"config" is optional.',
            code='validator-signature',
        )
    return wraps(validator_func)(
        generic_model_validator_wrapper(
            validator_func,
            sig,
            set(args),
        ),
    )


all_model_validator_kwargs = {'config'}


def generic_model_validator_wrapper(
    validator_func: Callable,
    sig: 'Signature',
    args: set[str],
) -> Callable:
    """
    Return a helper function to wrap a method to be called with its defined parameters.
    """
    # assume the first argument is value
    has_kwargs = False
    if 'kwargs' in args:
        has_kwargs = True
        args -= {'kwargs'}

    if not args.issubset(all_model_validator_kwargs):
        raise PydanticUserError(
            f'Invalid signature for validator {validator_func}: {sig}, '
            f'should be: '
            f'(self, config), '
            f'"config" is optional.',
            code='validator-signature',
        )

    if has_kwargs:
        return lambda self, config: validator_func(
            self, config=config,
        )
    if args == set():
        return lambda self, config: validator_func(  # noqa: ARG005
            self,
        )

    # args == {'validator'}
    return lambda self, config: validator_func(
        self, config=config,
    )


def prefix_errors(
    prefix: Tuple[Union[int, str], ...],
    errors: Union[List[InitErrorDetails], List[ErrorDetails]],
) -> List[InitErrorDetails]:
    """
    Extend all errors passed as list to include an additional prefix.

    This is used to prefix errors occuring in child classes to include the parents
    field details in the error locations.
    """

    return [
        cast(
            InitErrorDetails,
            {
                # Original data is ErrorDetails, we need to convert it back to
                # InitErrorDetails
                **error,
                'type': (
                    PydanticCustomError(
                        error['type'],  # type: ignore
                        cast(ErrorDetails, error)['msg'],  # type: ignore
                    )
                    if isinstance(error['type'], str)
                    else error['type']
                ),
                'loc': (*prefix, *error['loc']),
            },
        )
        if "msg" in error
        else cast(
            InitErrorDetails,
            {
                # Original data is InitErrorDetails, all fine
                **error,
                'loc': (*prefix, *error.get('loc', [])),
            },
        )
        for error
        in errors
    ]
