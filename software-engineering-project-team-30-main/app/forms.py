
from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, StringField, BooleanField, EmailField, TextAreaField, DecimalField,SubmitField, TimeField, DateField, FloatField, SelectField, FormField, SearchField
from wtforms.validators import DataRequired, Length, ValidationError, Regexp, Email, NumberRange, Optional, EqualTo
from datetime import date, timedelta, datetime, time
from decimal import Decimal

from .models import JourneyStatusEnum, JourneyTypeEnum, DriverStatusEnum, BookingStatusEnum, PaymentStatusEnum


class SignupForm(FlaskForm):
    first_name = StringField('Fname', validators=[DataRequired(), Length(2, 20, message='i.e. Jennifer')])
    last_name = StringField('Lname', validators=[DataRequired(), Length(2, 20, message='i.e. Lopez')])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 20, message='Keep it complex! Your password must be between 8-50 characters.')])
    confirmpassword = PasswordField('Password2', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    email = EmailField('email', validators=[DataRequired(), Email(), Length(10, 50, message='i.e. jenniferlopez@gmail.com')])
    phone_number = StringField('Phone', validators=[DataRequired()])
    submit = SubmitField('Sign Up')


class LoginForm(FlaskForm):
    email = EmailField('Email Address',
                       validators=[DataRequired(), Email(), Length(10, 40, message="jenniferlopez@gmail.con")])
    password = PasswordField('Password', validators=[DataRequired(), Length(7, 30)])
    submit = SubmitField('Log In')


class ReviewForm(FlaskForm):
    rating = IntegerField('Star Rating', validators=[DataRequired()])
    comment = TextAreaField('Comment', validators=[DataRequired(), Length(5, 500, message="Tell us your thoughts!")])
    submit = SubmitField('Rate')


class LocationForm(FlaskForm):
    nickname = StringField('Nickname', validators=[Optional()])
    addressLine1 = StringField('Address Line One',
                               validators=[Optional(), Length(2, 100, message='i.e. 123 House')])
    postcode = StringField('Postcode', validators=[Optional()])
    city = StringField('City', validators=[Optional(), Length(2, 30)])
    country = StringField('Country', validators=[Optional(), Length(2, 30)])
    submit = SubmitField('Add Location')


    # need to add validation checking for valid postcode (can use re)

    # need to change car registration for car nickname

MAX_SEATS_MSG = "Must be between 1 and 6 seats"
class CarRegistrationForm(FlaskForm):
    car_nickname = StringField('Car name', validators=[DataRequired(), Length(2, 30)])
    reg_plate = StringField('Registration Number', validators=[DataRequired(), Length(2, 7)])
    make = StringField('Brand', validators=[DataRequired(), Length(2, 30)])
    model = StringField('Model', validators=[DataRequired(), Length(2, 30)])
    colour = StringField('Colour', validators=[DataRequired(), Length(2, 30)])
    max_seats = IntegerField('Max Seats', validators=[DataRequired(), NumberRange(1, 6, MAX_SEATS_MSG)])
    submit = SubmitField('Register Car')


class DriverRegistrationForm(CarRegistrationForm):
    liscence_num = StringField('Drivers Liscence Number', validators=[DataRequired(), Length(16, 16)])
    submit = SubmitField('Register')


class JourneyForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', render_kw={"min": date.today()},
                     validators=[DataRequired()])
    time = TimeField('Time', format='%H:%M', validators=[DataRequired()])
    reg_plate = SelectField('Car', validators=[DataRequired()])
    previous_pickup_location = SelectField('Pickup Location', validators=[Optional()])
    previous_dropoff_location = SelectField('Drop-off Location', validators=[Optional()])
    journey_type = SelectField('Journey Type', choices=[(type.name, type.value) for type in JourneyTypeEnum],
                               validators=[DataRequired()])
    price_per_person = FloatField('Price per person',
                                    validators=[DataRequired(), NumberRange(min=0)])
    journey_status = SelectField('Journey Status',
                                 choices=[(status.name, status.value) for status in JourneyStatusEnum],
                                 validators=[DataRequired()])
    submit = SubmitField('Create Journey')


class DeleteAccountForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 20, message='Once the correct password is entered your account will be deleted')])
    submit = SubmitField('Delete Account!!!')
    
    
class AccessProfileForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 20, message='Input password to gain access to edit profile')])
    submit = SubmitField('Edit Profile')
    
class EditProfileForm(FlaskForm):
    first_name = StringField('Fname', validators=[DataRequired(), Length(2, 20, message='i.e. Jennifer')])
    last_name = StringField('Lname', validators=[DataRequired(), Length(2, 20, message='i.e. Lopez')])
    email = EmailField('email', validators=[DataRequired(), Email(), Length(10, 50, message='i.e. jenniferlopez@gmail.com')])
    phone_number = StringField('Phone', validators=[DataRequired()])
    submit = SubmitField('Edit Details') 


class ConfigureCostForm(FlaskForm):
    cost =  DecimalField('Configure Cost', validators=[DataRequired(), NumberRange(min=0)])
    journey_id = IntegerField('Journey ID')
    booking_id = IntegerField('Booking ID')
    submit = SubmitField('Book Now')
    
#for when you view revenue
class RevenueSettingsForm(FlaskForm):
    timeframe = SelectField('Choose a timeframe:', choices=[('Week', 'Week'), ('Last 30 Days', 'Month')])
    end_date = DateField('Select an end date', validators=[DataRequired()], render_kw={"max": date.today().isoformat()} )
    revenue_type = SelectField('Choose Whos Revenue to view', choices=[]) #wil be dynamically filled with 'manager' and/or 'driver' depending on users current roles

#for changing booking fee
class BookingFeeForm(FlaskForm):
    booking_fee = DecimalField('Booking Fee %', validators=[NumberRange(min=0, max=100)])
    submit = SubmitField('Configure')

#for changing discount percentage
class DiscountForm(FlaskForm):
    discount_perc = DecimalField('Discount %', validators=[NumberRange(min=0, max=100)])
    avg_trips = IntegerField('Average Trips per Week to recieve discount', validators=[NumberRange(min=0, max=7)])
    submit = SubmitField('Configure')

#used to search users by name or email
class SearchUserForm(FlaskForm):
    first_name = StringField('Fname')
    last_name = StringField('Lname')
    email = EmailField('email', validators=[Email()])
    submit = SubmitField('Submit')

#used when assigning a user to a manager status
class SelectNewManagerForm(FlaskForm):    
    user_list = SelectField('Select a User to Assign Manager Status', choices=[], validators=[DataRequired()])
    submit = SubmitField('Submit')

class FilterJourneysForm(FlaskForm):
    date = DateField('Filter by Journey date', render_kw={"min": date.today().isoformat()} )
    time = TimeField('Time', render_kw={"min" : datetime.now() + timedelta(minutes=15)})
    pickup_postcode = StringField('Pickup Postcode', validators=[Optional()])
    dropoff_postcode = StringField('Dropoff Postcode', validators=[Optional()])
    j_type = SelectField('Choose Journey Type', choices=[('ONE TIME', "One Time"), ('DAILY', "Daily"), ('WEEKLY', "Weekly")])
    sort_by = SelectField('Sort By', choices=[("time", "Time"), ("rating", "Driver Rating")])

class ResetPasswordRequestForm(FlaskForm):
    email = EmailField('Email Address', validators=[DataRequired(), Email(), Length(10, 40, message="jenniferlopez@gmail.con")])
    submit = SubmitField('Request Password Reset')
    

class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired()])
    password2 = PasswordField("Repeat Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Confirm Password Reset")
    
    
class SupportPage(FlaskForm):
    name = StringField('name', validators=[DataRequired(), Length(2, 20, message='i.e. Jennifer')])
    email = EmailField('email', validators=[DataRequired(), Email(), Length(10, 50, message='i.e. jenniferlopez@gmail.com')])
    subject = StringField('subject', validators=[DataRequired(), Length(2, 20, message='i.e. Lopez')])
    message = TextAreaField('message', validators=[DataRequired(), Length(20, 300, message='i.e. Lopez')])
    submit = SubmitField("send message")


class ChangeAvailabilityForm(FlaskForm):
    availability_status = SelectField('Status', choices=[("ON HOLIDAY", "On Holiday"), ("ILLNESS", "Illness"), ("INACTIVE", "Other/Temporarily Taking a Break")])
    end_date = DateField('Last day of unavailability', validators=[DataRequired()], render_kw={"min": date.today().isoformat()} )

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField("Old Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired()])

