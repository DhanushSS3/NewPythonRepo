# app/schemas/user.py

import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from decimal import Decimal

# Import UploadFile for file uploads (still needed for the image fields in UserCreate)
from fastapi import UploadFile

# Schema for data received when creating a user (Request Body)
class UserCreate(BaseModel):
    """
    Pydantic model for user registration request data (primarily for documentation
    when using multipart/form-data).
    Includes fields typically required for creating a new user account.
    """
    name: str = Field(..., description="Full name of the user.")
    email: EmailStr = Field(..., description="User's email address (must be unique).") # Use EmailStr for validation
    phone_number: str = Field(..., max_length=20, description="User's phone number (must be unique).")
    password: str = Field(..., min_length=8, description="User's password (will be hashed).") # Add min_length for password strength

    # Required fields as per your list
    city: str = Field(..., description="City of the user.")
    state: str = Field(..., description="State of the user.")
    pincode: int = Field(..., description="Pincode of the user's location.") # Assuming pincode is an integer

    # Optional fields that might be provided during registration or set later
    user_type: Optional[str] = Field("live", max_length=100, description="Type of user (e.g., 'trader', 'investor'). Defaults to 'live'.")
    security_question: Optional[str] = Field(None, max_length=255, description="Security question for recovery.")
    fund_manager: Optional[str] = Field(None, max_length=255, description="Name of the assigned fund manager.")
    is_self_trading: Optional[int] = Field(1, description="Flag indicating if the user is self-trading (0 or 1). Defaults to 1.")
    group_name: Optional[str] = Field(None, max_length=255, description="Name of the trading group the user belongs to.")

    # Proof fields: Strings for type, UploadFile for images (handled in endpoint)
    id_proof: Optional[str] = Field(None, description="Type of ID proof (e.g., Aadhaar, Passport).")
    id_proof_image: Optional[UploadFile] = Field(None, description="ID proof image file.")
    address_proof: Optional[str] = Field(None, description="Type of address proof (e.g., Utility Bill, Bank Statement).")
    address_proof_image: Optional[UploadFile] = Field(None, description="Address proof image file.")

    # Note: Financial fields (wallet_balance, leverage, margin, etc.)
    # and unique identifiers (account_number, reffered_code) are typically
    # generated by the backend after registration, so they are NOT included
    # in the UserCreate schema.


# Schema for data returned after creating/fetching a user (Response Body)
class UserResponse(BaseModel):
    """
    Pydantic model for user response data.
    Excludes sensitive information like the hashed password.
    Includes fields typically returned after fetching user details.
    """
    id: int = Field(..., description="Unique identifier of the user.")
    name: str = Field(..., description="Full name of the user.")
    email: EmailStr = Field(..., description="User's email address.")
    phone_number: str = Field(..., description="User's phone number.")
    user_type: Optional[str] = Field(None, description="Type of user.")

    # Financial Fields (often included in user profile response)
    wallet_balance: Decimal = Field(..., max_digits=18, decimal_places=8, description="Current wallet balance.")
    leverage: Decimal = Field(..., max_digits=10, decimal_places=2, description="User's leverage setting.")
    margin: Decimal = Field(..., max_digits=18, decimal_places=8, description="User's current margin.")

    account_number: Optional[str] = Field(None, description="Unique platform account number.")
    group_name: Optional[str] = Field(None, description="Name of the trading group.")
    status: int = Field(..., description="User account status (0 or 1).") # Assuming 0/1 integer status
    isActive: int = Field(..., description="User active status (0 or 1).") # Assuming 0/1 integer status

    security_question: Optional[str] = Field(None, description="User's security question.")
    city: str = Field(..., description="City of the user.")
    state: str = Field(..., description="State of the user.")
    pincode: Optional[int] = Field(None, description="Pincode of the user's location.") # Pincode might be optional in response if not always set

    fund_manager: Optional[str] = Field(None, description="Name of the assigned fund manager.")
    is_self_trading: int = Field(..., description="Flag indicating if the user is self-trading.")

    # Proof fields (Storing paths to the images and string identifiers)
    id_proof: Optional[str] = Field(None, description="Type of ID proof (e.g., Aadhaar, Passport).")
    id_proof_image: Optional[str] = Field(None, description="Path to the ID proof image file.")
    address_proof: Optional[str] = Field(None, description="Type of address proof (e.g., Utility Bill, Bank Statement).")
    address_proof_image: Optional[str] = Field(None, description="Path to the address proof image file.")

    bank_ifsc_code: Optional[str] = Field(None, description="Bank IFSC code.")
    bank_holder_name: Optional[str] = Field(None, description="Bank account holder name.")
    bank_branch_name: Optional[str] = Field(None, description="Bank branch name.")
    bank_account_number: Optional[str] = Field(None, description="Bank account number.")

    reffered_code: Optional[str] = Field(None, description="User's unique referral code.")
    referred_by_id: Optional[int] = Field(None, description="ID of the user who referred this user.")
    referral_code: Optional[str] = Field(None, description="User's own referral code.")

    created_at: datetime.datetime = Field(..., description="Timestamp when the user was created.")
    updated_at: datetime.datetime = Field(..., description="Timestamp when the user was last updated.")

    # Configuration for Pydantic to work with SQLAlchemy models
    class Config:
        from_attributes = True


# --- New Schema for Updating a User ---
class UserUpdate(BaseModel):
    """
    Pydantic model for updating user data.
    All fields are optional, allowing partial updates.
    Sensitive fields like password should be updated via dedicated endpoints.
    """
    name: Optional[str] = Field(None, description="Full name of the user.")
    email: Optional[EmailStr] = Field(None, description="User's email address.")
    phone_number: Optional[str] = Field(None, max_length=20, description="User's phone number.")
    user_type: Optional[str] = Field(None, max_length=100, description="Type of user (e.g., 'trader', 'investor').")
    security_question: Optional[str] = Field(None, max_length=255, description="Security question for recovery.")
    fund_manager: Optional[str] = Field(None, max_length=255, description="Name of the assigned fund manager.")
    is_self_trading: Optional[int] = Field(None, description="Flag indicating if the user is self-trading (0 or 1).")
    group_name: Optional[str] = Field(None, max_length=255, description="Name of the trading group the user belongs to.")
    city: Optional[str] = Field(None, description="City of the user.")
    state: Optional[str] = Field(None, description="State of the user.")
    pincode: Optional[int] = Field(None, description="Pincode of the user's location.")

    # Financial fields can also be updated, but require careful handling (locking)
    # Note: Direct updates to wallet_balance might be restricted via this endpoint
    # and handled through specific deposit/withdrawal/trade endpoints.
    # Including them here for completeness, assuming logic in CRUD handles this.
    wallet_balance: Optional[Decimal] = Field(None, max_digits=18, decimal_places=8, description="Current wallet balance.")
    leverage: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2, description="User's leverage setting.")
    margin: Optional[Decimal] = Field(None, max_digits=18, decimal_places=8, description="User's current margin.")

    # Status fields might be updated by admins
    status: Optional[int] = Field(None, description="User account status (0 or 1).")
    isActive: Optional[int] = Field(None, description="User active status (0 or 1).")

    # Bank details
    bank_ifsc_code: Optional[str] = Field(None, max_length=50, description="Bank IFSC code.")
    bank_holder_name: Optional[str] = Field(None, max_length=255, description="Bank account holder name.")
    bank_branch_name: Optional[str] = Field(None, max_length=255, description="Bank branch name.")
    bank_account_number: Optional[str] = Field(None, max_length=100, description="Bank account number.")

    # Referral fields (might be updated by admins)
    referred_by_id: Optional[int] = Field(None, description="ID of the user who referred this user.")
    reffered_code: Optional[str] = Field(None, description="User's unique referral code.")

    # Note: Password should NOT be updated via this schema. Use a dedicated endpoint.
    # id_proof and address_proof *types* might be updatable, but images require file upload endpoints.
    id_proof: Optional[str] = Field(None, description="Type of ID proof (e.g., Aadhaar, Passport).")
    address_proof: Optional[str] = Field(None, description="Type of address proof (e.g., Utility Bill, Bank Statement).")


# --- OTP and Password Reset Schemas (Keep Existing) ---
# ... (Keep the existing SendOTPRequest, VerifyOTPRequest, RequestPasswordReset, ResetPasswordConfirm, StatusResponse schemas here) ...

class SendOTPRequest(BaseModel):
    """
    Pydantic model for the request body to send an OTP (for verification or password reset).
    """
    email: EmailStr = Field(..., description="Email address to send the OTP to.")

class VerifyOTPRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address associated with the OTP.")
    otp_code: str = Field(..., description="The OTP code received by the user.")
    user_type: Optional[str] = Field("live", description="User type (e.g., 'live', 'demo'). Defaults to 'live'.")


class RequestPasswordReset(BaseModel):
    email: EmailStr = Field(..., description="Email address to send the password reset OTP to.")
    user_type: Optional[str] = Field("live", description="User type (e.g., 'live', 'demo'). Defaults to 'live'.")


class ResetPasswordConfirm(BaseModel):
    email: EmailStr = Field(..., description="Email address associated with the OTP.")
    user_type: Optional[str] = Field("live", description="User type (e.g., 'live', 'demo'). Defaults to 'live'.")
    new_password: str = Field(..., min_length=8, description="The new password for the user account.")

class PasswordResetVerifyResponse(BaseModel):
    verified: bool = Field(..., description="Whether the OTP was successfully verified.")
    message: str = Field(..., description="Response message.")
    reset_token: Optional[str] = Field(None, description="Reset token to be used for confirming password reset.")

class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address associated with the OTP.")
    user_type: Optional[str] = Field("live", description="User type (e.g., 'live', 'demo'). Defaults to 'live'.")
    new_password: str = Field(..., min_length=8, description="The new password for the user account.")
    reset_token: str = Field(..., description="Reset token obtained after OTP verification.")


class StatusResponse(BaseModel):
    """
    Generic Pydantic model for simple status responses.
    """
    message: str = Field(..., description="Response message.")


# --- Authentication Schemas (Keep Existing) ---
# in app/schemas/user.py

from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password")
    user_type: Optional[str] = Field("live", description="Type of user, defaults to 'live'")

class Token(BaseModel):
    """
    Pydantic model for JWT tokens returned upon successful authentication.
    """
    access_token: str = Field(..., description="The JWT access token.")
    refresh_token: str = Field(..., description="The JWT refresh token.")
    token_type: str = Field("bearer", description="The type of token (usually 'bearer').")

class TokenRefresh(BaseModel):
    """
    Pydantic model for refreshing an access token using a refresh token.
    """
    refresh_token: str = Field(..., description="The JWT refresh token.")

from pydantic import BaseModel, EmailStr, Field

# In app/schemas/user.py (or inline for this example)
# from pydantic import BaseModel, EmailStr, Field

class SignupSendOTPRequest(BaseModel):
    email: EmailStr
    user_type: Optional[str] = Field("live", description="User type, defaults to 'live'")

class SignupVerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=8)
    user_type: Optional[str] = Field("live", description="User type, defaults to 'live'")