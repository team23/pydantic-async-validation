from typing import Any, Dict, List

import pydantic
import pytest
from pydantic.errors import PydanticUserError

from pydantic_async_validation import AsyncValidationModelMixin, async_model_validator
from pydantic_async_validation.validators import ValidationInfo


class SomethingModel(AsyncValidationModelMixin, pydantic.BaseModel):
    name: str
    age: int

    @async_model_validator()
    async def validate_name(self) -> None:
        if self.name == "invalid":
            raise ValueError("Invalid name")

    @async_model_validator()
    async def validate_age(self) -> None:
        assert self.age > 0


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
async def test_async_validation_raises_when_validation_fails():
    instance = SomethingModel(name="invalid", age=1)
    with pytest.raises(pydantic.ValidationError):
        await instance.model_async_validate()


@pytest.mark.asyncio
async def test_all_field_validator_combinations_are_valid():
    class OtherModel(AsyncValidationModelMixin, pydantic.BaseModel):
        name: str

        @async_model_validator()
        async def validate_name_1(self) -> None: pass

        @async_model_validator()
        async def validate_name_2(self, config: ValidationInfo) -> None: pass

        @async_model_validator()
        async def validate_name_3(self, **kwargs) -> None: pass

    instance = OtherModel(name="valid")
    await instance.model_async_validate()


@pytest.mark.asyncio
async def test_invalid_validators_are_prohibited():
    with pytest.raises(PydanticUserError):
        class OtherModel1(AsyncValidationModelMixin, pydantic.BaseModel):
            name: str

            @async_model_validator()
            async def validate_name(self, uses_value_or_anything: Any) -> None: pass

    with pytest.raises(PydanticUserError):
        class OtherModel2(AsyncValidationModelMixin, pydantic.BaseModel):
            name: str

            @async_model_validator()
            async def validate_name(cls) -> None: pass


@pytest.mark.asyncio
async def test_async_validation_may_get_extra_details():
    class OtherModel(AsyncValidationModelMixin, pydantic.BaseModel):
        name: str

        @async_model_validator(some="thing")
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
        ('something', '__root__'),
        ('somethings', 0, '__root__'),
        ('somethings_by_name', 'some', '__root__'),
    }
