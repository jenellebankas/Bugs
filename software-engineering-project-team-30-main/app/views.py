from app import app, db, admin, bcrypt, login_manager
from flask_mailman import Mail, EmailMessage
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, time, timedelta, datetime
import stripe
from flask_mailman import Mail, EmailMessage
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import date, time, timedelta, datetime
import schedule, time, threading #for scheduling
from flask import session, render_template, redirect, url_for, flash, request, jsonify, render_template_string, render_template_string
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf.csrf import validate_csrf
import re

##### formatted like this because every time we commit it removes somebody elses forms
#enums
from .forms import JourneyTypeEnum, JourneyStatusEnum, BookingStatusEnum, PaymentStatusEnum
#registration stuff
from .forms import LoginForm, SignupForm, DriverRegistrationForm, CarRegistrationForm
#user profile stuff
from .forms import ChangePasswordForm, ResetPasswordForm, ResetPasswordRequestForm, DeleteAccountForm ,AccessProfileForm, EditProfileForm, ChangeAvailabilityForm
#journeys and bookings
from .forms import LocationForm, JourneyForm, FilterJourneysForm
#manager stuff
from .forms import SelectNewManagerForm, SearchUserForm, RevenueSettingsForm, BookingFeeForm, DiscountForm, ConfigureCostForm 
#reviews and communication
from .forms import SupportPage

from .forms import DriverStatusEnum

from .models import User, Driver, Car, Manager, Journey, Location, Discount, Review, Booking, BookingFees, PaymentMethod
from app import app, db, admin, bcrypt, login_manager
from flask_mailman import Mail, EmailMessage
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.exc import IntegrityError 
from werkzeug.security import check_password_hash
from datetime import date, time, timedelta, datetime
import schedule, time, threading #for scheduling
from flask import Flask, render_template, jsonify, request
from flask import render_template
from datetime import date, timedelta
from sqlalchemy import and_  # NEW IMPORT
import requests # NEW IMPORT
from flask import jsonify, request #NEW IMPORT

stripe.api_key = "sk_test_51Qw2FeJcESkTiOzcPf3JwS6oCPhHSDGvj2T5JH91Rv9E9v3s8bhs5NE2CdhTwm0qVejshjHORvt9CqSi31XYt9MY00pIGE0vtj"
login_manager.login_view = "login"
login_manager.login_message = "Please Login to access this page"

#Scheduler----------------------------------------------------------
def run_scheduler():
    app.logger.info("Starting Scheduler...")
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start the scheduler in a new thread
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True  # Daemonize the thread to stop it when the main application exits
scheduler_thread.start()

#-------------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('homepage.html',title= 'Home')

# user signup / login ------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = SignupForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data)
            new_user = User(first_name= form.first_name.data, last_name= form.last_name.data, email=form.email.data, phone_number= form.phone_number.data, password=hashed_password, )
            db.session.add(new_user)
            db.session.commit()
            flash('Your account has been created!', 'success')
            return redirect(url_for('login'))

        except IntegrityError:
            db.session.rollback()
            flash('Email is already in use, try again!', 'danger')
        
    return render_template('signUp.html', form=form, page='register', title='registration')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)

            if user.is_driver:
                check_driver_availability(user.driver_id)

            return redirect(url_for('profile'))
        else:
            # Pass the error message directly to the template (no flash needed)
            error_message = 'Invalid email or password'
            return render_template('login.html', title='Skrrrt Login', form=form, page='login', error_message=error_message)

    return render_template('login.html', title='Skrrrt Login', form=form, page='login')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


#access profile user information
#PROFILE --------------------------------------------------------------------

def check_driver_availability(driver_id):
    driver = Driver.query.get(driver_id)

    if driver.driver_status != DriverStatusEnum.ACTIVE:
        today = date.today()
        try:

            if driver.unavailable_end_date == today:
                set_driver_available(driver.driver_id)

        except:
            db.session.rollback()
            flash("Error when changing driver availability", "danger")

@app.route('/set-avaiable/<int:driver_id>', methods=['GET', 'POST'])
def set_driver_available(driver_id):
    #get driver
    try:
        driver = Driver.query.get(driver_id)

        if driver.driver_status != DriverStatusEnum.ACTIVE.value:

            driver.driver_status = DriverStatusEnum.ACTIVE.value
            driver.unavailable_end_date = None
            db.session.commit()
            flash("Set driver as available")

        else:
            flash("Driver is already Available", "warning")
    except:
        db.session.rollback()
        flash("Error setting driver as Available", "warning")

    return redirect(url_for("profile"))

@app.route('/set-unavaiable/<int:driver_id>', methods=['GET', 'POST'])
def set_driver_unavailable(driver_id, reason, end_date):
    #get driver
    driver = Driver.query.get(driver_id)

    today = date.today()

    #for jorunesy in period, cancel them
    journeys = Journey.query.filter(Journey.date > today, Journey.date <= end_date, Journey.driver_id==driver_id)

    if journeys:
        for j in journeys:
            cancel_journey(j.id)
        
    #set availability and end date in driver
    driver.driver_status = reason
    driver.unavailable_end_date = end_date

    db.session.commit()

    flash("Set driver status successfully", "success")

#view profile and ALL options
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    car = None
    form = ChangeAvailabilityForm()
    form_p = ChangePasswordForm()

    if form_p.validate_on_submit() and ("submit_form_p" in request.form):
        app.logger.info("password checking")
        old_password = form_p.old_password.data
        new_password = form_p.new_password.data

        change_password(old_password, new_password, current_user.id)
        return redirect(url_for("profile"))

    if form.validate_on_submit() and "submit_form_a" in request.form:
        driver_id = current_user.driver_id
        reason = form.availability_status.data
        end_date = form.end_date.data

        set_driver_unavailable(driver_id, reason, end_date)

        return redirect(url_for("profile"))

    # quering the drivers table, looking at rows where the user id matches the logged in user's id
    driver = Driver.query.filter_by(user_id=current_user.id).first()

    #getting the drivers car
    if driver:
        car = Car.query.filter_by(driver_id=driver.driver_id).first()

    # getting all the journeys the user has booked and complete
    user_bookings = Booking.query.filter_by(user_id=current_user.id).join(Journey).all()

    driver_rides = Journey.query.filter(
        Journey.driver_id == current_user.driver_id,
        Journey.journey_status == JourneyStatusEnum.COMPLETE,  
    ).order_by(desc(Journey.date)).all()

    driver_rides=format_journeys(driver_rides)

    # rides the current user has booked on to (bookings)
    user_bookings = Booking.query.filter(
    Booking.user_id == current_user.id,
    Booking.booking_status == BookingStatusEnum.COMPLETE
    ).all()

    #format
    user_bookings = format_bookings(user_bookings)

    return render_template('profile.html', title='Profile', driver=driver, car=car, driver_rides=driver_rides, user_bookings=user_bookings, form=form, form_p=form_p)

#access profile user information
@app.route('/accessprofile', methods=['GET','POST'])
@login_required
def accessprofile():
    form = AccessProfileForm()
    if form.validate_on_submit():
        if bcrypt.check_password_hash(current_user.password, form.password.data):
            session['profile_verified'] = True
            return(redirect(url_for('editprofile')))
    return render_template('accessprofile.html', title = 'Access your Skrrrt! Profile', form = form)

#edit profile
@app.route('/editprofile', methods=['GET','POST'])
@login_required
def editprofile():
    if not session.get('profile_verified'):
        return redirect(url_for('accessprofile'))
    
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name=form.last_name.data
        current_user.email=form.email.data
        current_user.phone_number=form.phone_number.data
        db.session.commit()
        flash("Profile updated successfully", 'success')
        session.pop('profile_verified', None)
        return(redirect(url_for('profile')))
    return render_template('editprofile.html', title = 'Edit Skrrrt! Profile', form = form)

#delete account
@app.route('/deleteaccount', methods=['GET','POST'])
@login_required
def deleteaccount():
    form = DeleteAccountForm()
    
    if form.validate_on_submit():
        if bcrypt.check_password_hash(current_user.password, form.password.data):
            db.session.delete(current_user)
            db.session.commit()
            logout_user()
            flash('Account has been deleted succesffully','success')
            return redirect(url_for('login'))
        else:
            flash('Incorrect password try again','danger')
    return render_template('deleteaccount.html', title = 'Delete Account', form=form)

#change password
def change_password(old, new, user_id):
    app.logger.info("changing password")
    user = User.query.get(user_id)
    try:

        #check if old password matches stored
        if not bcrypt.check_password_hash(user.password, old):
            flash("Old password is incorrect.", "danger")
            return redirect(url_for("profile"))

        #change password
        user.password = bcrypt.generate_password_hash(new)

        db.session.commit()
        flash("Password updated successfully!", "success")

    except:
        flash("Error when updating password", "danger")

    return redirect(url_for("profile"))

#send request to reset password
@app.route("/reset_password_request", methods=['GET','POST'])
def reset_password_request():
    if current_user.is_authenticated:
        flash('already logged in to account', 'danger')
        return redirect(url_for('login'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user_select = select(User).where(User.email == form.email.data)
        user = db.session.scalar(user_select)
        
        if user:
            send_request_password_email(user)
            
            flash("Instructions have been sent to your email address, if it exists in our system")
            
            return redirect(url_for('login'))
    return render_template("resetPasswordRequest.html", title ="Reset Password", form = form)
    
#send emaail
def send_request_password_email(user):
    reset_password_url = url_for(
        "reset_password",
        token=user.generate_reset_password_token(),
        user_id=user.id,
        _external=True
        )
        
    email_Body = render_template("resetPasswordEmailContent.html", reset_password_url=reset_password_url)
    
    message = EmailMessage(
        subject="Reset your password",
        body=email_Body,
        to=[user.email]
        )
    message.content_subtype = "html"
    
    message.send()

#changes the password with token validation   
@app.route("/reset_password/<token>/<int:user_id>", methods=["GET", "POST"])
def reset_password(token, user_id):
    if current_user.is_authenticated:
        return redirect(url_for("login"))

    user = User.validate_reset_password_token(token, user_id)
    if not user:
        flash('error occurred try again later', 'danger')
        return redirect(url_for('reset_password_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        if user:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user.password = hashed_password
            db.session.commit()
            flash('Password successfully updated', 'success')
            return redirect(url_for('login'))
        else:
            flash('Failed to updated password please try again', 'danger')
            return redirect(url_for(reset_password_request))
    return render_template(
        "resetPasswordForm.html", title="Reset Password", form=form
    )
    
#DRIVER ----------------------------------------------------------------------------------------
   
# register to be a driver
@app.route('/driver-registration', methods=['GET', 'POST'])
@login_required
def register_driver():
    form = DriverRegistrationForm()

    existing_driver = Driver.query.filter_by(user_id=current_user.id).first()

    if existing_driver:
        return redirect(url_for('make_journey'))

    error_message = "You haven't registered to drive"

    try:
        if form.validate_on_submit():

            # validation for the driving licence
            if not re.search(r'^[A-Z9]{5}\d[0156]\d([0][1-9]|[12]\d|3[01])\d[A-Z9]{2}\d[A-Z]{2}$', form.liscence_num.data):
                error_message = "This is not a valid UK Licence Format"
                return render_template('driversignup.html', title="Register to drive!", form=form, error_message=error_message)

            driver = Driver(user_id=int(current_user.id), num_trips=0, license_num=form.liscence_num.data,
                            driver_status="ACTIVE", driver_rating=0.0, num_ratings=0)

            db.session.add(driver)
            db.session.flush()
            app.logger.info("driver created")

            # check licence plate is of the correct format
            if not re.search(r'^([A-Z]{3}\s?(\d{3}|\d{2}|d{1})\s?[A-Z])|([A-Z]\s?(\d{3}|\d{2}|\d{1})\s?[A-Z]{3})|(([A-HK-PRSVWY][A-HJ-PR-Y])\s?([0][2-9]|[1-9][0-9])\s?[A-HJ-PR-Z]{3})$', form.reg_plate.data):
                error_message = "This is not a valid UK Car Registration Plate"
                return render_template('driversignup.html', title="Register to drive!", form=form, error_message=error_message)

            car = Car(car_nickname=form.car_nickname.data, reg_plate=form.reg_plate.data, make=form.make.data,
                      model=form.model.data,
                      colour=form.colour.data, max_seats=int(form.max_seats.data), driver_id=int(driver.driver_id))
            db.session.add(car)
            db.session.commit()

            # ✅ on success, redirect
            return redirect(url_for('make_journey'))

    except Exception as e:
        app.logger.error(f"Error in driver registration: {e}")
        error_message = "Error in registration."

    # Render with or without errors
    return render_template('driversignup.html', title="Register to drive!", form=form, error_message=error_message)



#driver makes a journey

# to add a second car after signing up to be a driver with the first car
@app.route('/add-a-car', methods=['GET', 'POST'])
@login_required
def newcar():
    form = CarRegistrationForm()
    # driverslisencenumber = Driver.query.get(driver_id=current_user.driver_id)
    # form.liscence_number = driverslisencenumber
    driver = Driver.query.filter_by(user_id=current_user.id).first()


    try:
        if form.validate_on_submit():
            if (not re.search(
                    r'^([A-Z]{3}\s?(\d{3}|\d{2}|d{1})\s?[A-Z])|([A-Z]\s?(\d{3}|\d{2}|\d{1})\s?[A-Z]{3})|(([A-HK-PRSVWY][A-HJ-PR-Y])\s?([0][2-9]|[1-9][0-9])\s?[A-HJ-PR-Z]{3})$',
                    form.reg_plate.data)):
                flash("This is not a valid UK Car Registration Plate", "danger!")
                return render_template('newcar.html', title="New Car", form=form)

            car = Car(car_nickname=form.car_nickname.data, reg_plate=form.reg_plate.data, make=form.make.data,
                      model=form.model.data, colour=form.colour.data ,max_seats=form.max_seats.data,
                      driver_id=driver.driver_id)
            db.session.add(car)
            db.session.commit()
            flash("New Car Added", "success")

            return redirect(url_for('profile'))
    except:
        flash("Registration Plate already exists!", "danger")

    return render_template('newcar.html', title="New Car", form=form)

#used when user wants to make a ride. if they are not a driver they get redirected to sign up form
@app.route('/baseride-nav', methods=['GET', 'POST'])
@login_required
def baseride_nav():
    
    driver = Driver.query.filter_by(user_id=current_user.id).first()

    if driver is None:
            flash("You are not registered as a driver", "warning")
            return redirect(url_for("register_driver"))
    
    journey = Journey.query.filter_by(driver_id=driver.driver_id).first()

    if journey is None:
        return redirect(url_for('make_journey'))

    return render_template('baseride.html', title="Make a Journey")

# when adding a new location to the journey form to dynamically add them to the dropdown
# make sure that the CSRF token is added to the form, must be done manually
@app.route('/add_location', methods=['POST'])
@login_required
def add_location():
    csrf_token = request.headers.get("X-CSRFToken")  # Extract CSRF token from headers

    # Validate CSRF token
    try:
        validate_csrf(csrf_token)
    except Exception as e:
        return jsonify({"success": False, "error": "Invalid or missing CSRF token"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No JSON data received"}), 400

    # Extract data
    nickname = data.get("nickname")
    addressLine1 = data.get("addressLine1")
    country = data.get("country")
    city = data.get("city")
    postcode = data.get("postcode")

    # Validate input
    if not all([nickname, addressLine1, country, city, postcode]):
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    existing_location = Location.query.filter_by(
        driver_id=current_user.driver_id,
        nickname=nickname,
        address_line_1=addressLine1,
        postcode=postcode,
        city=city,
        country=country
    ).first()

    if existing_location:
        return jsonify({"success": False, "error": "Location already exists!"}), 400

    # then save the new added location to the db
    new_location = Location(
        driver_id=current_user.driver_id,
        nickname=nickname,
        address_line_1=addressLine1,
        postcode=postcode,
        city=city,
        country=country
    )

    db.session.add(new_location)
    db.session.commit()

    return jsonify({"success": True, "id": new_location.id, "nickname": new_location.nickname})

@app.route('/get-location-details/<location_id>')
def get_location_details(location_id):
    location = Location.query.get(location_id)

    #change to dictionary because of jsonify error
    location = {
        "id": location.id,
        "nickname": location.nickname,
        "addressLine1": location.address_line_1,
        "city": location.city,
        "postcode": location.postcode,
        "country": location.country,
    }
    
    return jsonify(location)

#using json and script.js
@app.route('/edit_location/<location_id>/<journey_id>', methods=['PUT', 'GET', 'POST'])
def edit_location(location_id, journey_id):

    data = request.json
    location = Location.query.get(location_id)

    app.logger.info("Editing location")
    if location:
        try:
            location.nickname = data.get('nickname')
            location.address_line_1 = data.get('addressLine1')
            location.city = data.get('city')
            location.postcode = data.get('postcode')
            location.country = data.get('country')


            db.session.commit()
            app.logger.info("Success")
            flash("Location Edited Successfully", "success")

        except:
            db.session.rollback()
            app.logger.info("error")
            flash("Error when editing location details.", "danger")
            return "", 500

            #notify passengers
            #get all bookings on the hourney
            bookings = Booking.query.filter_by(journey_id=journey_id).all()
            #get driver details and what user they are
            journey = Journey.query.get(journey_id)
            driver=Driver.query.get(journey.driver_id)
            driver_user = User.query.get(driver.user_id)

            app.logger.info("got driver details")

            if bookings:
                for b in bookings:
                    passenger = User.query.get(journey.user_id)

                    #send email to passenger
                    message = EmailMessage(
                    subject="Booking Details Changed",
                    body="Your driver has changed the journey,\n From " + pickup_location +  ", To " + dropoff_location + " on " + j.date + "@" + j.time + "\nIf you dont agree with this change, please contact your driver at " + driver_user.email + "\n Thank you,\n - The Team @ Skrrt",
                    to=[passenger.email]
                    )
                app.logger.info("notified passengers")
                flash("Passengers notfied of the change.", "Success")

            app.logger.info("done")
            return "", 204

    return "", 204


# pass the locations into the page template
@app.route('/deletelocation', methods=['GET', 'POST'])
def delete_saved_location():
    locations = Location.query.filter_by(driver_id=current_user.driver_id).all()

    valid_locations = []

    for location in locations:
        journeys_at_location = Journey.query.filter((Journey.pickup_location == location.id) | (Journey.dropoff_location == location.id)).all()

        if Booking.query.filter(Booking.journey_id.in_([j.id for j in journeys_at_location])).first() is not None:
            valid_locations.append(location)

    return render_template("savedLocations.html", title="Save Location", locations=valid_locations)

# delete the location passing the intended location id
@app.route("/delete/<int:location_id>", methods=["POST"])
def delete_location(location_id):

    # checking if the csrf token is carried over
    csrf_token = request.headers.get("X-CSRFToken")

    # validate the token
    try:
        validate_csrf(csrf_token)
    except Exception as e:
        return jsonify({"success": False, "error": "Invalid or missing CSRF token"}), 403

    location = Location.query.get(location_id)
    if location:
        db.session.delete(location)
        db.session.commit()
        return jsonify({"message": "Location deleted successfully"}), 200

    return jsonify({"error": "Location not found"}), 404

#driver makes a journey
@app.route('/makejourney', methods=['GET', 'POST'])
@login_required
def make_journey():
    # later we can try and find a way to ensure that new locations are unique not too sure how to rn
    form = JourneyForm()
    form.journey_status.data = JourneyStatusEnum.WAITING.name

    location_dropdown = False
    selected_value = None

    current_driver = current_user.driver_id
    cars = Car.query.filter_by(driver_id=current_driver).all()

    # checking if there are previous_locations
    previous_locations = Location.query.filter_by(driver_id=current_driver).all()

    # make sure that the choices can be appended to something
    form.previous_pickup_location.choices = []
    form.previous_dropoff_location.choices = []

    if previous_locations:
        form.previous_pickup_location.choices = [(location.id, location.nickname) for location in previous_locations]
        form.previous_dropoff_location.choices = [(location.id, location.nickname) for location in previous_locations]
    else:
        form.previous_pickup_location.choices.append((None, "No Locations Saved Yet"))
        form.previous_dropoff_location.choices.append((None, "No Locations Saved Yet"))


    form.reg_plate.choices = [(car.reg_plate, car.car_nickname) for car in cars]



    if form.validate_on_submit():

        if (not form.previous_pickup_location.data or not form.previous_dropoff_location.data):
            flash("You must select or create a new location for pickup and/or drop off", "danger")
            return render_template('newride.html', title="New Journey", form=form)

        # check if previous_pickup and dropoff are the same
        if (form.previous_pickup_location.data == form.previous_dropoff_location.data):
            flash("Start and end location cannot be the same", "danger")
            return render_template('newride.html', title="New Journey", form=form)

        pickup_location = form.previous_pickup_location.data
        dropoff_location = form.previous_dropoff_location.data
        journey_type = form.journey_type.data
        journey_date = form.date.data
        journey_time = form.time.data

        selected_datetime = datetime.combine(journey_date, journey_time)
        min_allowed_datetime = datetime.now() + timedelta(hours=1)  # One hour from now

        if selected_datetime < min_allowed_datetime:
            flash("Journey must be at least one hour in the future!", "danger")
            return render_template('newride.html', form=form, previous_locations=previous_locations)

        # need to batch add bookings based off of form input for the daily and weekly buttons
        # repeat the booking for times into the future (so month in advance) might change this

        journeys_to_add = []

        if journey_type == "DAILY":
            for i in range(7):
                new_date = journey_date + timedelta(days=i)
                journeys_to_add.append(Journey(
                    date=new_date,
                    time=journey_time,
                    pickup_location=pickup_location,
                    dropoff_location=dropoff_location,
                    journey_status=JourneyStatusEnum.WAITING.value,
                    price_per_person=form.price_per_person.data,
                    driver_id=current_driver,
                    journey_type=journey_type,
                    reg_plate=form.reg_plate.data,
                    num_confirmed=0
                ))

        elif journey_type == "WEEKLY":
            # let weekly journeys be valid for a month: maybe show a message to user
            for i in range(4):
                new_date = journey_date + timedelta(weeks=i)
                journeys_to_add.append(Journey(
                    date=new_date,
                    time=journey_time,
                    pickup_location=pickup_location,
                    dropoff_location=dropoff_location,
                    journey_status=JourneyStatusEnum.WAITING.value,
                    price_per_person=form.price_per_person.data,
                    driver_id=current_driver,
                    journey_type=journey_type,
                    reg_plate=form.reg_plate.data,
                    num_confirmed=0
                ))

        else:
            # Create a single journey for "ONE-TIME"
            journeys_to_add.append(Journey(
                date=journey_date,
                time=journey_time,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                journey_status=JourneyStatusEnum.WAITING.value,
                price_per_person=form.price_per_person.data,
                driver_id=current_driver,
                journey_type=journey_type,
                reg_plate=form.reg_plate.data,
                num_confirmed=0
            ))

        # add all journeys to the database in batches dependent on user input
        db.session.add_all(journeys_to_add)
        db.session.commit()

        flash('Journey Created!', 'success')
        return redirect(url_for('upcomingbookings'))

    return render_template('newride.html', title="New Journey", form=form)

#see user bookings, drivers upcomining rides and pending requests to join a ride
@app.route('/your-bookings', methods=['GET', 'POST'])
@login_required
def upcomingbookings():
    form = ConfigureCostForm()
    todays_datetime = datetime.now()

    if request.method == 'POST':
        return reconfigure_cost(form.booking_id.data, form.cost.data)

    # upcoming rides the current user has booked on to (bookings)
    user_bookings = Booking.query.filter(
    Booking.user_id == current_user.id,
    Booking.booking_status != BookingStatusEnum.COMPLETE
    ).all()

    #format
    user_bookings = format_bookings(user_bookings)

    pending_bookings = []
    driver_rides = []
    #Google maps API information
    pickup_location = {'lat': 53.8008, 'lng': -1.5491}  # Coordinates of Leeds
    dropoff_location = {'lat': 53.4794, 'lng': -2.2453} # Coordinates of Manchester

    
    driver = Driver.query.filter_by(user_id=current_user.id).first()

    if current_user.is_driver:
        # fetch journeys owned by the driver
        driver_journeys = Journey.query.filter( Journey.driver_id == current_user.driver_id).all()
        driver_journey_ids = [j.id for j in driver_journeys]

        #Journey.journey_status != JourneyStatusEnum.COMPLETE.name
        driver_rides = Journey.query.filter(
            Journey.driver_id == current_user.driver_id,
            Journey.journey_status != JourneyStatusEnum.COMPLETE,  
        ).all()

        driver_rides = format_journeys(driver_rides)
  
        # fetch bookings where the journey belongs to the driver (people wanting to book onto the journey)
        pending_bookings = Booking.query.join(Journey).filter(
            Journey.driver_id == current_user.driver_id,
            Booking.booking_status == BookingStatusEnum.PENDING
        ).all()

        pending_bookings = format_bookings(pending_bookings)


    return render_template('bookings.html', 
                            title='Your Bookings', 
                            user_bookings=user_bookings, #booked by user
                            driver=driver, 
                            pending_bookings=pending_bookings,  #invites
                            driver_rides=driver_rides, #driver journeus
                            form=form,
                            todays_datetime=todays_datetime,
                            today_in15mins = todays_datetime + timedelta(minutes = 15),
                            today_in2hours = todays_datetime + timedelta(hours=2),
                            pickup_location=pickup_location,
                            dropoff_location=dropoff_location)

GOOGLE_MAPS_API_KEY = "AIzaSyDgGXaoIUnKbcco5UWyPQjDkxnpiS1gWrY"

@app.route('/get_route', methods=['GET'])
def get_route():
    pickup = request.args.get("pickup_location", "53.8008,-1.5491")  # Default: Leeds
    dropoff = request.args.get("dropoff_location", "53.4794,-2.2453")  # Default: Manchester

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.polyline"  # Limits response size
    }

    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": float(pickup.split(",")[0]),
                    "longitude": float(pickup.split(",")[1])
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": float(dropoff.split(",")[0]),
                    "longitude": float(dropoff.split(",")[1])
                }
            }
        },
        "travelMode": "DRIVE"
    }

    response = requests.post(url, json=body, headers=headers)
    data = response.json()

    if "routes" in data and len(data["routes"]) > 0:
        polyline = data["routes"][0]["polyline"]["encodedPolyline"]
        return jsonify({"polyline": polyline})

    return jsonify({"error": "No routes found"}), 400




#FIND AND BOOK JOURNEY ----------------------------------------------------------------------------------------

#base book
@app.route('/bookaride', methods=['GET'])
@login_required
def book():
    return render_template('book.html', title='Book A Ride')

#find available journeys to book
@app.route('/available-journeys', methods=['GET', 'POST'])
@login_required
def availableJourneys():
    form = FilterJourneysForm()
    form_cc = ConfigureCostForm()

    # Fetch all journeys that are "WAITING" && still have seats available && have more than 30 minutes before they depart
    # and that is not a journey beloning to the driver
    user_bookings = Booking.query.filter_by(user_id=current_user.id).all()

    user_bookings = Booking.query.filter(
    and_(Booking.user_id == current_user.id, Booking.booking_status != BookingStatusEnum.CANCELLED )).all()

    user_booked_journey_ids = [b.journey_id for b in user_bookings]

    journeys = Journey.query.join(Car, Journey.reg_plate == Car.reg_plate).filter(
        and_(
        Journey.journey_status == JourneyStatusEnum.WAITING,
        Journey.num_confirmed < Car.max_seats,
        Journey.driver_id != current_user.driver_id,  #drriver cant see own journey
        or_(
            and_(Journey.date == date.today(), Journey.time > datetime.now().time()), #later today or any time in the future
            Journey.date > date.today()
        ),
        ~Journey.id.in_(user_booked_journey_ids)  #exclude already booked journeys that havent been cancelled
    )
    ).order_by(Journey.date, Journey.time)


    #filter
    if request.method == "GET":
        journeys = journeys.all()
        app.logger.info(journeys)
        journey_details = format_journeys(journeys)
        return render_template('availablejourneys.html', journeys=journey_details, title = "Available Bookings", form=form, form_cc=form_cc)
    else:
        app.logger.info("Filtering Journeys")

        #fill variables if form element was filled in
        input_date_str = request.form.get('date')
        input_time_str = request.form.get('time')
        pickup_postcode = request.form.get('pickup_postcode')
        dropoff_postcode = request.form.get('dropoff_postcode')
        type = request.form.get('j_type')

        sort_by = request.form.get('sort_by', 'time')  # Default sorting by time

        #filter by date
        if input_date_str:
            input_date = datetime.strptime(input_date_str, '%Y-%m-%d').date()  # Convert date input

            #get journeys 10 minutes before or after specified time
            journeys = journeys.filter(
                (Journey.date == input_date)
            )

        #filter by time
        if input_time_str:
            input_time = datetime.strptime(input_time_str, '%H:%M') # Convert time input
            ten_minutes_before = (input_time - timedelta(minutes=10)).time()
            ten_minutes_after = (input_time + timedelta(minutes=10)).time()

            print(ten_minutes_after)

            for j in journeys:
                print(j.time)

            #get journeys 10 minutes before or after specified time
            journeys = journeys.filter(
                (Journey.time >= ten_minutes_before),
                (Journey.time <= ten_minutes_after),
            )

        #filter by postcode

        # for UK postcodes last three digits always inward code so using outward

        if pickup_postcode:
            pickup_postcode = pickup_postcode.strip().upper()
            outward_pickup = len(pickup_postcode) - 3
            journeys = journeys.filter(Location.postcode.ilike(f"%{pickup_postcode[:outward_pickup]}%"))

        if dropoff_postcode:
            dropoff_postcode = dropoff_postcode.strip().upper()
            outward_dropoff = len(dropoff_postcode) - 3
            journeys = journeys.filter(Location.postcode.ilike(f"%{dropoff_postcode[:outward_dropoff]}%"))

        # filter by commute or one time
        if type != "ALL":
            journeys = journeys.filter(Journey.journey_type == type)

        #sort by rating or datetime
        if sort_by == 'rating':
            journeys = journeys.join(Driver).order_by(Journey.driver_rating.desc())  # Sort by rating descending
        else:
            journeys = journeys.filter().order_by(Journey.date, Journey.time)

    #execute query
    journeys = journeys.all()
    journey_details = format_journeys(journeys)

    if form_cc.validate_on_submit() and "submit_form_cc" in request.form:
        return redirect(url_for('card_select',journey_id=form_cc.journey_id.data, price=form_cc.cost.data))

    return render_template('availablejourneys.html', title = "Available Journeys to Book", journeys=journey_details, input_date=input_date_str, input_time=input_time_str, pickup=pickup_postcode, dropoff=dropoff_postcode, form=form, form_cc=form_cc)

#user id passed as parameter
def format_user_name(id):
    person = User.query.get(id)
    driver_name = person.first_name + " " + person.last_name
    return driver_name

#pass journeyid as parameter
def format_location_name(id):
    location = Location.query.get(id)
    location_string = location.address_line_1 + ", " + location.city + ", " + location.postcode
    return location_string

def format_location_nickname(id):
    location = Location.query.get(id)
    location_string = location.nickname 
    return location_string


#format bookings
def format_bookings(bookings):
    booking_details = []
    
    for b in bookings:
 
        journey = [0]
        #get journey corresponding with booking
        journey[0] = Journey.query.get(b.journey_id)
        #format the single journey
        j_details = format_journeys(journey)

        #get passenger name
        user = User.query.get(b.user_id)
        user_name = user.first_name + " " + user.last_name

        #concatinate with extra booking details
        b_details = {
            "journey_id" : b.journey_id,
            "booking_status" : b.booking_status.value,

            "price" : f"{b.price:.2f}", #user configured price
            "payment_status" : b.payment_status.value,

            #passenger name
            "user_name" : user_name,
            "user_email" : user.email,
            "user_phone_num": user.phone_number,

            "reviewed" : b.reviewed
        }

        # ** unpakcs dictionary details and merge them
        booked_journey_details = {
            #as we only formatted one journey at a time, there is only 1 in the list. so we access it at element [0]
            **j_details[0],
            **b_details,
            # replace ID (filled with journey id) with booking id as we are dealing with specifically bookings
            "id" : b.id
        }
        # Reference : https://www.geeksforgeeks.org/python-unpack-dictionary/#merging-dictionaries-using-

        booking_details.append(booked_journey_details)

    return booking_details

#formats journeys so that information can be displayed instead of ids as this is not user friendly
def format_journeys(journeys):
    journey_details = []
    
    for j in journeys:
 
        driver = Driver.query.get(j.driver_id)
        driver_name = format_user_name(driver.user_id)
        driver_email = User.query.get(driver.user_id).email

        pickup_location = format_location_name(j.pickup_location)

        dropoff_location = format_location_name(j.dropoff_location)

        car = Car.query.get(j.car.reg_plate)

        details = {
            "id": j.id,
            "journey_status": j.journey_status.value,
        
            "date": j.date.strftime("%A %d %B %Y"), #format from numbers to words
            "time": j.time.strftime("%I:%M %p").lstrip("0"), #format from 24hr clock to 12 hr clock with AM/PM
            "datetime": datetime.combine(j.date, j.time),

            "price_per_person": f"{j.price_per_person:.2f}",

            "available_seats": j.car.max_seats - j.num_confirmed,
            "num_confirmed": j.num_confirmed,
            "max_seats": j.car.max_seats,

            "pickup_location": pickup_location, 
            "pickup_id": j.pickup_location,
            "pickup_nickname": format_location_nickname(j.pickup_location),
            "dropoff_location": dropoff_location,
            "dropoff_id": j.dropoff_location,
            "dropoff_nickname": format_location_nickname(j.dropoff_location),

            "driver_name": driver_name,
            "driver_email": driver_email,

            "car": car,
        }
        journey_details.append(details)

    return journey_details

#used to configure cost after a joruney has already been booked and it is pending
@app.route('/configure-cost/<int:journey_id>/<float:price>', methods=['POST'])
def reconfigure_cost(booking_id, price):
    try:
        app.logger.info(booking_id)
        app.logger.info("Changing price")
        booking = Booking.query.get(booking_id)
        app.logger.info("got booking")
        booking.price = price
        app.logger.info("got price")
        booking.booking_status = BookingStatusEnum.PENDING
        db.session.commit()
        flash("Price successfully configured.", "success")
    
        if checkifdiscountapplys(booking.user_id) == True:
            discount = Discount.query.get(1)
            flash("As a loyal customer, you qualify for a " + (discount.discount_percentage * 100) + " discount. It will be applied once the driver accepts your ride.", "success")

    except:
        db.session.rollback()
        flash("Error when configuring cost", "danger")
    
    return redirect(url_for('upcomingbookings'))

#every hour check if 2 hours after a journeys time has passed. if yes then mark it as complete
#optional parameter for code reuse in running webiste instead of scheduled script
def check_journey_datetime(journey=None):
    
    app.logger.info(f"Running check at {datetime.now()}")
    
    #because it is running in a different thread we need to import the conext
    with app.app_context():

        now = datetime.now()
        
        #journey is passed in from teh running application. We will just be setting the status of one journey.
        #if its not null then check every journey which is not complete
        if journey == None:
            journeys = Journey.query.filter(Journey.journey_status != "COMPLETE",  Journey.journey_status != JourneyStatusEnum.INACTIVE, Journey.journey_status != JourneyStatusEnum.CANCELLED ).all()
        else:
            journeys = [journey]

        filtered_journeys = []
        for journey in journeys:
            journey_datetime = datetime.combine(journey.date, journey.time)

            #if journey is from a previous DAY or the journey is today and 30 minutes has passed... then we will check its status
            if journey.date < now.date() or (journey.date == now.date() and journey_datetime < (now - timedelta(minutes=30))):
                filtered_journeys.append(journey)

        #for every journey check its status and change it appropiatley
        for j in filtered_journeys:
            app.logger.info(f"Journey {j.id} has passed, marking it as complete.")
    
            try:
                #set journey status to complete
                j.journey_status = JourneyStatusEnum.COMPLETE.value
                bookings_on_journey = Booking.query.filter_by(journey_id=j.id).all()

                #set booking status for any bookings on the journey
                for b in bookings_on_journey:

                    #if booking is accepted then complete booking
                    if b.booking_status == BookingStatusEnum.ACCEPTED:
                        b.booking_status = BookingStatusEnum.COMPLETE.value
                    #if booking is pending then set it to declined
                    elif b.booking_status == BookingStatusEnum.PENDING :  
                        b.booking_status = BookingStatusEnum.DECLINED.value
                    
                db.session.commit()
            except:
                db.session.rollback()
        app.logger.info("CHECK COMPLETE")

#scheduler repeats every 10 minutes
schedule.every(10).minutes.do(check_journey_datetime)

#mark ride as complete
@app.route('/ride-complete/<int:journey_id>', methods=['GET', 'POST'])
@login_required
def mark_as_complete(journey_id):
    journey = Journey.query.get(journey_id)
    
    check_journey_datetime(journey)

    return redirect(url_for("upcomingbookings"))

# user books onto a journey and it is now waiting for confirmation from the driver
@app.route('/book-journey/<int:journey_id>/<float:price>', methods=['POST', 'GET'])
@login_required
def book_journey(journey_id, price):
    journey = Journey.query.get_or_404(journey_id)
    payment_method_id = session.get('pending_payment_method_id')

    if not journey:
        flash("This journey does not exist.", "danger")
        return redirect(url_for('availableJourneys'))

    car = Car.query.filter_by(reg_plate=journey.reg_plate).first()

    if not car:
        flash("The car for this journey was not found.", "danger")
        return redirect(url_for('availableJourneys'))

    #make sure price is greater than 0 and not bigger than asked price
    if price > journey.price_per_person:
        flash("You cant pay more than what the driver is asking for. Choose a new price", "warning")

    existing_booking = Booking.query.filter_by(user_id=current_user.id, journey_id=journey.id).first()

    if existing_booking and existing_booking.booking_status != BookingStatusEnum.CANCELLED:
        flash("You have already booked this journey.", "warning")
        return redirect(url_for('availableJourneys'))


    # Check if there are seats available
    if journey.num_confirmed >= car.max_seats:
        flash("Sorry, this journey is fully booked!", "danger")
        return redirect(url_for('availableJourneys'))

    payment_method = PaymentMethod.query.get(payment_method_id)
    try:
        # Create PaymentIntent
        amount = int(round(price*100)) # Convert to int in pence for stripe
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='gbp',
            payment_method=payment_method.payment_method_id,
            customer=current_user.stripe_customer_id,
            confirm=False,
            automatic_payment_methods={
                "enabled": True,
                "allow_redirects": "never"
                }
        )

        # Create a new booking
        new_booking = Booking(
            user_id=current_user.id,
            journey_id=journey.id,
            payment_status=PaymentStatusEnum.PENDING,
            payment_method_id=payment_method_id,
            payment_intent_id=payment_intent.id,
            price=price,
            booking_status=BookingStatusEnum.PENDING

        )

        db.session.add(new_booking)
        db.session.commit()

    except stripe.error.StripeError as e:
        flash(f"Stripe Error: {str(e)}", "danger")
        return redirect(url_for('availableJourneys'))

    flash("Booking request sent! Waiting for driver's approval.", "success")

    if checkifdiscountapplys(current_user.id) == True:
        discount = Discount.query.get(1)
        flash("As a loyal customer, you qualify for a " + (discount.discount_percentage * 100) + " discount. It will be applied once the driver accepts your ride.", "success")
 
    # Update number of confirmed passengers
    journey.num_confirmed += 1
    if journey.num_confirmed >= car.max_seats:
        journey.journey_status = JourneyStatusEnum.INACTIVE  # Mark journey as full

    return redirect(url_for('availableJourneys'))

# driver can accept/decline routes for the bookings
@app.route('/accept-booking/<int:booking_id>', methods=['POST'])
@login_required
def accept_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    journey = Journey.query.get(booking.journey_id)
    driver = Driver.query.filter_by(user_id=current_user.id).first()

    if not journey or journey.driver_id != driver.driver_id:
        flash("You are not authorized to accept this booking!", "danger")
        return redirect(url_for('upcomingbookings'))

    #if user qualifies for discount then apply it
    if checkifdiscountapplys(booking.user_id) == True:
        discount = Discount.query.get(1)
        price = price - (price * discount.discount_percentage)

    try:
        payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

        #Check if payment intent has expired
        if payment_intent.status == "canceled" and payment_intent.cancellation_reason == "payment_intent_expired":
            #Renew payment
            renew_payment(booking.id)
            booking = Booking.query.get_or_404(booking_id)

        payment_intent = stripe.PaymentIntent.confirm(booking.payment_intent_id)

        if payment_intent.status == "succeeded":
            booking.booking_status = BookingStatusEnum.ACCEPTED
            booking.payment_status = PaymentStatusEnum.COMPLETE

            db.session.commit()
            flash("Payment Successful. Booking Accepted", "success")

            #flush price
            db.session.flush()

            send_booking_confirmation_email(booking.user_id, booking_id)
    
            journey.num_confirmed += 1
            db.session.commit()
            flash("Booking accepted!", "success")

        else:
            flash("Payment could not be completed", "danger")

    except:
        flash("Error processing Payment")
        db.session.rollback()

    return redirect(url_for('upcomingbookings'))

#decline
@app.route('/decline-booking/<int:booking_id>', methods=['POST'])
@login_required
def decline_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    journey = Journey.query.get(booking.journey_id)
    driver = Driver.query.filter_by(user_id=current_user.id).first()

    if not journey or journey.driver_id != driver.driver_id:
        flash("You are not authorised to decline this booking!", "danger")
        return redirect(url_for('upcomingbookings'))
   
    try:
        booking.booking_status = BookingStatusEnum.DECLINED
        db.session.commit()
        flash("Booking declined.", "warning")
    except: 
        db.session.rollback()
        flash("Error when declining booking.", "warning")

    return redirect(url_for('upcomingbookings'))

@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    journey = Journey.query.get(booking.journey_id)
    
    journey_datetime = datetime.combine(journey.date, journey.time)
    current_datetime = datetime.now()
    
    #only remove people if their booking waa confirmed
    if booking.booking_status == BookingStatusEnum.CONFIRMED:
        journey.num_confirmed -= 1

    if journey.journey_status == JourneyStatusEnum.FULL:
        journey.journey_status == JourneyStatusEnum.WAITING

    if booking.booking_status == "ACCEPTED":
        if  journey_datetime - timedelta(minutes=15) >  current_datetime:
            refund(booking.id, late=False)
            flash("booking has been succesfully cancelled for free", 'success')
        else:
            refund(booking.id, late=True)
            flash("Booking cancelled with late notice fee", 'warning')
    else:
        flash("Booking cancelled")
    booking.booking_status = BookingStatusEnum.CANCELLED
    db.session.commit()
    return redirect(url_for('upcomingbookings'))

@app.route('/cancel-journey/<int:journey_id>', methods=['POST'])
@login_required
def cancel_journey(journey_id):

    try:
        #get journey
        journey = Journey.query.get(journey_id)

        #get journey date and current date
        journey_datetime = datetime.combine(journey.date, journey.time)
        current_datetime = datetime.now()

        #if more than 15 mins before ride then 
        if journey_datetime - timedelta(minutes=15) >  current_datetime:

            bookings_on_journey = Booking.query.filter_by(journey_id=journey.id).all()
            app.logger.info(bookings_on_journey)

            #cancel all bookings on journey
            for b in bookings_on_journey:
                refund(b.id, late=False)
                cancel_booking(b.id)

            #cancel journey
            app.logger.info(journey)
            journey.journey_status = JourneyStatusEnum.CANCELLED
            app.logger.info("Journey Cancelled")

            pickup_location = format_location_name(j.pickup_location)
            dropoff_location = format_location_name(j.dropoff_location)
            dropoff_nickname = format_location_nickname(j.dropoff_location)

            app.logger.info("Got location name")
            #email passenger
            passenger = User.query.get(journey.user_id)
            #send email to passenger
            message = EmailMessage(
            subject="Booking Cancellation - Journey to" + "dropoff_nickname",
            body="Your driver has cancelled the journey,\n From " + pickup_location +  ", To " + dropoff_location + " on " + j.date + "@" + j.time + "\n, therefore your booking has been cancelled and you will be given a full refund. We are sorry for any incovenience caused.\n Thank you,\n - The Team @ Skrrt",
            to=[passenger.email]
            )

            db.session.commit()
            flash("Journey has been succesfully cancelled.", 'success')

        else:
            flash("You cannot cancel this journey within 15 minutes of the departure time", 'warning')

    except:
        db.session.rollback()
        flash("Error cancelling journey and corresponding bookings")

    return redirect(url_for('upcomingbookings'))


#retrieves all previous bookings made by the user
def previous_bookings():
    past_bookings = []
    booking = Booking.query.filter_by(user_id=current_user.id).all()
    booking = format_bookings(booking)
    
    current_datetime = datetime.now()
    for  b in booking:
        
        booking_date = datetime.strptime(b.get("date"), "%A %d %B %Y")
        booking_time = datetime.strptime(b.get("time"), "%I:%M %p")
        booking_datetime = datetime.combine(booking_date.date(), booking_time.time())

        
        time_difference = current_datetime - booking_datetime
        
        if time_difference > timedelta(minutes=15):
            past_bookings.append(b)
    return past_bookings
    

#MANAGER -----------------------------------------------------------------------------------------------------

#manager prefill
def manager_prefill(form_su, form_nm, form_bf, form_d):
    #get most recent booking fee update
    fee = getbookingfee()
    if fee == None:
        form_bf.booking_fee.data = 0.00

    else:
        #prefill current fee
        app.logger.info("prefilled booking fee with %f", fee.booking_fee_percentage * 100)
        form_bf.booking_fee.data = fee.booking_fee_percentage * 100 # convert decimal to percentage for user understanding


    #get current user discount and prefill
    discount = Discount.query.get(1)

    if discount == None:
        new_discount = Discount(avg_trips=0, discount_percentage=0.1)
        db.session.add(new_discount)
        db.session.commit()
        discount = Discount.query.get(1)

    #prefill discount form
    form_d.discount_perc.data = discount.discount_percentage * 100 #convert decimal to percentage for user understanding
    form_d.avg_trips.data = discount.avg_trips
    app.logger.info("prefilled discount with %f", discount.discount_percentage )

    #get all managers and all uses
    managers = Manager.query.all()
    user_choices = User.query.all()
    #get every user who is not a manager
    manager_ids = [manager.user_id for manager in managers]
    user_choices = [person for person in user_choices if person.id not in manager_ids]
    people = [(person.id, f"{person.first_name} {person.last_name} - {person.email}") for person in user_choices]
    form_nm.user_list.choices = (people)
    app.logger.info("Got choices")


def manager_booking_fee(form_bf, request):
    app.logger.info("validating form BOOKING FEES")
    try:
        #current
        fee = getbookingfee()

        new_fee = float(request.form.get('booking_fee'))
        new_fee = new_fee / 100

        if new_fee < 0 or new_fee > 1:
            flash("Fee percentage must be between 0 and 100", "warning")
            app.logger.info("Not in range")
            raise ValueError("Not in range")

        if fee != None and new_fee == fee.booking_fee_percentage:
            flash("No change in new vs old fee.", "sucess")
            app.logger.info("same value")
            raise ValueError("No change")

        #get todays date
        today = datetime.now()

        if fee != None:
            #addd end date to old fee
            app.logger.info("Editing last fee, adding end date")
            #add end date to current fee
            fee.end_date = today.now()
            app.logger.info("changed date")

        #create new fee
        app.logger.info("creating new fee")
        new_record = BookingFees(booking_fee_percentage=new_fee, start_date=today)
        app.logger.info("created.")

        #add new fee
        db.session.add(new_record)
        app.logger.info("added to session")
        db.session.commit()
        app.logger.info("done")
        flash("Fee successfully changed.", "success")

    except:
        db.session.rollback()
        flash("Error in fee update", "warning")

    return redirect(url_for("manager"))

def manager_new(form_nm, request):
    try:
        person = form_nm.user_list.data
        app.logger.info("got person")

        #insert into managers
        manager = Manager(user_id=person)
        app.logger.info("created manager")

        db.session.add(manager)
        app.logger.info("added to session")

        db.session.commit()
        app.logger.info("committed")

        flash("Successfuly assigned Manager role to user.", "success")


    except:
            db.session.rollback()
            flash("Error in manager assignment", "warning")

    return redirect(url_for("manager"))

def manager_discount(form_d, request):
    app.logger.info("validating form DISCOUNTS")
    try:
        decimal = float(request.form.get('discount_perc')) / 100
        avg_trips = float(request.form.get('avg_trips'))

        if decimal < 0 or decimal > 1:
            flash("Enter a valid percentage", "warning")
            raise ValueError("Percentage must be between 0 to 100")
            
        if avg_trips > 7 or avg_trips < 0:
            flash("Enter a valid percentage", "warning")
            raise ValueError("Must be between 1 and 7")

        discount.discount_percentage = decimal
        discount.avg_trips = avg_trips
        app.logger.info("changed values")

        db.session.commit()

        app.logger.info("success")
        flash("Update discount Successful", "success")

    except:
        db.session.rollback()
        flash("Error in fee update", "warning")
    
    return redirect(url_for("manager"))

#assign users to manager status, change discounts, view manager revenue and change booking fee
@app.route('/manager', methods=['GET', 'POST'])
@login_required
def manager():

    if current_user.is_manager == False:
        flash("You are not a manager and cannot access this page.")
        return redirect(url_for("profile"))

    #initilaise forms
    app.logger.info("manager")
    form_su = SearchUserForm()
    form_nm = SelectNewManagerForm()
    form_bf = BookingFeeForm()
    form_d = DiscountForm()

    #prefill forms
    manager_prefill(form_su, form_nm, form_bf, form_d)

    #submit booking fee form
    if  form_bf.validate_on_submit() and 'submit_form_bf' in request.form:
       manager_booking_fee(form_bf, request)

    #submit discounts form
    if form_d.validate_on_submit() and 'submit_form_d' in request.form:
        manager_discount(form_d, request)

    #new manager form
    if form_nm.validate_on_submit() and 'submit_form_nm' in request.form:
        manager_new(form_nm, request)

    return render_template('manager.html', form_d=form_d, form_bf=form_bf, form_su=form_su, form_nm=form_nm, title="Management")

#gets the most recent booking fee change. past fees must be stored for calculating revenue
def getbookingfee():
    fee = BookingFees.query.order_by(BookingFees.id.desc()).first()
    return fee

#check if discount applys to user
def checkifdiscountapplys(id):
    #get all current users bookings which have been completed
    bookings = Booking.query.filter_by(user_id=id, booking_status=BookingStatusEnum.COMPLETE.value).all()

    if bookings:
        for b in bookings:
            #get the correspodning completed journey for each booking, so that we can get the joruney date
            journeys = Journey.query.filter_by(id=b.journey_id, journey_status=JourneyStatusEnum.COMPLETE.value).all()
    else:
        return False
    
    if journeys:
        #from booking get journey id and date
        #get earliest date and last date
        #compare num of weeks difference
        #divide num of trips by num of weeks
        #if bigger or equal to get discount.avg_trips
        youngest_trip = min(journeys, key=lambda journeys: journeys.date)
        oldest_trip = max(journeys, key=lambda journeys: journeys.date)

        difference = ((oldest_trip.date - youngest_trip.date).days) // 7 #rounds down and discards .3 of a week

        discount= Discount.query.get(1) # there is only one discount you can get
        if difference:
            if difference >= discount.avg_trips:
                return True
            else:
                return False
    else:
        return False



##REVENUE and CHARTS --------------------------------------------------------------------------------------------- 

#form to filter revenue date and period. then calls charts to display chart
@app.route('/revenue', methods=['GET', 'POST'])
@login_required
def revenue():
    form=RevenueSettingsForm()

    #if user is a driver and a manager then need to choose what revenue they want to view
    if current_user.is_driver and current_user.is_manager:
        form.revenue_type.choices =  [('driver', 'Driver Revenue'), ('manager', 'Manager Revenue')]
    elif current_user.is_driver:
        form.revenue_type.choices =  [('driver', 'Driver Revenue')]
    elif current_user.is_manager:
        form.revenue_type.choices =  [('manager', 'Manager Revenue')]
    else:
        flash("You do not have the rights to access this page", "danger")
        return redirect(url_for("profile"))

    if form.validate_on_submit():
        timeframe=form.timeframe.data
        end_date=form.end_date.data
        revenue_type = form.revenue_type.data

        return charts(timeframe, end_date, revenue_type)

    return render_template(template_name_or_list='revenue.html', form=form,  title="View your Revenue", hide=True)#hide = true hides graph with empty

#makes charts 
def charts(timeframe, end_date, revenue_type):

    #get timeframe from form data
    if timeframe == "Week":
        frame=7
    else:
        frame=30

    #get period start and end as a datetime type
    period_end = end_date
    period_start = period_end - timedelta(days=frame)

    #initialise revenue list, holds tuple of journey total and date
    revenue = []
    frametotal = 0
 
    #get title according to time frame
    if frame == 7:
        title = "Revenue for the past 7 Days"
    else:
        title = "Revenue for the past 30 Days"

    #booking fee may be a list of fees and dates, then check range to see what fee 
    # #applies to each day. create a list same length as the days and each fee corresponds
    # # to same position in date array.

    #empty list of what the booking fee is per day
    bookingfees = [0] * frame
    for x in range (0,frame):
        #get fee that is in current date range of the fee
        current_date = period_start + timedelta(days=x)
        current_fee = BookingFees.query.filter(current_date >= BookingFees.start_date, current_date <= BookingFees.end_date).first()
        if current_fee != None:
            bookingfees[x] = current_fee.booking_fee_percentage 

    #if manager then you dont filter by driverid and bookingfee% of income
    if revenue_type == "manager":
        #get all completed journeys in period
        journeys = Journey.query.filter(Journey.date >= period_start, Journey.date <= period_end, Journey.journey_status==JourneyStatusEnum.COMPLETE.value).order_by(Journey.date.asc()).all()
        incomepercentage = bookingfees

    #if driver then get only your journeys and 1-bookingfee income percentage
    if revenue_type == "driver":
        #get j from completed journeys in period where driverid = current_user.driver_id
        journeys = Journey.query.filter(Journey.date >= period_start, Journey.date <= period_end, Journey.driver_id == current_user.driver_id, Journey.journey_status==JourneyStatusEnum.COMPLETE.value).order_by(Journey.date.asc()).all()
        
        #driver gets (1-bookingfee)% of the payments
        incomepercentage = [1-bf for bf in bookingfees]
        app.logger.info(incomepercentage)

    #fill journey total-date pair
    for j in journeys:
        #get every completed bookings for the journey and total the price for each user
        bookings_on_journey = Booking.query.filter_by(journey_id=j.id, booking_status=BookingStatusEnum.COMPLETE.value).all()
        journey_total = 0

        for b in bookings_on_journey:
            #get user configured price
            journey_total += b.price

        #which day in time period it is
        day_offset = (abs(j.date - period_start)).days - 1

        #work out journey total and append
        journeytotal = journey_total * float(incomepercentage[day_offset])
        revenue.append((journeytotal, j.date))
        frametotal += journeytotal

    #initialise dictionary
    revenue_by_date = {}

    #for each revenue date pair
    for journey_revenue, journey_date in revenue:
        if journey_date in revenue_by_date:
            revenue_by_date[journey_date] += journey_revenue
        else:
            revenue_by_date[journey_date] = journey_revenue

    #fill missing dates with 0
    current_date = period_start
    while current_date <= end_date:
        if current_date not in revenue_by_date:
            revenue_by_date[current_date] = 0
        current_date += timedelta(days=1)

    #sort dictionary
    sorted_revenue = sorted(revenue_by_date.items(), key=lambda x: x[0])


    #so that we can reconfigure settings 
    form = RevenueSettingsForm()

    #if user is a driver and a manager then need to choose what revenue they want to view
    if current_user.is_driver and current_user.is_manager:
        form.revenue_type.choices =  [('driver', 'Driver Revenue'), ('manager', 'Manager Revenue')]
    elif current_user.is_driver:
        form.revenue_type.choices =  [('driver', 'Driver Revenue')]
    elif current_user.is_manager:
        form.revenue_type.choices =  [('manager', 'Manager Revenue')]

    labels = sorted(set(date for date, _ in revenue_by_date.items()))

    return render_template(template_name_or_list='revenue.html', form=form, data=sorted_revenue, labels=labels, total=frametotal, title=title, hide=False) #hide=false shows graph

# Communication side -----------------------------------------------------------------------------------------

@app.route('/send-booking-email', methods=['GET', 'POST'])
@login_required
def booking_confirmation():
    user = current_user
    send_booking_confirmation_email(user, Journey_id)
    flash("email sent succesfully", 'success')
    return redirect(url_for('profile'))

def send_booking_confirmation_email(userid, booking_id):

    user = User.query.get(userid)

    booking = Booking.query.get(booking_id)
    bookings = format_bookings([booking])
    booking = bookings[0]
    
    booking_pickup_location = booking['pickup_location']
    booking_drop_off_location = booking['dropoff_location']
    booking_date = booking['date']
    booking_time = booking['time']
    booking_price = booking['price']
    driver_name = booking["driver_name"]
    
    booking_link = url_for('upcomingbookings', _external=True
                           )
    email_Body = render_template("Bookingconfirmationemail.html",   
                                driver_name = driver_name, 
                                booking_pickup_location = booking_pickup_location,
                                booking_drop_off_location = booking_drop_off_location,
                                booking_date = booking_date,
                                booking_time = booking_time,
                                booking_price = booking_price,
                                booking_link = booking_link)
    
    message = EmailMessage(
        subject="Booking confirmation",
        body=email_Body,
        to=[user.email]
        )

    message.content_subtype = "html"
    
    message.send()

#access support page and send email to get help
@app.route('/support', methods=['GET', 'POST'])
@login_required
def supportpage():
    form = SupportPage()
    
    if form.validate_on_submit():
        send_support_message(form.name.data, form.email.data, form.subject.data, form.message.data)
        flash('Message has been sent','success')
        return redirect(url_for('profile'))
    return render_template('supportpage.html', form = form, title = 'Skrrrt! Support page')

#sends the message
def send_support_message(name, email, subject, message):
    
    message = EmailMessage(
        subject=f" Support Request from {name}: {subject}",
        body= f"{message}, Requester Email: {email}", 
        to=['skrrrtlimited@gmail.com']
    )
    
    message.send()
    

#user alert to driver that they are at the pickup location
@app.route('/i-am-here/<int:booking_id>', methods=['POST'])
def alert_at_pickup_location(booking_id):
    booking = Booking.query.get(booking_id)
    #get booking details
    bookings = format_bookings([booking])
    booking = bookings[0]

    #get passenger name
    rider_name = booking["user_name"]
    rider_email = booking["user_email"]
    rider_phone_num = booking["user_phone_num"]

    #Get driver details
    driver_name = booking["driver_name"]
    driver_email =booking["driver_email"]

    #send email
    message = EmailMessage(
        subject= f"Rider '{rider_name}' is at the pickup location",
        body= f"Passenger '{rider_name}' has arrived for their journey, commencing at { booking['time'] } on { booking['date']}. Having issues finding them? Contact the passenger on the phone number: {rider_phone_num}.", 
        to=[driver_email] 
    )

    message.send()

    flash("Alert sent to driver.", "info")
    return redirect(url_for('upcomingbookings'))

# creating an accept/decline routes for the bookings

@app.route('/get_review/<int:journey_id>', methods=['GET'])
def get_review_id(journey_id):
    # Query the database to get the booking details based on the booking ID
    bookings = Booking.query.filter_by(journey_id=journey_id).all()

    if not bookings:
        return jsonify({'success': False, 'error': 'No bookings found for this journey'})

    reviews = []

    for book in bookings:
        review = Review.query.filter_by(booking_id=book.id).first()
        if review:
            reviews.append({
                'booking_id': book.id,
                'review_title': review.review_title,
                'comment': review.comment,
                'rating': review.rating
            })

    if reviews != []:
        return jsonify({'success': True, 'reviews': reviews})
    else:
        return jsonify({'success': False, 'error': 'No reviews found for this journey'})

@app.route('/driver-review/<int:booking_id>', methods=['POST'])
def add_driver_review(booking_id):
        # validate csrf token if missing, causes isses with the request later on
        csrf_token = request.headers.get("X-CSRFToken")

        try:
            validate_csrf(csrf_token)
        except Exception as e:
            return jsonify({"success": False, "error": "Invalid or missing CSRF token"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "JSON not received"}), 500

        booking = Booking.query.filter_by(id=booking_id).join(Journey).join(Driver).first()

        if not booking:
            return jsonify({"success": False, "message": "Booking not found!"}), 404

        if booking.reviewed:
            return jsonify({"status": "error", "message": "Review already submitted!"})

        review_title = data.get("review_title")
        comment = data.get("comment")
        rating = data.get("rating")

        if (not review_title) or (not comment) or (not rating):
            flash("All fields must be filled", "danger")
            return jsonify({"success": False, "message": "You must fill in all fields"})


        try:
            driver = booking.journey.driver


            current_rating_val = driver.driver_rating
            current_num_rating_val = driver.num_ratings

            # Calculate new average rating
            new_rating = (current_rating_val + float(rating)) / (int(current_num_rating_val) + 1)

            driver.driver_rating = new_rating
            driver.num_ratings += 1

            # Create and save new review
            new_review = Review(
                booking_id=int(booking_id),
                review_title=review_title,
                comment=comment,
                rating=rating,
            )
            # boolean for sql
            booking.reviewed = True

            db.session.add(new_review)
            db.session.commit()

            flash("Review Sent!", "success")
            return jsonify({"success": True, "message": "Review Sent!"})

        except:
            flash("Error, Cannot Send Review", "error")
            return jsonify({"success": False, "message": "Cannot Send Review"}), 500


@app.route('/card-select/<int:journey_id>/<float:price>', methods=['GET', 'POST'])
@login_required
def card_select(journey_id, price):
    #journey_id = session.get('pending_journey_id')
    price_pass = price
    journey_id_pass = journey_id
    print(price_pass, journey_id_pass)
    if not journey_id:
        flash("Please select a journey first.", "error")
        return redirect(url_for('availableJourneys'))
    
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        selected_card_id = request.form.get("payment_method")

        if not selected_card_id:
            flash("Please select a payment method.", "error")
            return redirect(url_for('card_select', journey_id=journey_id_pass, price=price_pass))
        
        session['pending_payment_method_id'] = selected_card_id
        
        return redirect(url_for('book_journey', journey_id=journey_id_pass, price=price_pass))
    print(journey_id_pass, price_pass)
    return render_template("card_select.html",title="Card Select", payment_methods=payment_methods, journey_id=journey_id_pass, price=price_pass)


@app.route('/add-card/<int:journey_id>/<float:price>', methods=['GET', 'POST'])
@login_required
def add_card(journey_id, price):
    price_pass = price
    journey_id_pass = journey_id
    if request.method == 'POST':
        token = request.form.get("stripeToken")

        if not token:
            flash("Invalid card details.", "error")
            return redirect(url_for("add_card", journey_id=journey_id_pass, price=price_pass))

        try:
            if not current_user.stripe_customer_id:
                customer = stripe.Customer.create(email=current_user.email)
                current_user.stripe_customer_id = customer.id
                db.session.commit()
            else:
                customer = stripe.Customer.retrieve(current_user.stripe_customer_id)

            payment_method = stripe.PaymentMethod.create(
                type="card",
                card={"token": token}
            )
            stripe.PaymentMethod.attach(payment_method.id, customer=customer.id)

            card_details = stripe.PaymentMethod.retrieve(payment_method.id).card

            new_payment = PaymentMethod(
                user_id=current_user.id,
                payment_method_id=payment_method.id,
                brand=card_details.brand,
                last4=card_details.last4,
                exp_date = f"{card_details.exp_month:02}/{card_details.exp_year % 100:02}"
            )

            db.session.add(new_payment)
            db.session.commit()

            flash("Card added successfully!", "success")
            return redirect(url_for("card_select", journey_id=journey_id_pass, price=price_pass))

        except stripe.error.StripeError as e:
            flash(f"Stripe error: {e.user_message}", "error")
            return redirect(url_for("add_card", journey_id=journey_id_pass, price=price_pass))

    return render_template("add_card.html", title="Add Card", journey_id=journey_id_pass, price=price_pass)


def refund(booking_id, late = False):
    try:
        booking = Booking.query.filter_by(id=booking_id).first()
        payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)
        charge_id = payment_intent.charges.data[0].id
        if late:
            amount = int(round(booking.price*25)) # Convert a quarter into int in pence for stripe
            refund = stripe.Refund.create(charge_id, amount=amount)
        else:
            refund = stripe.Refund.create(charge_id)
        booking.payment_status = PaymentStatusEnum.REFUNDED
        db.session.commit()

    except Exception as e:
        return jsonify({"error": str(e)}), 400

def renew_payment(booking_id):
    booking = Booking.query.filter_by(id=booking_id).first()
    old_payment_intent = stripe.PaymentIntent.retrieve(booking.payment_intent_id)

    new_payment_intent = stripe.PaymentIntent.create(
        amount=old_payment_intent.amount,
        currency="gbp",
        customer=old_payment_intent.customer,
        payment_method=old_payment_intent.payment_method
    )

    #Update the booking payment intent to match new one
    booking.payment_intent_id = new_payment_intent.id
    db.session.commit()
