from typing import Any, Dict, List

import pydantic
import pytest
from pydantic.errors import PydanticUserError

from pydantic_async_validation import AsyncValidationModelMixin, async_field_validator
from pydantic_async_validation.validators import ValidationInfo


class SomethingModel(AsyncValidationModelMixin, pydantic.BaseModel):
    name: str
    age: int

    @async_field_validator('name')
    async def validate_name(self, value: str) -> None:
        if value == "invalid":
            raise ValueError("Invalid name")


@pytest.mark.asyncio
async def test_async_validation_raises_no_issues():
    instance = SomethingModel(name="valid", age=1)
    await instance.model_async_validate()


@pytest.mark.asyncio
async def test_async_validation_raises_when_validation_fails():
    instance = SomethingModel(name="invalid", age=1)
    with pytest.raises(pydantic.ValidationError):
        await instance.model_async_validate()


@pytest.mark.asyncio
async def test_all_field_validator_combinations_are_valid():
    class OtherModel(AsyncValidationModelMixin, pydantic.BaseModel):
        name: str

        @async_field_validator('name')
        async def validate_name_1(self) -> None: pass

        @async_field_validator('name')
        async def validate_name_2(self, value: str) -> None: pass

        @async_field_validator('name')
        async def validate_name_3(self, field: str) -> None: pass

        @async_field_validator('name')
        async def validate_name_4(self, value: str, field: str) -> None: pass

        @async_field_validator('name')
        async def validate_name_5(self, config: ValidationInfo) -> None: pass

        @async_field_validator('name')
        async def validate_name_6(self, value: str, config: ValidationInfo) -> None: pass

        @async_field_validator('name')
        async def validate_name_7(self, field: str, config: ValidationInfo) -> None: pass

        @async_field_validator('name')
        async def validate_name_8(self, value: str, field: str, config: ValidationInfo) -> None: pass

        @async_field_validator('name')
        async def validate_name_9(self, **kwargs) -> None: pass

    instance = OtherModel(name="valid")
    await instance.model_async_validate()


@pytest.mark.asyncio
async def test_invalid_validators_are_prohibited():
    with pytest.raises(PydanticUserError):
        class OtherModel1(AsyncValidationModelMixin, pydantic.BaseModel):
            name: str

            @async_field_validator
            async def validate_name(self, no_value: Any) -> None: pass

    with pytest.raises(PydanticUserError):
        class OtherModel1(AsyncValidationModelMixin, pydantic.BaseModel):
            name: str

            @async_field_validator('name')
            async def validate_name(self, no_value: Any) -> None: pass

    with pytest.raises(PydanticUserError):
        class OtherModel2(AsyncValidationModelMixin, pydantic.BaseModel):
            name: str

            @async_field_validator('name')
            async def validate_name(self, value: str, something_else: Any) -> None: pass

    with pytest.raises(PydanticUserError):
        class OtherModel3(AsyncValidationModelMixin, pydantic.BaseModel):
            name: str

            @async_field_validator('name')
            async def validate_name(cls, value: str) -> None: pass


@pytest.mark.asyncio
async def test_async_validation_may_get_extra_details():
    class OtherModel(AsyncValidationModelMixin, pydantic.BaseModel):
        name: str

        @async_field_validator('name', some="thing")
        async def validate_name(self, config: ValidationInfo) -> None:
            assert config.extra == {"some": "thing"}

    instance = OtherModel(name="valid")
    await instance.model_async_validate()


@pytest.mark.asyncio
async def test_async_validation_will_call_sub_model_validation():
    class OtherModel(AsyncValidationModelMixin, pydantic.BaseModel):
        something: SomethingModel
        somethings: List[SomethingModel]
        somethings_by_name: Dict[str, SomethingModel]

    instance = OtherModel(
        something=SomethingModel(name="invalid", age=1),
        somethings=[SomethingModel(name="invalid", age=1)],
        somethings_by_name={"some": SomethingModel(name="invalid", age=1)},
    )
    with pytest.raises(pydantic.ValidationError) as O_o:
        await instance.model_async_validate()

    assert len(O_o.value.errors()) == 3
    assert {e['loc'] for e in O_o.value.errors()} == {
        ('something', 'name'),
        ('somethings', 0, 'name'),
        ('somethings_by_name', 'some', 'name'),
    }
