# `pydantic-async-validation`

Add async validation to your pydantic models 🥳. This allows you to add validation that actually checks the database
or makes an API call or just use any code you did write async.

Note that validation cannot happen during model creation, so you have to call `await obj.model_async_validate()`
yourself. This is due to the fact that `__init__()` will always be a sync method and you cannot sanely call async
methods from sync methods.

**Note:** `pydantic-async-validation` is compatible with `pydantic` versions `2.x` only. It supports
Python `3.8`, `3.9`, `3.10`, `3.11` and `3.12`. This is also ensured running all tests on all those versions
using `tox`.

## Example usage

```python
import pydantic
from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin


class SomethingModel(AsyncValidationModelMixin, pydantic.BaseModel):
    name: str

    @async_field_validator('name')
    async def validate_name(self, value: str) -> None:
        if value == "invalid":
            raise ValueError("Invalid name")


valid_instance = SomethingModel(name="valid")
await valid_instance.model_async_validate()

invalid_instance = SomethingModel(name="invalid")
await invalid_instance.model_async_validate()  # will raise normal pydantic ValidationError
```

## Field validators

You can use `async_field_validator` to add async validators to your model. The first argument is the name of the field
to validate. You may also pass additional field names, the validator will then be called for all fields. As validation
is happening after the instance was created, you can access all fields of the model and the validator should just be a
normal instance method (accepting `self` as its first parameter).

Field validators may use any combination of the following arguments:
* `value`: The value of the field to validate (same as `getattr(self, field)`)
* `field`: The name of the field being validated, can be useful if you use the same validator for multiple fields
* `config`: The config of the validator, see `ValidationInfo` for details

You may also pass additional keyword arguments to `async_field_validator`, they will be passed to the validator config
(`ValidationInfo` instance) and be available in the validator config as `config.extra`.

Example:

```python
import pydantic
from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin, ValidationInfo


class SomethingModel(AsyncValidationModelMixin, pydantic.BaseModel):
    name: str
    other_name: str

    @async_field_validator('name', 'other_name', some_extra='value')
    async def validate_name(self, value: str, field: str, config: ValidationInfo) -> None:
        if value == "invalid":
            # Using ValueError 
            raise ValueError(f"Invalid {field} with extra {config.extra['some_extra']}")
```

## Model validators

You can use `async_model_validator` to add async validators to your model. The validator will be called after all field
validators have been called. The validator should be a normal instance method (accepting `self` as its first parameter).

Model validators may use any combination of the following arguments:
* `config`: The config of the validator, see `ValidationInfo` for details


Example:

```python
import pydantic
from pydantic_async_validation import async_model_validator, AsyncValidationModelMixin, ValidationInfo


class SomethingModel(AsyncValidationModelMixin, pydantic.BaseModel):
    name: str
    other_name: str

    @async_model_validator(some_extra='value')
    async def validate_names(self, config: ValidationInfo) -> None:
        # Using assertion 
        assert self.name != self.other_name, f"Names are equal with extra {config.extra['some_extra']}"
```

## When to use field vs. model validators

As validation happens after the model instance was created, you can access all fields just using `self` anyways. So
field vs. model validation is kind of the same thing. However field validators allow you to get the `value` of the
field as its parameter, so this is perfect when you reuse validators or want to validate multiple fields with the same
validator. Also field validators will tie the `ValidationError` to the field, so it will contain the detail about which
field failed to validate. In general you should use field validators when you want to validate a single field. I also
suggest using the `value` parameter to have a clean and consistent interface for your validators.

Model validators on the other hand should be used when you need to validate multiple fields at once. This is especially
useful when you want to validate that multiple fields are consistent with each other. For example you might want to
validate that a start date is before an end date. In this case you would use a model validator and access both fields
using `self`. Note that model validators will be tied to `"__root__"` in the `ValidationError` as there is no specific
field to tie it to.

## Handling validation errors

Like with normal pydantic validation, you can catch `ValidationError` and access the `errors()` method to get a list of
all errors. Like with pydantic errors will be collected and be raised as one `ValidationError` at the end of validation,
including all errors that occurred.

`model_async_validate()` will also try to validate child model instances, that are also using the
`AsyncValidationModelMixin`. This means the following example code will work as expected:

```python
import pydantic
from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin, ValidationInfo


class SomethingModel(AsyncValidationModelMixin, pydantic.BaseModel):
    name: str

    @async_field_validator('name')
    async def validate_name(self, value: str, field: str, config: ValidationInfo) -> None:
        if value == "invalid":
            raise ValueError(f"Value may not be 'invalid'")


class ParentModel(AsyncValidationModelMixin, pydantic.BaseModel):
    child: SomethingModel


invalid_instance = ParentModel(child=SomethingModel(name="invalid"))
await invalid_instance.model_async_validate()  # will raise normal pydantic ValidationError
```

Note the `ValidationError` will now have the location of the error set to `"child.name"`.

Recursive validation will happen in those cases:
* Child models as direct instance variables (as in example above)
* Child models in list items (like `child: List[SomethingModel]`)
* Child models in dict values (like `child: Dict[str, SomethingModel]`)

## FastAPI support

When using FastAPI you also can use the `AsyncValidationModelMixin`, note however that FastAPI will see any
`ValidationError` risen in endpoint methods as unhandled exceptions and thus will return a HTTP 500 error. FastAPI
will only handle the validation errors happening during handling the endpoint parameters in a special way and
convert those to `RequestValidationError` - which will then be handled by the default exception handler for
`RequestValidationError` FastAPI provides. This will then result in a HTTP 422 return code.

When using `pydantic_async_validation` this would be a major drawback, as using `model_async_validate` for
validating input (/request) data is a totally fine use case and you cannot push this into the normal request
validation step FastAPI does. To solve this issue you can use the `ensure_request_validation_errors` context manager
provided in `pydantic_async_validation.fastapi`. This will ensure that any `ValidationError` risen inside the context
manager will be converted to a `RequestValidationError`. Those `RequestValidationError`s will then be handled by
the default exception handler for `RequestValidationError` which FastAPI provides. This will then again result in a
HTTP 422 return code.

Example for usage with FastAPI:

```python
import fastapi
import pydantic
from pydantic_async_validation import AsyncValidationModelMixin
from pydantic_async_validation.fastapi import ensure_request_validation_errors


class SomethingModel(AsyncValidationModelMixin, pydantic.BaseModel): ...


app = fastapi.FastAPI()

@app.get("/return-http-422-on-async-validation-error")
async def return_http_422_on_async_validation_error():
    instance = SomethingModel(...)
    with ensure_request_validation_errors("body"):  # use body as error location prefix
        await instance.model_async_validate()
```

You may also use `ensure_request_validation_errors` to do additional validation on the request data using normal
pydantic validation and converting those `ValidationError`s to `RequestValidationError`s. Use the `prefix`
parameter to mimic the FastAPI behaviour regarding using "body" for POST body data for example. 😉

**Note:** When using FastAPI you should install `pydantic-async-validation` using
`pip install pydantic-async-validation[fastapi]` to ensure FastAPI is installed in a compatible version.

# Contributing

If you want to contribute to this project, feel free to just fork the project,
create a dev branch in your fork and then create a pull request (PR). If you
are unsure about whether your changes really suit the project please create an
issue first, to talk about this.
