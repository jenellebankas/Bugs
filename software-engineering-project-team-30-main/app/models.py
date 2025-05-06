from app import db
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app
from sqlalchemy import Enum
import enum
from sqlalchemy.orm import relationship

class DriverStatusEnum(enum.Enum):
    ACTIVE = "ACTIVE"
    HOLIDAY = "ON HOLIDAY"
    INACTIVE = "INACTIVE"

class BookingStatusEnum(enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED" #to do with price configuration
    INACTIVE = "INACTIVE"
    CANCELLED = "CANCELLED"
    COMPLETE = "COMPLETE"

class JourneyStatusEnum(enum.Enum):
    WAITING = "WAITING"
    FULL = "FULLY BOOKED"
    INACTIVE = "INACTIVE"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"

class JourneyTypeEnum(enum.Enum):
    ONE = "ONE TIME"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"

class PaymentStatusEnum(enum.Enum):
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    REFUNDED = "REFUNDED"

#people 

class User(UserMixin, db.Model):
    __tablename__='Users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255))
    phone_number = db.Column(db.String(255), nullable=False)
    stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True)
    
    def generate_reset_password_token(self):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps(self.email, salt=self.password)
    
    def generate_booking_confirmation_token(self):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps(self.email, salt=self.password)
    
    @staticmethod
    def validate_reset_password_token(token: str, user_id: int):
        user = db.session.get(User, user_id)

        if user is None:
            return None

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            token_user_email = serializer.loads(
                token,
                max_age=current_app.config["RESET_PASS_TOKEN_MAX_AGE"],
                salt=user.password,
            )
        except (BadSignature, SignatureExpired):
            return None

        if token_user_email != user.email:
            return None

        return user

    @property
    def role(self):
        return "User"
        
    #Driver Relationship
    drivers = relationship("Driver", backref="User")
    
    #get driver id without querying driver
    @property
    def driver_id(self):
        if self.drivers:
                return self.drivers[0].driver_id  
        else:
            return None

    #check if user is a driver
    @property
    def is_driver(self):
        if self.drivers:
            if self.drivers[0].driver_id:
                return True
            
        return False 

    # Manager Relationship
    managers = relationship("Manager", backref="User")

    #get manager id
    @property
    def manager_id(self):
        if self.managers:
                return self.managers[0].manager_id  
        else:
            return None

    #check if user is manager
    @property
    def is_manager(self):
        if self.managers:
            if self.managers[0].manager_id:
                return True
        
        return False 

    
class Manager(db.Model):
    __tablename__='Managers'
    manager_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', name='user_id'))

    @property
    def role(self):
        return "Manager"
    

class Driver(db.Model):
    __tablename__='Drivers'
    driver_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', name='user_id'))
    num_trips = db.Column(db.Integer, nullable=False)
    license_num = db.Column(db.String, unique=True, nullable=False)
    driver_status = db.Column(db.String, nullable=True, default='ACTIVE')
    driver_rating = db.Column(db.Float, nullable=True)
    num_ratings = db.Column(db.Integer, nullable=True)
    unavailable_end_date = db.Column(db.Date, nullable=True)

    @property
    def role(self):
        return "Driver"
        
    
# journeys / locations


class Booking(db.Model):
    __tablename__="Bookings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', name='user_id'))
    journey_id = db.Column(db.Integer, db.ForeignKey('Journeys.id', name='journey_id'))
    price = db.Column(db.Float) # to configure price they pay
    payment_method_id = db.Column(db.String, db.ForeignKey('PaymentMethods.id', name='payment_method_id'))
    payment_intent_id = db.Column(db.String)
    payment_status = db.Column(Enum(PaymentStatusEnum), nullable=False, default=PaymentStatusEnum.PENDING)
    booking_status = db.Column(Enum(BookingStatusEnum), nullable=False, default=BookingStatusEnum.PENDING)
    reviewed = db.Column(db.Boolean, nullable=False, default=0)

    journey = db.relationship("Journey", backref="bookings", lazy="joined")
    payment_method = db.relationship("PaymentMethod", backref="bookings", lazy="joined")



class Journey(db.Model):
    __tablename__="Journeys"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('Drivers.driver_id', name='driver_id'))
    reg_plate = db.Column(db.String, db.ForeignKey('Cars.reg_plate', name='reg_plate'))
    pickup_location = db.Column(db.Integer, db.ForeignKey('Locations.id', name='pickup_location'))
    dropoff_location = db.Column(db.Integer, db.ForeignKey('Locations.id', name='dropoff_location'))
    journey_type = db.Column(Enum(JourneyTypeEnum), nullable=False, default=JourneyTypeEnum.ONE)
    price_per_person = db.Column(db.Float, nullable=False) #this is initial cost. may be indiviudally changed by a user
    journey_status = db.Column(Enum(JourneyStatusEnum), nullable=False, default=JourneyStatusEnum.WAITING)
    num_confirmed = db.Column(db.Integer, nullable=False)

    car = db.relationship("Car", backref="journeys", lazy="joined") #added
    driver = db.relationship("Driver", backref="journeys", lazy="joined")

    

class Location(db.Model):
    __tablename__="Locations"
    id = db.Column(db.Integer, primary_key=True)
    address_line_1 = db.Column(db.String(100), nullable=False)
    postcode = db.Column(db.String(8), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    nickname = db.Column(db.String(50), nullable=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('Drivers.driver_id', name='driver_id'))

# miscelanous

class Discount(db.Model):
    __tablename__="Discounts"
    id = db.Column(db.Integer, primary_key=True)
    avg_trips = db.Column(db.Integer, nullable=False) #per week to be able to get discount
    discount_percentage = db.Column(db.Float, nullable=False)

#keeps a record of previous fees
class BookingFees(db.Model):
    __tablename__="BookingFees"
    id = db.Column(db.Integer, primary_key=True)
    booking_fee_percentage = db.Column(db.Float, nullable=False) #0-1 as a percentage
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

class Review(db.Model):
    __tablename__="Reviews"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('Bookings.id', name='booking_id'),  nullable=False)
    review_title = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=True)

    booking = db.relationship('Booking', backref='reviews')


class Car(db.Model):
    __tablename__="Cars"
    reg_plate = db.Column(db.String(12), primary_key=True)
    car_nickname = db.Column(db.String(255), nullable=False)
    make = db.Column(db.String(50),  nullable=True)
    model = db.Column(db.String(50), nullable=True)
    colour = db.Column(db.String(50), nullable=True)
    max_seats = db.Column(db.Integer,  nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('Drivers.driver_id', name='driver_id'),  nullable=False)


class PaymentMethod(db.Model):
    __tablename__ = 'PaymentMethods'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', name='user_id'))
    payment_method_id = db.Column(db.String(255), nullable=False, unique=True)
    brand = db.Column(db.String(50), nullable=False)
    last4 = db.Column(db.String(4), nullable=False)
    exp_date = db.Column(db.String(5), nullable=False) # MM/YY

    user = db.relationship('User', backref=db.backref('payment_methods', lazy=True))
