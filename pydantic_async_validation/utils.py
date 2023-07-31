from functools import wraps
from inspect import Signature, signature
from typing import Callable

from pydantic import PydanticUserError


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
            f'"field" and "config" are all optional.',
            code='validator-signature',
        )
    return wraps(validator_func)(
        generic_field_validator_wrapper(
            validator_func,
            sig,
            set(args[1:]),
        ),
    )


all_field_validator_kwargs = {'field', 'validator'}


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
        raise PydanticUserError( # noqa
            f'Invalid signature for validator {validator_func}: {sig}, '
            f'should be: '
            f'(self, value, field, config), '
            f'"field" and "config" are all optional.',
            code='validator-signature',
        )

    if has_kwargs:
        return lambda self, v, field, config: validator_func(
            self, v, field=field, config=config,
        )
    if args == set():
        return lambda self, v, field, config: validator_func(
            self, v,
        )
    if args == {'field'}:
        return lambda self, v, field, config: validator_func(
            self, v, field=field,
        )
    if args == {'config'}:
        return lambda self, v, field, config: validator_func(
            self, v, config=config,
        )

    # args == {'field', 'validator'}
    return lambda self, v, field, config: validator_func(
        self, v, field=field, config=config,
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
            set(args[1:]),
        ),
    )


all_model_validator_kwargs = {'validator'}


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
        raise PydanticUserError( # noqa
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
        return lambda self, config: validator_func(
            self,
        )

    # args == {'validator'}
    return lambda self, config: validator_func(
        self, config=config,
    )
