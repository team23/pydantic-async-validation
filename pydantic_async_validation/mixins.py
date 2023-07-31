from typing import ClassVar, List, Tuple

import pydantic
from pydantic_core import ErrorDetails, PydanticCustomError, ValidationError

from pydantic_async_validation.constants import (
    ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
    ASYNC_FIELD_VALIDATORS_KEY,
    ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
    ASYNC_MODEL_VALIDATORS_KEY,
)
from pydantic_async_validation.metaclasses import AsyncValidationModelMetaclass
from pydantic_async_validation.validators import Validator


class AsyncValidationModelMixin(
    pydantic.BaseModel,
    metaclass=AsyncValidationModelMetaclass,
):
    # MUST match names defined in constants.py!
    pydantic_model_async_field_validators: ClassVar[List[Tuple[List[str], Validator]]]
    pydantic_model_async_model_validators: ClassVar[List[Validator]]

    async def model_async_validate(self) -> None:
        """
        Run async validation for the model instance.

        Will call all async field and async model validators. All errors will be
        collected and raised as a `ValidationError` exception.
        """
        field_names: list[str]
        validator: Validator

        validation_errors = []
        validators = getattr(self, ASYNC_FIELD_VALIDATORS_KEY, [])
        root_validators = getattr(self, ASYNC_MODEL_VALIDATORS_KEY, [])

        for validator_attr in validators:
            field_names, validator = getattr(
                validator_attr,
                ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
            )
            for field_name in field_names:
                try:
                    await validator.func(
                        self,
                        getattr(self, field_name, None),
                        field_name,
                        validator,
                    )
                except (ValueError, TypeError, AssertionError) as o_O:
                    validation_errors.append(
                        ErrorDetails(
                            type=PydanticCustomError('value_error', str(o_O)),
                            msg=str(o_O),
                            loc=(field_name,),
                            input=getattr(self, field_name, None),
                        ),
                    )

        for validator_attr in root_validators:
            validator = getattr(
                validator_attr,
                ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
            )
            try:
                await validator.func(
                    self,
                    validator,
                )
            except (ValueError, TypeError, AssertionError) as o_O:
                validation_errors.append(
                    ErrorDetails(
                        type=PydanticCustomError('value_error', str(o_O)),
                        msg=str(o_O),
                        loc=('__root__',),
                        input=self.__dict__,
                    ),
                )

        # TODO:
        # for attribute_name, attribute_value in self.__dict__.items():
        #     if isinstance(attribute_value, AsyncValidationModelMixin):
        #         await attribute_value.model_async_validate()

        if len(validation_errors) > 0:
            raise ValidationError.from_exception_data(
                self.__class__.__name__,
                validation_errors,
            )
