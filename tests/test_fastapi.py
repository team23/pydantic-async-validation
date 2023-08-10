import pydantic
import pytest

from pydantic_async_validation import AsyncValidationModelMixin, async_field_validator

try:
    import fastapi
    from fastapi.testclient import TestClient

    from pydantic_async_validation.fastapi import ensure_request_validation_errors
except ImportError:
    fastapi = None


class SomethingModel(AsyncValidationModelMixin, pydantic.BaseModel):
    name: str

    @async_field_validator('name')
    async def validate_name(self, value: str) -> None:
        if value == "invalid":
            raise ValueError("Invalid name")


@pytest.fixture()
def app():
    app = fastapi.FastAPI()

    @app.get("/no-errors")
    async def all_valid():
        instance = SomethingModel(name="valid")
        with ensure_request_validation_errors():
            await instance.model_async_validate()

    @app.get("/without-request-validation-errors")
    async def without():
        instance = SomethingModel(name="invalid")
        await instance.model_async_validate()

    @app.get("/with-request-validation-errors")
    async def with_context_manager():
        instance = SomethingModel(name="invalid")
        with ensure_request_validation_errors():
            await instance.model_async_validate()

    return app


@pytest.mark.skipif(fastapi is None, reason="fastapi not installed")
def test_fastapi_without_error_just_works(app):
    with TestClient(app) as client:
        response = client.get("/no-errors")
        assert response.status_code == 200


@pytest.mark.skipif(fastapi is None, reason="fastapi not installed")
def test_fastapi_fails_without_handling(app):
    with TestClient(app) as client:
        with pytest.raises(pydantic.ValidationError):
            client.get("/without-request-validation-errors")


@pytest.mark.skipif(fastapi is None, reason="fastapi not installed")
def test_fastapi_triggers_validation_response(app):
    with TestClient(app) as client:
        response = client.get("/with-request-validation-errors")
        assert response.status_code == 422
