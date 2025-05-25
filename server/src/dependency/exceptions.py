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
    def __init__(self, url: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            detail=f"Item not available at {url}",
        )