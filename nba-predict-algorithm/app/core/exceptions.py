"""
异常处理
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError


class AlgorithmException(Exception):
    """算法异常基类"""
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(message)


class DataNotFoundException(AlgorithmException):
    """数据不存在异常"""
    def __init__(self, message: str = "数据不存在"):
        super().__init__(message, code=404)


class ParameterException(AlgorithmException):
    """参数异常"""
    def __init__(self, message: str = "参数错误"):
        super().__init__(message, code=400)


class CalculationException(AlgorithmException):
    """计算异常"""
    def __init__(self, message: str = "计算失败"):
        super().__init__(message, code=500)


class DataSourceException(AlgorithmException):
    """数据源异常"""
    def __init__(self, message: str = "数据源采集失败"):
        super().__init__(message, code=503)


def register_exception_handlers(app: FastAPI):
    """注册异常处理器"""

    @app.exception_handler(AlgorithmException)
    async def algorithm_exception_handler(request: Request, exc: AlgorithmException):
        logger.error(f"算法异常: {exc.message}")
        return JSONResponse(
            status_code=exc.code,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": None,
            }
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        message = "; ".join(errors)
        logger.error(f"参数校验失败: {message}")
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": f"参数校验失败: {message}",
                "data": None,
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"未知异常: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "data": None,
            }
        )
