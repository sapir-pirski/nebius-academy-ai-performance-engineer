from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_setup import logger


def fastapi_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "message": str(message)},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    def http_exception_handler(_: Request, exc: HTTPException):
        logger.warning("http_exception status=%s message=%s", exc.status_code, exc.detail)
        return fastapi_error(exc.status_code, exc.detail)

    @app.exception_handler(RequestValidationError)
    def validation_exception_handler(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        first_error = errors[0].get("msg") if errors else "Invalid request body"
        logger.warning("validation_error message=%s", first_error)
        return fastapi_error(422, first_error)

    @app.exception_handler(Exception)
    def unexpected_exception_handler(_: Request, exc: Exception):
        logger.exception("unexpected_exception")
        return fastapi_error(500, "Unexpected server error.")
