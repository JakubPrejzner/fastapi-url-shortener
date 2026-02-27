from fastapi import HTTPException, status


class ShortCodeNotFound(HTTPException):
    def __init__(self, short_code: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short code '{short_code}' not found",
        )


class ShortCodeCollision(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a unique short code. Try again.",
        )
