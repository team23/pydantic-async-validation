import pydantic
import pytest

from pydantic_async_validation import AsyncValidationModelMixin, async_field_validator

try:
    import fastapi
    from fastapi.encoders import jsonable_encoder
    from fastapi.exceptions import RequestValidationError
    from fastapi.testclient import TestClient

    from pydantic_async_validation.fastapi import ensure_request_validation_errors
except ImportError:
    fastapi = None


class ModelUsingPydanticValidation(pydantic.BaseModel):
    name: str

    @pydantic.field_validator("name")
    def _validate_name(cls, value: str) -> str:  # noqa: ARG002
        raise ValueError("Always invalid")


class ParentModelUsingPydanticValidation(pydantic.BaseModel):
    child: ModelUsingPydanticValidation


class ModelUsingAsyncValidation(AsyncValidationModelMixin, pydantic.BaseModel):
    name: str

    @async_field_validator("name")
    async def _validate_name(self, value: str) -> str:  # noqa: ARG002
        raise ValueError("Always invalid")


class ParentModelUsingAsyncValidation(AsyncValidationModelMixin, pydantic.BaseModel):
    child: ModelUsingAsyncValidation


@pytest.mark.skipif(fastapi is None, reason="fastapi not installed")
@pytest.mark.asyncio()
async def test_pydantic_validation_compatibility():
    pydantic_validation_error = {}
    try:
        with ensure_request_validation_errors():
            ModelUsingPydanticValidation(name="invalid anyways")
    except RequestValidationError as O_o:
        pydantic_validation_error.update(jsonable_encoder(O_o.errors())[0])

    async_validation_error = {}
    try:
        with ensure_request_validation_errors():
            await ModelUsingAsyncValidation(name="invalid anyways").model_async_validate()
    except RequestValidationError as O_o:
        async_validation_error.update(jsonable_encoder(O_o.errors())[0])

    assert pydantic_validation_error["input"] == async_validation_error["input"]
    assert pydantic_validation_error["loc"] == async_validation_error["loc"]
    assert pydantic_validation_error["type"] == async_validation_error["type"]


@pytest.mark.skipif(fastapi is None, reason="fastapi not installed")
@pytest.mark.asyncio()
async def test_pydantic_child_validation_compatibility():
    pydantic_validation_error = {}
    try:
        with ensure_request_validation_errors():
            ParentModelUsingPydanticValidation(
                # using a dict so the validation happens in ParentModelUsingPydanticValidation
                child={"name": "invalid anyways"},
            )
    except RequestValidationError as O_o:
        pydantic_validation_error.update(jsonable_encoder(O_o.errors())[0])

    async_validation_error = {}
    try:
        with ensure_request_validation_errors():
            obj = ParentModelUsingAsyncValidation(
                # using a dict so the validation happens in ParentModelUsingAsyncValidation
                child={"name": "invalid anyways"},
            )
            await obj.model_async_validate()
    except RequestValidationError as O_o:
        async_validation_error.update(jsonable_encoder(O_o.errors())[0])

    assert pydantic_validation_error["input"] == async_validation_error["input"]
    assert pydantic_validation_error["loc"] == async_validation_error["loc"]
    assert pydantic_validation_error["type"] == async_validation_error["type"]


@pytest.fixture()
def app():
    app_ = fastapi.FastAPI()

    @app_.post("/pydantic-test")
    async def pydantic_test(data: ModelUsingPydanticValidation = fastapi.Body(...)):
        return data

    @app_.post("/async-test")
    async def async_test(data: ModelUsingAsyncValidation = fastapi.Body(...)):
        with ensure_request_validation_errors():
            await data.model_async_validate()
        return data

    @app_.post("/async-test-with-prefix")
    async def async_test_with_prefix(data: ModelUsingAsyncValidation = fastapi.Body(...)):
        with ensure_request_validation_errors("body"):
            await data.model_async_validate()
        return data

    return app_


@pytest.mark.skipif(fastapi is None, reason="fastapi not installed")
@pytest.mark.asyncio()
async def test_fastapi_validation_compatibility(app):
    with TestClient(app) as client:
        response = client.post("/pydantic-test", json={"name": "invalid anyways"})
        assert response.status_code == 422
        pydantic_validation_error = response.json()["detail"][0]

    with TestClient(app) as client:
        response = client.post("/async-test", json={"name": "invalid anyways"})
        assert response.status_code == 422
        async_validation_error = response.json()["detail"][0]

    with TestClient(app) as client:
        response = client.post("/async-test-with-prefix", json={"name": "invalid anyways"})
        assert response.status_code == 422
        prefixed_async_validation_error = response.json()["detail"][0]

    assert pydantic_validation_error["loc"] == ["body", "name"]
    assert async_validation_error["loc"] == ["name"]
    assert prefixed_async_validation_error["loc"] == ["body", "name"]

    assert pydantic_validation_error["input"] == async_validation_error["input"]
    assert pydantic_validation_error["input"] == prefixed_async_validation_error["input"]

    assert pydantic_validation_error["type"] == async_validation_error["type"]
    assert pydantic_validation_error["type"] == prefixed_async_validation_error["type"]
