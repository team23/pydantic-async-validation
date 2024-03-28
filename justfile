default:
    just --list

[unix]
_install-pre-commit:
    #!/usr/bin/env bash
    if ( which pre-commit > /dev/null 2>&1 )
    then
        pre-commit install --install-hooks
    else
        echo "-----------------------------------------------------------------"
        echo "pre-commit is not installed - cannot enable pre-commit hooks!"
        echo "Recommendation: Install pre-commit ('brew install pre-commit')."
        echo "-----------------------------------------------------------------"
    fi

[windows]
_install-pre-commit:
    #!powershell.exe
    Write-Host "Please ensure pre-commit hooks are installed using 'pre-commit install --install-hooks'"

install: (poetry "install" "-E" "fastapi") && _install-pre-commit

update: (poetry "install" "-E" "fastapi")

poetry *args:
    poetry {{args}}

test *args: (poetry "run" "pytest" "--cov=pydantic_async_validation" "--cov-report" "term-missing:skip-covered" args)

test-all: (poetry "run" "tox")

ruff *args: (poetry "run" "ruff" "check" "pydantic_async_validation" "tests" args)

pyright *args: (poetry "run" "pyright" "pydantic_async_validation" args)

lint: ruff pyright

publish: (poetry "publish" "--build")

release version: (poetry "version" version)
    git add pyproject.toml
    git commit -m "release: 🔖 v$(poetry version --short)" --no-verify
    git tag "v$(poetry version --short)"
    git push
    git push --tags
