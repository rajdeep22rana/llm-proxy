from fastapi import APIRouter

router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.post("/")
async def proxy():
    # TODO: implement proxy logic
    return {"message": "stub"}
