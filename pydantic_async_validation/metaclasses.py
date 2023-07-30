from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from pydantic._internal._model_construction import ModelMetaclass  # noqa

from pydantic_async_validation.constants import (
    ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
    ASYNC_FIELD_VALIDATORS_KEY,
    ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
    ASYNC_MODEL_VALIDATORS_KEY,
)

if TYPE_CHECKING:
    from pydantic_async_validation.validators import Validator


class AsyncValidationModelMetaclass(ModelMetaclass):
    def __new__(
        mcs,
        name: str,
        bases: tuple[type],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        async_field_validators: List[Tuple[List[str], Validator]] = []
        async_model_validators: List[Validator] = []

        async_field_validator_fields: Optional[List[str]]
        async_field_validator_config: "Optional[Validator]"
        async_model_validator_config: "Optional[Validator]"

        for base in bases:
            async_field_validators += getattr(
                base,
                ASYNC_FIELD_VALIDATORS_KEY,
                [],
            )
            async_model_validators += getattr(
                base,
                ASYNC_MODEL_VALIDATORS_KEY,
                [],
            )

        for _attr_name, attr_value in namespace.items():
            # Register all validators
            async_field_validator_fields, async_field_validator_config = getattr(
                attr_value,
                ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
                (None, None),
            )
            if (
                async_field_validator_fields is not None
                and async_field_validator_config is not None
                and callable(async_field_validator_config.func)
            ):
                async_field_validators.append(attr_value)

            # Register all root validators
            async_model_validator_config = getattr(
                attr_value,
                ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
                None,
            )
            if (
                async_model_validator_config is not None
                and callable(async_model_validator_config.func)
            ):
                async_model_validators.append(attr_value)

        namespace[ASYNC_FIELD_VALIDATORS_KEY] = async_field_validators
        namespace[ASYNC_MODEL_VALIDATORS_KEY] = async_model_validators

        return super().__new__(mcs, name, bases, namespace, **kwargs)
