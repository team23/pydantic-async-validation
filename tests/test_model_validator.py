from typing import Union

import pytest

from pydantic_async_validation.exceptions import AsyncValidationError
from pydantic_async_validation.mixins import AsyncValidationModelMixin
from pydantic_async_validation.validators import async_field_validator, async_model_validator


class AsyncValidationModelTestModel(AsyncValidationModelMixin):
    id: Union[int, None] = None
    title: Union[str, None] = None
    slug: Union[str, None] = None

    @async_field_validator("slug")
    async def _validate_is_slugified_title(cls, value, instance, field):
        if instance.title:
            slugified_title = instance.title.replace(" ", "_")
            if slugified_title != value:
                raise ValueError(f"The field {field} needs to contain the slugified value of 'title'")

    @async_model_validator()
    async def _validate_id_and_title_are_set(cls, instance):
        """
        Provide a simple way of raising a validation error inside tests.
        """
        if instance.id is None or instance.title is None:
            raise ValueError("You need to set 'id' and 'title'")

    @async_model_validator(skip_on_failure=True)
    async def _skipped_on_failure_validation(cls, instance):
        if instance.title == 'Test Skip':
            raise ValueError('Skipped validator error')


class InheritingValidationTestModel(AsyncValidationModelTestModel):
    pass


class InheritingValidationTestModelWithAdditionalValidator(AsyncValidationModelTestModel):
    @async_model_validator()
    async def _validate_nothing_but_break(cls, instance):
        raise ValueError("This always fails")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_count, instance_data",
    [
        (0, {"id": 1, "title": "Some Title", "slug": "Some_Title"}),
        (1, {"id": 1, "title": "Some Title", "slug": "something_else"}),
        (1, {"id": 1, "title": "Test Skip", "slug": "Test_Skip"}),
        (1, {"id": 1, "title": "Test Skip", "slug": "something_else"}),
        (1, {"title": "Some Title", "slug": "Some_Title"}),
        (2, {"title": "Some Title", "slug": "something_else"}),
        (1, {"title": "Test Skip", "slug": "Test_Skip"}),
        (2, {"title": "Test Skip", "slug": "something_else"}),
    ],
)
async def test_validator(error_count: int, instance_data):
    instance = AsyncValidationModelTestModel(**instance_data)
    inheriting_instance = InheritingValidationTestModel(**instance_data)
    inheriting_instance_with_additional_validator = \
        InheritingValidationTestModelWithAdditionalValidator(**instance_data)
    if error_count > 0:
        with pytest.raises(AsyncValidationError) as o_O:
            await instance.model_async_validate()
        assert len(o_O.value.errors()) == error_count

        with pytest.raises(AsyncValidationError) as o_O:
            await inheriting_instance.model_async_validate()
        assert len(o_O.value.errors()) == error_count

        with pytest.raises(AsyncValidationError) as o_O:
            await inheriting_instance_with_additional_validator.model_async_validate()
        assert len(o_O.value.errors()) == (error_count + 1)
    else:
        await instance.model_async_validate()
        await inheriting_instance.model_async_validate()
