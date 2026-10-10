from pydantic import BaseModel


# Shared response models. Model names become type names in the frontend's generated API client
# (TuneUp-App-Frontend/src/api/generated.ts), so keep them unique across all routers.
class DetailResponse(BaseModel):
    detail: bool
