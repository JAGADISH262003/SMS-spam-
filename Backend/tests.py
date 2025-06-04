from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages # To check messages

# Import for workflow test
from User.views import hybrid_model as user_views_hybrid_model # To check if model loaded in User.views

class BackendViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.index_url = reverse('index')
        self.login_page_url = reverse('login_page')
        self.register_page_url = reverse('register_page')

    def test_index_get(self):
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_login_page_get(self):
        response = self.client.get(self.login_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_register_page_get(self):
        response = self.client.get(self.register_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')


class AuthLogicTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_login_url = reverse('user_login')
        self.user_registration_url = reverse('user_registration')
        self.user_logout_url = reverse('user_logout')
        self.userhome_url = reverse('userhome')
        self.index_url = reverse('index')
        self.login_page_url = reverse('login_page')

        self.test_user_username = 'testloginuser'
        self.test_user_password = 'password123'
        self.user = User.objects.create_user(
            username=self.test_user_username,
            password=self.test_user_password,
            first_name='Test',
            last_name='UserAuth'
        )

    def test_user_login_success_and_failure(self):
        response_success = self.client.post(self.user_login_url, {
            'username': self.test_user_username,
            'password': self.test_user_password
        })
        self.assertRedirects(response_success, self.userhome_url)

        self.client.login(username=self.test_user_username, password=self.test_user_password)
        response_authenticated_check = self.client.get(self.userhome_url)
        self.assertTrue(response_authenticated_check.context['user'].is_authenticated)

        response_failure = self.client.post(self.user_login_url, {
            'username': self.test_user_username,
            'password': 'wrongpassword'
        })
        self.assertRedirects(response_failure, self.login_page_url)
        messages = list(get_messages(response_failure.wsgi_request))
        self.assertTrue(any(message.tags == "error" and "Invalid username or password." in message.message for message in messages))

    def test_user_registration_success_and_duplicate(self):
        new_username = 'newtestuser'
        new_password = 'newpassword123'

        response_success = self.client.post(self.user_registration_url, {
            'username': new_username,
            'email': 'newuser@example.com',
            'password': new_password,
            'confirm_password': new_password,
            'first_name': 'New',
            'last_name': 'RegUser'
        })
        self.assertRedirects(response_success, self.login_page_url)
        self.assertTrue(User.objects.filter(username=new_username).exists())
        messages_success = list(get_messages(response_success.wsgi_request))
        self.assertTrue(any(message.tags == "success" and "Registration successful" in message.message for message in messages_success))

        response_duplicate = self.client.post(self.user_registration_url, {
            'username': new_username,
            'email': 'another@example.com',
            'password': new_password,
            'confirm_password': new_password,
            'first_name': 'New',
            'last_name': 'UserDup'
        })
        self.assertRedirects(response_duplicate, reverse('register_page'))
        messages_duplicate = list(get_messages(response_duplicate.wsgi_request))
        self.assertTrue(any(message.tags == "error" and "Username already exists" in message.message for message in messages_duplicate))

        response_password_mismatch = self.client.post(self.user_registration_url, {
            'username': 'anothernewuser',
            'email': 'anothernew@example.com',
            'password': new_password,
            'confirm_password': 'mismatchedpassword',
            'first_name': 'Mismatch',
            'last_name': 'User'
        })
        self.assertRedirects(response_password_mismatch, reverse('register_page'))
        messages_mismatch = list(get_messages(response_password_mismatch.wsgi_request))
        self.assertTrue(any(message.tags == "error" and "Passwords do not match" in message.message for message in messages_mismatch))

    def test_user_logout(self):
        self.client.login(username=self.test_user_username, password=self.test_user_password)
        response_loggedin = self.client.get(self.userhome_url)
        self.assertEqual(response_loggedin.status_code, 200)
        self.assertTrue(response_loggedin.context['user'].is_authenticated)

        response_logout = self.client.get(self.user_logout_url)
        self.assertRedirects(response_logout, self.login_page_url)

        response_after_logout = self.client.get(self.index_url)
        self.assertTrue(response_after_logout.context['user'].is_anonymous)
        self.assertNotIn('_auth_user_id', self.client.session)


class UserWorkflowIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_registration_url = reverse('user_registration')
        self.user_login_url = reverse('user_login')
        self.userhome_url = reverse('userhome')
        self.userpredict_url = reverse('userpredict')
        self.login_page_url = reverse('login_page')

    def test_full_user_registration_login_predict_workflow(self):
        # Registration
        reg_username = "workflowuser"
        reg_password = "password123"
        reg_email = "workflow@example.com"
        response_reg = self.client.post(self.user_registration_url, {
            'username': reg_username,
            'email': reg_email,
            'password': reg_password,
            'confirm_password': reg_password,
            'first_name': 'Workflow',
            'last_name': 'UserReg'
        })
        self.assertRedirects(response_reg, self.login_page_url, msg_prefix="Registration redirect failed")

        # Verify user created (and is inactive by default as per view logic)
        workflow_user = User.objects.get(username=reg_username)
        self.assertIsNotNone(workflow_user)
        self.assertFalse(workflow_user.is_active, "User should be inactive after registration")

        # Manually activate user for login test (as admin approval is mocked)
        workflow_user.is_active = True
        workflow_user.save()

        # Login
        response_login = self.client.post(self.user_login_url, {
            'username': reg_username,
            'password': reg_password
        })
        self.assertRedirects(response_login, self.userhome_url, msg_prefix="Login redirect failed")

        # GET User Predict Page
        response_predict_get = self.client.get(self.userpredict_url)
        self.assertEqual(response_predict_get.status_code, 200, "Userpredict GET failed")
        self.assertTemplateUsed(response_predict_get, 'User/userpredict.html')

        # POST to User Predict Page
        user_message_input = "This is a test message for prediction."
        response_predict_post = self.client.post(self.userpredict_url, {'user_input': user_message_input})
        self.assertEqual(response_predict_post.status_code, 200, "Userpredict POST failed")

        # Check context based on model loading status in User.views
        if user_views_hybrid_model is None: # Check the actual loaded model in User.views
            self.assertIn('error_message', response_predict_post.context)
            self.assertEqual(response_predict_post.context['error_message'],
                             'Prediction service is currently unavailable due to missing model files.')
        else:
            self.assertIn('result', response_predict_post.context)
            self.assertIn('input', response_predict_post.context)
            self.assertEqual(response_predict_post.context['input'], user_message_input)
            self.assertTrue(response_predict_post.context['result'] in ['Spam', 'Ham'])
