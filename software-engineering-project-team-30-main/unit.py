import unittest
from app import app, db, bcrypt
from app.models import User

class baseClass(unittest.TestCase):

    def setUp(self):
        # configure for testing
        app.config['TESTING'] = True

        # disable to be able to test more efficiently

        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        # create the database tables to be used for testing
        with app.app_context():
            db.create_all()

    def tearDown(self):
        # good practice to remove temporarily created tables
        with app.app_context():
            db.session.remove()
            db.drop_all()

class TestAuthentication(baseClass):
    def setUp(self):
        # configure for testing
        app.config['TESTING'] = True

        # disable to be able to test more efficiently

        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        # create the database tables to be used for testing
        with app.app_context():
            db.create_all()

    def tearDown(self):
        # good practice to remove temporarily created tables
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_user_registration(self):
        with app.app_context():
            user = User(
                first_name='Test',
                last_name='User',
                email='test_direct@example.com',
                phone_number='1234567890',
                password=bcrypt.generate_password_hash('Password123')
            )
            db.session.add(user)
            db.session.commit()

            # check if the user exists
            user_in_db = User.query.filter_by(email='test_direct@example.com').first()
            self.assertIsNotNone(user_in_db)
            self.assertEqual(user_in_db.first_name, 'Test')
            self.assertEqual(user_in_db.last_name, 'User')

    def test_login_with_correct_credentials(self):
        with app.app_context():
            hashed_password = bcrypt.generate_password_hash('Password123')
            user = User(
                first_name='Test',
                last_name='User',
                email='login_test@example.com',
                phone_number='1234567890',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()

            # attempting a login
            response = self.client.post('/login', data={
                'email': 'login_test@example.com',
                'password': 'Password123'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)

    def test_login_with_wrong_password(self):
        with app.app_context():
            # create a fake user
            hashed_password = bcrypt.generate_password_hash('Password123')
            user = User(
                first_name='Test',
                last_name='User',
                email='wrong_pw@example.com',
                phone_number='1234567890',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()

            # using wrong password to login
            response = self.client.post('/login', data={
                'email': 'wrong_pw@example.com',
                'password': 'WrongPassword'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)

            self.assertIn(b'login', response.data.lower())

    def test_logout(self):
        # login first before we can log out
        with app.app_context():
            # Create a user
            hashed_password = bcrypt.generate_password_hash('Password123')
            user = User(
                first_name='Test',
                last_name='User',
                email='logout_test@example.com',
                phone_number='1234567890',
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()

            # login
            self.client.post('/login', data={
                'email': 'logout_test@example.com',
                'password': 'Password123'
            })

            # then logout
            response = self.client.get('/logout', follow_redirects=True)

            # check what happens after this
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'login', response.data.lower())

if __name__ == '__main__':
    unittest.main()
