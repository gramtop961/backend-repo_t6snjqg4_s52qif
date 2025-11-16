"""
Database Schemas for Car Cleaning Marketplace

Each Pydantic model represents a collection in MongoDB. The collection name is the lowercase of the class name.

Models:
- Cleaner -> "cleaner"
- Booking -> "booking"
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime


class Location(BaseModel):
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    address: Optional[str] = Field(None, description="Human readable address")
    city: Optional[str] = Field(None, description="City or area name")


class ServiceOption(BaseModel):
    name: str = Field(..., description="Service name, e.g., 'Exterior Wash'")
    description: Optional[str] = Field(None, description="Short description")
    price: float = Field(..., ge=0, description="Price for this service")
    duration_minutes: int = Field(..., ge=10, le=600, description="Estimated duration in minutes")


class Cleaner(BaseModel):
    name: str = Field(..., description="Cleaner full name or business name")
    provider_type: Literal["individual", "company"] = Field("individual", description="Whether this provider is an individual or a company")
    phone: Optional[str] = Field(None, description="Contact phone number")
    bio: Optional[str] = Field(None, description="Short profile/bio")
    photo_url: Optional[str] = Field(None, description="Profile photo URL")
    rating: float = Field(4.8, ge=0, le=5, description="Average rating 0-5")
    total_reviews: int = Field(0, ge=0, description="Total number of reviews")
    is_available: bool = Field(True, description="Availability flag")
    location: Location = Field(..., description="Current service location")
    services: List[ServiceOption] = Field(default_factory=list, description="Offered services")
    base_callout_fee: float = Field(0, ge=0, description="Optional callout fee")


class BookingCustomer(BaseModel):
    name: str
    phone: str
    email: Optional[EmailStr] = None


class CarDetails(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    plate: Optional[str] = None


class Booking(BaseModel):
    cleaner_id: str = Field(..., description="Reference to Cleaner _id string")
    service_name: str = Field(..., description="Chosen service name")
    service_price: float = Field(..., ge=0, description="Price of chosen service")
    scheduled_time: datetime = Field(..., description="ISO datetime for service start")
    location: Location
    customer: BookingCustomer
    car: Optional[CarDetails] = None
    notes: Optional[str] = None

    total_price: float = Field(..., ge=0, description="Total price including callout")
    commission_rate: float = Field(0.1, ge=0, le=1, description="Platform commission rate")
    commission_amount: float = Field(..., ge=0, description="Commission amount")
    net_amount: float = Field(..., ge=0, description="Net to cleaner after commission")

    status: str = Field("pending", description="pending | confirmed | completed | cancelled")
    payment_status: str = Field("unpaid", description="unpaid | paid | refunded")
    payment_reference: Optional[str] = None
