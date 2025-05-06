# Skrrt!

## Project Description
- A Car-Share Web-Based Application that allows you to book onto journeys!
- Join the community today by simply signing up, registering your car and booking some journeys

# Installation and Running

Access the deployed website here! https://skrrt-car-pool-services.onrender.com

If you are manually running or debugging (for our team), install all the dependancies and execute the run command below: 
python3 -m venv flask
source flask/bin/activate
pip install flask
pip install flask-login
pip install flask-mail
pip install flask-mailman
pip install flask-sqlalchemy
pip install flask-migrate
pip install flask-whooshalchemy
pip install flask-wtf
pip install flask-babel
pip install coverage
pip install flask-admin
pip install flask_bcrypt
pip install email_validator
pip install schedule
pip install stripe
flask db init
python3 run.py


## File Structure 

```
├── README.md
├── __pycache__
│   └── config.cpython-312.pyc
├── app
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-312.pyc
│   │   ├── __init__.cpython-313.pyc
│   │   ├── forms.cpython-312.pyc
│   │   ├── forms.cpython-313.pyc
│   │   ├── models.cpython-312.pyc
│   │   ├── models.cpython-313.pyc
│   │   ├── views.cpython-312.pyc
│   │   └── views.cpython-313.pyc
│   ├── db_create.py
│   ├── forms.py
│   ├── models.py
│   ├── static
│   │   ├── images
│   │   │   ├── Affordable.jpg
│   │   │   ├── Flexible.jpg
│   │   │   ├── Logo.png
│   │   │   ├── Taxi_home.jpg
│   │   │   └── Trust.png
│   │   ├── script.js
│   │   └── styles.css
│   ├── templates
│   │   ├── Bookingconfirmationemail.html
│   │   ├── accessprofile.html
│   │   ├── add_card.html
│   │   ├── availablejourneys.html
│   │   ├── base.html
│   │   ├── baseride.html
│   │   ├── bookings.html
│   │   ├── card_select.html
│   │   ├── deleteaccount.html
│   │   ├── driversignup.html
│   │   ├── editprofile.html
│   │   ├── homepage.html
│   │   ├── login.html
│   │   ├── manager.html
│   │   ├── newcar.html
│   │   ├── newride.html
│   │   ├── profile.html
│   │   ├── resetPasswordEmailContent.html
│   │   ├── resetPasswordForm.html
│   │   ├── resetPasswordRequest.html
│   │   ├── revenue.html
│   │   ├── savedLocations.html
│   │   ├── signUp.html
│   │   └── supportpage.html
│   └── views.py
├── app.db
├── config.py
├── requirements.txt
├── run.py
└── unit.py
```
