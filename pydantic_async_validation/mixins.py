from typing import ClassVar, List, Tuple, Union

import pydantic
from pydantic_core import InitErrorDetails, PydanticCustomError, ValidationError

from pydantic_async_validation.constants import (
    ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
    ASYNC_FIELD_VALIDATORS_KEY,
    ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
    ASYNC_MODEL_VALIDATORS_KEY,
)
from pydantic_async_validation.metaclasses import AsyncValidationModelMetaclass
from pydantic_async_validation.utils import prefix_errors
from pydantic_async_validation.validators import ValidationInfo


class AsyncValidationModelMixin(
    pydantic.BaseModel,
    metaclass=AsyncValidationModelMetaclass,
):
    # MUST match names defined in constants.py!
    pydantic_model_async_field_validators: ClassVar[List[Tuple[List[str], ValidationInfo]]]
    pydantic_model_async_model_validators: ClassVar[List[ValidationInfo]]

    async def model_async_validate(self) -> None:
        """
        Run async validation for the model instance.

        Will call all async field and async model validators. All errors will be
        collected and raised as a `ValidationError` exception.
        """
        field_names: list[str]
        field_validator: ValidationInfo
        model_validator: ValidationInfo

        validation_errors = []
        field_validators = getattr(self, ASYNC_FIELD_VALIDATORS_KEY, [])
        model_validators = getattr(self, ASYNC_MODEL_VALIDATORS_KEY, [])

        # Call all field validators
        for field_validator_attr in field_validators:
            field_names, field_validator = getattr(
                field_validator_attr,
                ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
            )
            for field_name in field_names:
                try:
                    await field_validator.func(
                        self,
                        getattr(self, field_name, None),
                        field_name,
                        field_validator,
                    )
                except (ValueError, AssertionError) as o_O:
                    validation_errors.append(
                        InitErrorDetails(
                            type=PydanticCustomError('value_error', str(o_O)),  # type: ignore
                            loc=(field_name,),
                            input=getattr(self, field_name, None),
                        ),
                    )

        # Call all model validators
        for model_validator_attr in model_validators:
            model_validator = getattr(
                model_validator_attr,
                ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
            )
            try:
                await model_validator.func(
                    self,
                    model_validator,
                )
            except (ValueError, AssertionError) as o_O:
                validation_errors.append(
                    InitErrorDetails(
                        type=PydanticCustomError('value_error', str(o_O)),  # type: ignore
                        loc=('__root__',),
                        input=self.__dict__,
                    ),
                )

        # Also call async validation on attribute values
        async def extend_with_validation_errors_by(
            prefix: Tuple[Union[int, str], ...],
            instance: AsyncValidationModelMixin,
        ) -> None:
            try:
                await instance.model_async_validate()
            except ValidationError as O_o:
                validation_errors.extend(
                    prefix_errors(
                        prefix,
                        O_o.errors(),
                    ),
                )

        for attribute_name, attribute_value in self.__dict__.items():
            # Direct child instance
            if isinstance(attribute_value, AsyncValidationModelMixin):
                await extend_with_validation_errors_by(
                    (attribute_name,),
                    attribute_value,
                )
            # List of child instances
            if isinstance(attribute_value, list):
                for index, item in enumerate(attribute_value):
                    if isinstance(item, AsyncValidationModelMixin):
                        await extend_with_validation_errors_by(
                            (attribute_name, index),
                            item,
                        )
            # Dict of child instances
            if isinstance(attribute_value, dict):
                for key, item in attribute_value.items():
                    if isinstance(item, AsyncValidationModelMixin):
                        await extend_with_validation_errors_by(
                            (attribute_name, key),
                            item,
                        )

        # If some errors did occur, raise them as a ValidationError
        if len(validation_errors) > 0:
            raise ValidationError.from_exception_data(
                self.__class__.__name__,
                validation_errors,
            )
