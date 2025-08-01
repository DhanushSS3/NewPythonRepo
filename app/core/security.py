# app/core/security.py
import os
from typing import Any, Union, Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from redis import asyncio as aioredis # Use async Redis client
import json
from datetime import datetime, timedelta # Correct: Import both datetime and timedelta directly

import logging

# Ensure these imports are correct based on your project structure
from app.database.models import User, DemoUser

# Import necessary components from fastapi
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request # Import Request if needed in dependencies

# Import necessary components for database interaction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Import your database models and session dependency
# Removed duplicate: from app.database.models import User
from app.database.session import get_db # Assuming get_db dependency is imported here

from app.core.config import get_settings
from app.core.logging_config import security_logger

# Configure logging

# logger = logging.getLogger(__name__) # This line is removed as per the edit hint
# Configure the password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Get application settings
settings = get_settings()

# --- Password Hashing Functions ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Generates a hash for a given plain password.
    """
    return pwd_context.hash(password)

# --- JWT Functions ---

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) # Use settings for default expiry

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # logger.debug(f"\n--- Token Creation Details ---") # This line is removed as per the edit hint
    # logger.debug(f"Using SECRET_KEY: {str(settings.SECRET_KEY)[:5]}... for encoding") # This line is removed as per the edit hint
    # logger.debug(f"ALGORITHM used for encoding: '{settings.ALGORITHM}'") # This line is removed as per the edit hint
    # logger.debug(f"Payload to encode: {to_encode}") # This line is removed as per the edit hint

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    # logger.debug(f"Generated JWT: {encoded_jwt[:30]}...\n") # This line is removed as per the edit hint
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates a JWT refresh token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict[str, Any]:
    """
    Decodes a JWT token and returns the payload.
    """
    try:
        # logger.debug(f"Attempting to decode token: {token[:30]}...") # This line is removed as per the edit hint
        # logger.debug(f"Using SECRET_KEY: {str(settings.SECRET_KEY)[:5]}... for decoding") # This line is removed as per the edit hint
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # logger.debug(f"Token decoded successfully. Payload: {payload}") # This line is removed as per the edit hint
        return payload
    except JWTError as e:
        # logger.warning(f"JWTError in decode_token: {type(e).__name__} - {str(e)}", exc_info=True) # This line is removed as per the edit hint
        raise JWTError("Could not validate credentials")
    except Exception as ex:
        # logger.error(f"Unexpected error in decode_token: {type(ex).__name__} - {str(ex)}", exc_info=True) # This line is removed as per the edit hint
        raise JWTError("Could not validate credentials due to unexpected error")

# --- Redis Integration ---

import socket

# app/core/security.py

from typing import Optional
import socket
from redis.asyncio import Redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def connect_to_redis() -> Optional[Redis]:
    """
    Establishes a Redis connection with configured host, port, db, and password.
    Validates connection with PING and ensures AOF persistence is enabled.
    Returns the Redis client instance or None on failure.
    """
    try:
        redis_host = settings.REDIS_HOST
        redis_port = settings.REDIS_PORT

        # Resolve IP for clarity (optional in most environments)
        resolved_ip = socket.gethostbyname(redis_host)

        client = Redis(
            host=redis_host,
            port=redis_port,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )

        await client.ping()
        logger.info(f"[Redis] Connected to {redis_host} ({resolved_ip}):{redis_port}")

        # Ensure AOF persistence is enabled
        config_get = await client.config_get('appendonly')
        if config_get.get('appendonly') != 'yes':
            logger.warning("[Redis] AOF persistence not enabled. Enabling now...")
            await client.config_set('appendonly', 'yes')
            await client.config_set('appendfsync', 'everysec')
            logger.info("[Redis] AOF persistence enabled with appendfsync=everysec.")
        else:
            logger.info("[Redis] AOF persistence already enabled.")

        return client

    except Exception as e:
        logger.error(f"[Redis] Connection failed: {e}", exc_info=True)
        return None

async def close_redis_connection(client: Optional[Redis]) -> None:
    """
    Closes the Redis connection safely during application shutdown.
    """
    if client:
        try:
            await client.close()
            logger.info("[Redis] Connection closed successfully.")
        except Exception as e:
            logger.error(f"[Redis] Error while closing connection: {e}", exc_info=True)


async def store_refresh_token(
    client: aioredis.Redis, # Use the original aioredis type hint
    user_id: int,
    refresh_token: str,
    user_type: Optional[str] = None
):
    """
    Stores a refresh token in Redis associated with a user ID.
    Requires an active Redis client instance.
    Now also accepts an optional user_type.
    """
    if not client:
        # logger.warning("Redis client not provided to store_refresh_token. Cannot store refresh token.") # This line is removed as per the edit hint
        return

    redis_key = f"refresh_token:{refresh_token}"
    expiry_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    
    # Include user_type in token_data if it's provided
    token_data = {
        "user_id": user_id,
        "expires_at": (datetime.utcnow() + timedelta(seconds=expiry_seconds)).isoformat() # Corrected
    }
    if user_type:
        token_data["user_type"] = user_type

    token_data_json = json.dumps(token_data)
    
    # logger.info(f"Storing refresh token for user ID {user_id} (Type: {user_type or 'N/A'}). Key: {redis_key}, Expiry (seconds): {expiry_seconds}") # This line is removed as per the edit hint

    try:
        await client.set(redis_key, token_data_json, ex=expiry_seconds)
        # logger.info(f"Refresh token stored successfully for user ID: {user_id}") # This line is removed as per the edit hint
    except Exception as e:
        # logger.error(f"Error storing refresh token in Redis for user ID {user_id}: {e}", exc_info=True) # This line is removed as per the edit hint
        pass # This line is added as per the edit hint


async def get_refresh_token_data(client: aioredis.Redis, refresh_token: str) -> dict[str, Any] | None:
    """
    Retrieves refresh token data from Redis.
    Requires an active Redis client instance.
    """
    if not client:
        # logger.warning("Redis client not provided to get_refresh_token_data. Cannot retrieve refresh token.") # This line is removed as per the edit hint
        return None

    redis_key = f"refresh_token:{refresh_token}"
    # logger.info(f"Attempting to retrieve refresh token data for key: {redis_key}") # This line is removed as per the edit hint

    try:
        token_data_json = await client.get(redis_key)
        if token_data_json:
            token_data = json.loads(token_data_json)
            return token_data
        else:
            # logger.info(f"No refresh token data found in Redis for key: {redis_key}") # This line is removed as per the edit hint
            return None
    except json.JSONDecodeError:
        # logger.error(f"Failed to decode JSON from Redis data for key {redis_key}: {token_data_json}", exc_info=True) # This line is removed as per the edit hint
        return None
    except Exception as e:
        # logger.error(f"Error retrieving or parsing refresh token from Redis for key {redis_key}: {e}", exc_info=True) # This line is removed as per the edit hint
        return None

async def delete_refresh_token(client: aioredis.Redis, refresh_token: str):
    """
    Deletes a refresh token from Redis.
    Requires an active Redis client instance.
    """
    if not client:
        # logger.warning("Redis client not provided to delete_refresh_token. Cannot delete refresh token.") # This line is removed as per the edit hint
        return

    redis_key = f"refresh_token:{refresh_token}"
    # logger.info(f"Attempting to delete refresh token for key: {redis_key}") # This line is removed as per the edit hint

    try:
        deleted_count = await client.delete(redis_key)
        if deleted_count > 0:
            # logger.info(f"Refresh token deleted from Redis for key: {redis_key}") # This line is removed as per the edit hint
            pass # This line is added as per the edit hint
        else:
            # logger.warning(f"Attempted to delete refresh token, but key not found in Redis: {redis_key}") # This line is removed as per the edit hint
            pass # This line is added as per the edit hint
    except Exception as e:
        # logger.error(f"Error deleting refresh token from Redis for key {redis_key}: {e}", exc_info=True) # This line is removed as per the edit hint
        pass # This line is added as per the edit hint


# --- Authentication Dependency (for protecting routes) ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login", auto_error=False)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User | DemoUser:
    """
    Unified dependency to get the current authenticated user (live or demo) from the access token.
    Always uses BOTH user_type and id for DB lookup. Returns User or DemoUser object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        # logger.warning("Access token is missing.") # This line is removed as per the edit hint
        raise credentials_exception

    try:
        payload = decode_token(token)
        # logger.info(f"Token payload in get_current_user: {payload}") # This line is removed as per the edit hint
        user_id = payload.get("sub")
        user_type = payload.get("user_type")
        if user_id is None or user_type not in ("live", "demo", "admin"): # Added 'admin' to user_type check
            # logger.warning(f"Access token payload missing 'sub' or invalid 'user_type'. Payload: {payload}") # This line is removed as per the edit hint
            raise credentials_exception

        # Strictly filter by BOTH user_type and id
        if user_type == "demo":
            # logger.info(f"Looking up demo user with ID: {user_id}") # This line is removed as per the edit hint
            # from app.database.models import DemoUser # Already imported at the top
            result = await db.execute(select(DemoUser).filter(DemoUser.id == int(user_id), DemoUser.user_type == "demo"))
            user = result.scalars().first()
            if user:
                # logger.info(f"Found demo user - ID: {user.id}, Type: {user.user_type}") # This line is removed as per the edit hint
                pass # This line is added as per the edit hint
            else:
                # logger.warning(f"Demo user not found for ID: {user_id}") # This line is removed as per the edit hint
                pass # This line is added as per the edit hint
        else: # Covers "live" and "admin" if "admin" is a separate type from "live" user model
            # logger.info(f"Looking up live user with ID: {user_id}, Type: {user_type}") # This line is removed as per the edit hint
            # from app.database.models import User # Already imported at the top
            # Assuming 'admin' users are also stored in the 'User' table and have user_type='admin'
            result = await db.execute(select(User).filter(User.id == int(user_id), User.user_type == user_type))
            user = result.scalars().first()
            if user:
                # logger.info(f"Found live user - ID: {user.id}, Type: {user.user_type}") # This line is removed as per the edit hint
                pass # This line is added as per the edit hint
            else:
                # logger.warning(f"Live user not found for ID: {user_id}, Type: {user_type}") # This line is removed as per the edit hint
                pass # This line is added as per the edit hint

        if user is None:
            # logger.warning(f"User ID {user_id} with type {user_type} from access token not found in database.") # This line is removed as per the edit hint
            raise credentials_exception

        # Check for isActive only if the attribute exists on the user object
        if hasattr(user, "isActive") and getattr(user, "isActive", 0) != 1:
            # logger.warning(f"User ID {user_id} (type {user_type}) is not active or verified.") # This line is removed as per the edit hint
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active or verified."
            )
        # logger.info(f"Successfully authenticated user - ID: {user.id}, Type: {user.user_type}, Class: {type(user).__name__}") # This line is removed as per the edit hint
        return user

    except JWTError:
        # logger.warning("JWTError during access token validation.", exc_info=True) # This line is removed as per the edit hint
        raise credentials_exception
    except Exception as e:
        # logger.error(f"Unexpected error in get_current_user dependency for token: {token[:20]}... : {e}", exc_info=True) # This line is removed as per the edit hint
        raise credentials_exception


# --- Dependency specifically for admin users ---
async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to get the current authenticated user and check if they are an admin.
    Requires successful authentication via get_current_user first.
    """
    if current_user.user_type != 'admin':
        # logger.warning(f"User ID {current_user.id} attempted to access admin resource without admin privileges.") # This line is removed as per the edit hint
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource. Admin privileges required."
        )
    return current_user


# NEW FUNCTION TO SUPPORT SERVICE ACCOUNT JWT
def create_service_account_token(service_name: str, expires_minutes: int = 60) -> str:
    """
    Creates a JWT for a service account.
    The payload is structured specifically for service account validation.
    """
    data = {
        "sub": service_name,          # The subject is the name of the service
        "is_service_account": True    # Flag to identify this as a service account token
    }
    return create_access_token(data=data, expires_delta=timedelta(minutes=expires_minutes))

# NEW DEPENDENCY FUNCTION - MODIFIED to handle service accounts targeting demo/live users
async def get_user_from_service_or_user_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Union[User, DemoUser]:
    """
    Authenticates a user either directly from their token or
    by a service account token operating on behalf of a specific user.
    Always uses BOTH user_type and id/email for DB lookup.
    """
    try:
        payload = decode_token(token)
        # logger.info(f"Token payload: {payload}") # This line is removed as per the edit hint
        
        if payload.get("is_service_account"):
            service_name = payload.get("sub")
            # logger.info(f"Service account token detected for service: {service_name}") # This line is removed as per the edit hint
            # If a service account token, extract target user_id and user_type from request body or query params
            try:
                # Attempt to get JSON body if present, else default to empty dict
                body = await request.json()
            except Exception: # Catches JSONDecodeError if body is empty or not JSON
                body = {}

            user_id = body.get("user_id") or request.query_params.get("user_id")
            target_user_type = body.get("user_type") or request.query_params.get("user_type")

            if not user_id or target_user_type not in ["live", "demo"]:
                # logger.warning(f"Service account request missing or invalid target user_id/user_type. user_id: {user_id}, target_user_type: {target_user_type}") # This line is removed as per the edit hint
                raise HTTPException(status_code=400, detail="Missing or invalid user_id/user_type for service account operation.")
            
            # logger.info(f"Service account targeting user ID: {user_id}, Type: {target_user_type}") # This line is removed as per the edit hint
            # Strictly filter by BOTH user_type and id
            if target_user_type == "demo":
                # from app.database.models import DemoUser # Already imported at the top
                stmt = select(DemoUser).where(DemoUser.id == int(user_id), DemoUser.user_type == "demo")
            else: # Covers "live" users targeted by service accounts
                # from app.database.models import User # Already imported at the top
                stmt = select(User).where(User.id == int(user_id), User.user_type == "live")
            
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                # logger.warning(f"Target user (ID: {user_id}, Type: {target_user_type}) not found for service account.") # This line is removed as per the edit hint
                raise HTTPException(status_code=404, detail=f"Target user (ID: {user_id}, Type: {target_user_type}) not found.")
            
            # Attach a flag to the user object to indicate it was authenticated via a service account
            user.is_service_account = True
            
            # logger.info(f"Service account '{service_name}' successfully identified target user ID: {user_id}, Type: {target_user_type}") # This line is removed as per the edit hint
            return user
        else:
            # For regular user tokens, defer to get_current_user (which is now strict on both fields)
            # logger.info("Regular user token detected. Deferring to get_current_user.") # This line is removed as per the edit hint
            user = await get_current_user(db=db, token=token)
            # Explicitly mark that this is not a service account call
            user.is_service_account = False
            # logger.info(f"Authenticated user - ID: {user.id}, Type: {user.user_type}, Class: {type(user).__name__}") # This line is removed as per the edit hint
            return user
    except HTTPException: # Re-raise HTTPExceptions as they are intended errors
        raise
    except Exception as e:
        security_logger.error(f"Authentication error in get_user_from_service_or_user_token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_user_from_service_token(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get a user from a service account token.
    This is a streamlined version for service-provider-only endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if token is None:
        # logger.warning("Service account token is missing.") # This line is removed as per the edit hint
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        service_name: str = payload.get("sub")
        is_service_account: bool = payload.get("is_service_account", False)

        if service_name is None or not is_service_account:
            raise credentials_exception

    except JWTError:
        raise credentials_exception
    
    # For service accounts, we don't need to fetch a full user record from the DB.
    # We can return a lightweight object representing the service account.
    # This avoids DB lookups and prevents errors when no user_id is in the request.
    service_user = User(id=0, email=f"{service_name}@service.account")
    service_user.is_service_account = True
    
    return service_user

def log_user_login(user):
    security_logger.info(f"LOGIN: user_id={user.id}, email={getattr(user, 'email', None)}, user_type={getattr(user, 'user_type', None)}, time={datetime.utcnow().isoformat()}")

def log_user_logout(user):
    security_logger.info(f"LOGOUT: user_id={user.id}, email={getattr(user, 'email', None)}, user_type={getattr(user, 'user_type', None)}, time={datetime.utcnow().isoformat()}")


async def get_user_for_action_with_admin_support(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User | DemoUser:
    """
    Dependency that allows:
    - Regular users to act on their own behalf (from token)
    - Service accounts to act on behalf of a user (from request body)
    - Admins to act on behalf of any user (from request body)
    Always uses BOTH user_type and id for DB lookup.
    """
    from app.database.models import User, DemoUser
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_type_from_token = payload.get("user_type")
        user_id_from_token = payload.get("sub")
        is_service_account = payload.get("is_service_account", False)
        # If admin, allow acting on behalf of any user by reading from request
        if user_type_from_token == "admin":
            try:
                body = await request.json()
            except Exception:
                body = {}
            user_id = body.get("user_id") or request.query_params.get("user_id")
            target_user_type = body.get("user_type") or request.query_params.get("user_type")
            if not user_id or target_user_type not in ["live", "demo"]:
                raise HTTPException(status_code=400, detail="Missing or invalid user_id/user_type for admin operation.")
            if target_user_type == "demo":
                result = await db.execute(select(DemoUser).filter(DemoUser.id == int(user_id), DemoUser.user_type == "demo"))
                user = result.scalars().first()
            else:
                result = await db.execute(select(User).filter(User.id == int(user_id), User.user_type == "live"))
                user = result.scalars().first()
            if not user:
                raise HTTPException(status_code=404, detail=f"Target user (ID: {user_id}, Type: {target_user_type}) not found.")
            user.is_admin_acting = True
            return user
        # If service account, same as before
        elif is_service_account:
            try:
                body = await request.json()
            except Exception:
                body = {}
            user_id = body.get("user_id") or request.query_params.get("user_id")
            target_user_type = body.get("user_type") or request.query_params.get("user_type")
            if not user_id or target_user_type not in ["live", "demo"]:
                raise HTTPException(status_code=400, detail="Missing or invalid user_id/user_type for service account operation.")
            if target_user_type == "demo":
                result = await db.execute(select(DemoUser).filter(DemoUser.id == int(user_id), DemoUser.user_type == "demo"))
                user = result.scalars().first()
            else:
                result = await db.execute(select(User).filter(User.id == int(user_id), User.user_type == "live"))
                user = result.scalars().first()
            if not user:
                raise HTTPException(status_code=404, detail=f"Target user (ID: {user_id}, Type: {target_user_type}) not found.")
            user.is_service_account = True
            return user
        # Otherwise, regular user
        else:
            user = await get_current_user(db=db, token=token)
            user.is_service_account = False
            user.is_admin_acting = False
            return user
    except HTTPException:
        raise
    except Exception as e:
        security_logger.error(f"Authentication error in get_user_for_action_with_admin_support: {e}", exc_info=True)
        raise credentials_exception

