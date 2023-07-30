from functools import wraps
from inspect import Signature
from typing import Callable

import pydantic
from pydantic import PydanticUserError

_ASYNC_VALIDATOR_FUNCS: set[str] = set()


def prepare_validator(function: Callable, allow_reuse: bool = False) -> classmethod:
    """
    Return the function as classmethod and check for duplicate names.

    Avoid validators with duplicated names since without this,
    validators can be overwritten silently
    which generally isn't the intended behaviour,
    don't run in ipython (see #312) or if allow_reuse is False.
    """
    f_cls = (
        function
        if isinstance(function, classmethod)
        else classmethod(function)
    )
    if not allow_reuse:
        ref = f_cls.__func__.__module__ + '.' + f_cls.__func__.__qualname__
        if ref in _ASYNC_VALIDATOR_FUNCS:
            raise pydantic.ConfigError(
                f'Duplicate validator function "{ref}"; if this is intended, '
                f'set `allow_reuse=True`',
            )
        _ASYNC_VALIDATOR_FUNCS.add(ref)
    return f_cls


def make_generic_validator(validator: Callable) -> Callable:
    """
    Make a generic function which calls a validator with the right arguments.

    Unfortunately other approaches
    (eg. return a partial of a function that builds the arguments) is slow,
    hence this laborious way of doing things.

    It's done like this so validators don't all need **kwargs in
    their signature, eg. any combination of
    the arguments "values", "fields" and/or "config" are permitted.
    """
    from inspect import signature  # noqa

    sig = signature(validator)
    args = list(sig.parameters.keys())
    first_arg = args.pop(0)
    if first_arg == 'self':
        raise PydanticUserError(
            f'Invalid signature for validator {validator}: {sig},'
            f'"self" not permitted as first argument, '
            f'should be: (cls, value, instance, config, field), '
            f'"instance", "config" and "field" are all optional.',
            code='validator-signature',
        )
    return wraps(validator)(
        generic_validator_cls(validator, sig, set(args[1:])),
    )


all_kwargs = {'instance', 'field', 'config'}


def generic_validator_cls(
    validator: Callable,
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

    if not args.issubset(all_kwargs):
        raise PydanticUserError( # noqa
            f'Invalid signature for validator {validator}: {sig}, '
            f'should be: '
            f'(cls, value, instance, config, field), '
            f'"instance", "config" and "field" are all optional.',
            code='validator-signature',
        )

    if has_kwargs:
        return lambda cls, v, instance, field, config: validator(
            cls, v, instance=instance, field=field, config=config,
        )
    if args == set():
        return lambda cls, v, instance, field, config: validator(cls, v)
    if args == {'instance'}:
        return lambda cls, v, instance, field, config: validator(
            cls, v, instance=instance,
        )
    if args == {'field'}:
        return lambda cls, v, instance, field, config: validator(
            cls, v, field=field,
        )
    if args == {'config'}:
        return lambda cls, v, instance, field, config: validator(
            cls, v, config=config,
        )
    if args == {'instance', 'field'}:
        return lambda cls, v, instance, field, config: validator(
            cls, v, instance=instance, field=field,
        )
    if args == {'instance', 'config'}:
        return lambda cls, v, instance, field, config: validator(
            cls, v, instance=instance, config=config,
        )
    if args == {'field', 'config'}:
        return lambda cls, v, instance, field, config: validator(
            cls, v, field=field, config=config,
        )

    # args == {'instance', 'field', 'config'}
    return lambda cls, v, instance, field, config: validator(
        cls, v, instance=instance, field=field, config=config,
    )
