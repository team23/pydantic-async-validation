from typing import ClassVar, List, Tuple

import pydantic
from pydantic_core import ErrorDetails

from pydantic_async_validation.constants import (
    ASYNC_FIELD_VALIDATOR_CONFIG_KEY,
    ASYNC_FIELD_VALIDATORS_KEY,
    ASYNC_MODEL_VALIDATOR_CONFIG_KEY,
    ASYNC_MODEL_VALIDATORS_KEY,
)
from pydantic_async_validation.exceptions import AsyncValidationError
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
                        self.__class__,
                        getattr(self, field_name, None),
                        self,
                        field_name,
                        validator,
                    )
                except (ValueError, TypeError, AssertionError) as o_O:
                    validation_errors.append(
                        ErrorDetails(
                            type='value_error',
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
            if validator.skip_on_failure and validation_errors:
                continue
            try:
                await validator.func(self.__class__, self)
            except (ValueError, TypeError, AssertionError) as o_O:
                validation_errors.append(
                    ErrorDetails(
                        type='value_error',
                        msg=str(o_O),
                        loc=(),
                        input=self.__dict__,
                    ),
                )

        if len(validation_errors) > 0:
            raise AsyncValidationError(
                errors=validation_errors,
                model=self.__class__,
            )
