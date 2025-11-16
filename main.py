import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Cleaner, Booking, ServiceOption

app = FastAPI(title="Car Cleaning Marketplace API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utils
class CleanerResponse(BaseModel):
    id: str
    name: str
    rating: float
    total_reviews: int
    is_available: bool
    photo_url: Optional[str]
    bio: Optional[str]
    services: List[ServiceOption]
    location: dict
    base_callout_fee: float


@app.get("/")
def root():
    return {"message": "Car Cleaning Marketplace API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or ""
            try:
                collections = db.list_collection_names()
                response["collections"] = collections
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# Seed some demo cleaners if empty (for first run UX)
@app.post("/seed")
def seed_cleaners():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    has_any = db["cleaner"].count_documents({}) > 0
    if has_any:
        return {"seeded": False, "message": "Cleaners already exist"}

    demo = [
        {
            "name": "Sparkle Pro Detailing",
            "phone": "+1-555-0110",
            "bio": "Premium mobile car wash & detailing",
            "photo_url": "https://images.unsplash.com/photo-1609137144813-7d9921338f9b?w=800",
            "rating": 4.9,
            "total_reviews": 128,
            "is_available": True,
            "location": {"lat": 37.773972, "lng": -122.431297, "address": "San Francisco, CA"},
            "base_callout_fee": 5,
            "services": [
                {"name": "Exterior Wash", "description": "Foam wash & dry", "price": 25, "duration_minutes": 30},
                {"name": "Interior Clean", "description": "Vacuum & wipe down", "price": 35, "duration_minutes": 45},
                {"name": "Full Detail", "description": "In & Out premium detail", "price": 99, "duration_minutes": 120},
            ],
        },
        {
            "name": "EcoShine Mobile",
            "phone": "+1-555-0111",
            "bio": "Waterless eco-friendly clean",
            "photo_url": "https://images.unsplash.com/photo-1515923162031-1d7cfbca8b89?w=800",
            "rating": 4.7,
            "total_reviews": 76,
            "is_available": True,
            "location": {"lat": 37.784, "lng": -122.409, "address": "SoMa, SF"},
            "base_callout_fee": 3,
            "services": [
                {"name": "Quick Wash", "description": "15-min express", "price": 15, "duration_minutes": 15},
                {"name": "Interior Refresh", "description": "Vacuum & mats", "price": 25, "duration_minutes": 25},
            ],
        },
    ]

    for item in demo:
        create_document("cleaner", item)
    return {"seeded": True, "count": len(demo)}


@app.get("/cleaners", response_model=List[CleanerResponse])
def list_cleaners(lat: Optional[float] = None, lng: Optional[float] = None, radius_km: float = 25.0):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # For simplicity, return all for now. In real case, apply geo filtering.
    docs = get_documents("cleaner")
    results: List[CleanerResponse] = []
    for d in docs:
        results.append(CleanerResponse(
            id=str(d.get("_id")),
            name=d.get("name"),
            rating=d.get("rating", 0),
            total_reviews=d.get("total_reviews", 0),
            is_available=d.get("is_available", True),
            photo_url=d.get("photo_url"),
            bio=d.get("bio"),
            services=d.get("services", []),
            location=d.get("location", {}),
            base_callout_fee=d.get("base_callout_fee", 0.0)
        ))
    return results


class CreateBookingRequest(BaseModel):
    cleaner_id: str
    service_name: str
    scheduled_time: str  # ISO string
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    car_make: Optional[str] = None
    car_model: Optional[str] = None
    car_color: Optional[str] = None
    car_plate: Optional[str] = None
    notes: Optional[str] = None


@app.post("/book")
def create_booking(payload: CreateBookingRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    cleaner = db["cleaner"].find_one({"_id": ObjectId(payload.cleaner_id)})
    if not cleaner:
        raise HTTPException(status_code=404, detail="Cleaner not found")

    # Find chosen service
    service = None
    for s in cleaner.get("services", []):
        if s.get("name") == payload.service_name:
            service = s
            break
    if not service:
        raise HTTPException(status_code=400, detail="Service not offered by cleaner")

    service_price = float(service.get("price", 0))
    callout = float(cleaner.get("base_callout_fee", 0))
    total = service_price + callout

    commission_rate = 0.1
    commission_amount = round(total * commission_rate, 2)
    net_amount = round(total - commission_amount, 2)

    booking_doc = {
        "cleaner_id": payload.cleaner_id,
        "service_name": payload.service_name,
        "service_price": service_price,
        "scheduled_time": payload.scheduled_time,
        "location": {
            "lat": payload.lat,
            "lng": payload.lng,
            "address": payload.address,
        },
        "customer": {
            "name": payload.customer_name,
            "phone": payload.customer_phone,
            "email": payload.customer_email,
        },
        "car": {
            "make": payload.car_make,
            "model": payload.car_model,
            "color": payload.car_color,
            "plate": payload.car_plate,
        },
        "notes": payload.notes,
        "total_price": total,
        "commission_rate": commission_rate,
        "commission_amount": commission_amount,
        "net_amount": net_amount,
        "status": "pending",
        "payment_status": "unpaid",
        "payment_reference": None,
    }

    booking_id = create_document("booking", booking_doc)

    return {
        "booking_id": booking_id,
        "total_price": total,
        "commission_amount": commission_amount,
        "net_amount": net_amount,
        "message": "Booking created. Proceed to payment to confirm.",
    }


@app.get("/bookings")
def list_bookings():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("booking")
    # Clean up ObjectId for client consumption
    for d in docs:
        d["_id"] = str(d["_id"]) if d.get("_id") else None
    return docs


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
