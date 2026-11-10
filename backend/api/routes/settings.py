"""
API key / model settings routes.
"""

from fastapi import APIRouter

from config.settings import (
    AVAILABLE_GEMINI_MODELS,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_VERIFICATION_PROVIDER,
    VERIFICATION_PROVIDERS,
    AppConfig,
)
from models.schemas import (
    ApiKeyRequest,
    ApiKeyStatusResponse,
    ApiKeyTestResponse,
    MessageResponse,
    ModelUpdateRequest,
    VerificationSettingsRequest,
    VerificationSettingsResponse,
)
from services.gemini_service import validate_api_key
from utils.logging_config import logger
from utils.secure_storage import (
    get_api_key,
    get_verification_api_key,
    has_api_key,
    has_verification_api_key,
    remove_api_key,
    remove_verification_api_key,
    save_api_key,
    save_verification_api_key,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
@router.get("/key", response_model=ApiKeyStatusResponse)
def get_key_status():
    """Return whether a key is stored (never returns the key itself)."""
    config = AppConfig.get()
    return ApiKeyStatusResponse(
        has_key=has_api_key(),
        model=config.gemini_model,
        available_models=AVAILABLE_GEMINI_MODELS,
    )


# ---------------------------------------------------------------------------
# Save / update
# ---------------------------------------------------------------------------
@router.post("/key", response_model=MessageResponse)
def save_key(req: ApiKeyRequest):
    """Store the Gemini API key securely."""
    save_api_key(req.api_key)
    logger.info("API key saved by user")
    return MessageResponse(message="API key saved successfully")


@router.put("/key", response_model=MessageResponse)
def update_key(req: ApiKeyRequest):
    """Replace the stored API key."""
    save_api_key(req.api_key)
    logger.info("API key updated by user")
    return MessageResponse(message="API key updated successfully")


# ---------------------------------------------------------------------------
# Remove
# ---------------------------------------------------------------------------
@router.delete("/key", response_model=MessageResponse)
def delete_key():
    """Delete the stored API key."""
    removed = remove_api_key()
    return MessageResponse(
        message="API key removed" if removed else "No API key to remove",
    )


# ---------------------------------------------------------------------------
# Test / validate
# ---------------------------------------------------------------------------
@router.post("/key/test", response_model=ApiKeyTestResponse)
def test_key(req: ApiKeyRequest | None = None):
    """
    Validate the Gemini API key by making a real API call.
    Accepts a key in the body (to test before saving) or uses the stored key.
    """
    key = req.api_key if req and req.api_key else None
    config = AppConfig.get()
    result = validate_api_key(api_key=key, model=config.gemini_model)
    if result.valid:
        logger.info("API key test passed")
    else:
        logger.warning(f"API key test failed: {result.message}")
    return result


@router.get("/key/test", response_model=ApiKeyTestResponse)
def test_stored_key():
    """Validate the currently stored API key."""
    config = AppConfig.get()
    result = validate_api_key(model=config.gemini_model)
    return result


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------
@router.get("/model", response_model=ModelUpdateRequest)
def get_model():
    """Return the currently selected Gemini model."""
    config = AppConfig.get()
    return ModelUpdateRequest(model=config.gemini_model)


@router.put("/model", response_model=MessageResponse)
def set_model(req: ModelUpdateRequest):
    """Update the selected Gemini model."""
    if req.model not in AVAILABLE_GEMINI_MODELS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Model '{req.model}' is not supported. "
                   f"Available: {', '.join(AVAILABLE_GEMINI_MODELS)}",
        )
    config = AppConfig.get()
    config.set_gemini_model(req.model)
    logger.info(f"Gemini model set to: {req.model}")
    return MessageResponse(message=f"Model set to {req.model}")


@router.get("/models", response_model=dict)
def get_available_models():
    """Return available Gemini models and the currently selected one."""
    config = AppConfig.get()
    return {
        "models": AVAILABLE_GEMINI_MODELS,
        "selected": config.gemini_model,
        "default": DEFAULT_GEMINI_MODEL,
    }


# ---------------------------------------------------------------------------
# Verification settings
# ---------------------------------------------------------------------------
@router.get("/verification", response_model=VerificationSettingsResponse)
def get_verification_settings():
    """Return current verification provider configuration."""
    config = AppConfig.get()
    return VerificationSettingsResponse(
        provider=config.verification_provider,
        available_providers=VERIFICATION_PROVIDERS,
        has_api_key=has_verification_api_key(),
        api_url=config.verification_api_url or "",
    )


@router.post("/verification", response_model=MessageResponse)
def update_verification_settings(req: VerificationSettingsRequest):
    """Update verification provider, endpoint URL, and optional API key."""
    if req.provider not in VERIFICATION_PROVIDERS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{req.provider}' is not supported. "
                   f"Available: {', '.join(VERIFICATION_PROVIDERS)}",
        )
    config = AppConfig.get()
    config.set_verification_provider(req.provider, api_url=req.api_url or "")

    if req.api_key is not None:
        key_str = req.api_key.strip()
        if key_str:
            save_verification_api_key(key_str)
            logger.info("Verification API key updated")
        else:
            remove_verification_api_key()

    logger.info(f"Verification provider set to {req.provider}")
    return MessageResponse(message=f"Verification provider set to {req.provider}")


@router.delete("/verification/key", response_model=MessageResponse)
def delete_verification_key():
    """Remove stored verification API key."""
    removed = remove_verification_api_key()
    return MessageResponse(
        message="Verification API key removed" if removed else "No verification API key to remove"
    )
