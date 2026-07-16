from fastapi import Header, HTTPException, status


def get_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key")
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized."
        )
    return x_api_key
