from fastapi import HTTPException


class ItemNotAvailable(HTTPException):
    """Item is not available."""
    def __init__(self, url: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            detail=f"Item not available at {url}",
        )


class ItemNotFound(HTTPException):
    """Item not found."""
    def __init__(self, status_code: int = 404):
        super().__init__(
            status_code=status_code,
            detail=f"Item not found",
        )


class UnknownUrlTypeError(HTTPException):
    """Unknown URL type."""
    def __init__(self, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            detail=f"Url doesn't contain \"ozon\"",
        )