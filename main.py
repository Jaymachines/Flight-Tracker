from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime

# 1. Setup the SQLite Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./flight_data.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Define le SQL Table Structure
class FlightPriceDB(Base):
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String, index=True)      # e.g., "YQB-TYO"
    airline = Column(String)                   # e.g., "Aggregated"
    price = Column(Float)                      # e.g., 806.0
    departure_date = Column(String, index=True)# e.g., "2026-09-01"
    scrape_date = Column(DateTime, index=True) # When you ran the script
    source = Column(String)

# Create la table dans le database file
Base.metadata.create_all(bind=engine)

# 3. Define le Incoming Data Format ce qui est send par le database
class FlightPricePayload(BaseModel):
    route_id: str
    airline: str
    price: float
    departure_date: str
    timestamp: str 
    source: str

app = FastAPI(title="StreetPulse Flight Engine")

# la dependance à ouvrir le database sans tout brake up comme un idiot
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Receiving Endpoint
@app.post("/ingest_price")
def ingest_price(payload: FlightPricePayload, db: Session = Depends(get_db)):
    # Convertir le string timestamp en Python DateTime object
    try:
        parsed_time = datetime.datetime.strptime(payload.timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        parsed_time = datetime.datetime.utcnow()

    # Create a new row for the database
    new_price_entry = FlightPriceDB(
        route_id=payload.route_id,
        airline=payload.airline,
        price=payload.price,
        departure_date=payload.departure_date,
        scrape_date=parsed_time,
        source=payload.source
    )
    
    # Save it permanent
    db.add(new_price_entry)
    db.commit()
    db.refresh(new_price_entry)
    
    return {"status": "success", "logged_id": new_price_entry.id}