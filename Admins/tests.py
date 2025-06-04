from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from User.models import Prediction # For creating Prediction objects
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest import mock # For mocking
from django.core.files.storage import FileSystemStorage # To potentially mock its delete method
from io import BytesIO # For checking mock call
from django.contrib.messages import get_messages # For checking messages

class AdminViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='adminuser', password='password123', email='admin@example.com')
        # Provide first_name and last_name for regular_user to avoid potential IntegrityError
        self.regular_user = User.objects.create_user(
            username='testuser',
            password='password123',
            first_name='Test',
            last_name='RegularUser'
            )

        self.adminhome_url = reverse('adminhome')
        self.admingraphs_url = reverse('admingraphs')
        self.adminaccuracy_url = reverse('adminaccuracy')
        self.admindisplaypredictions_url = reverse('admindisplaypredictions')

    def test_adminhome_get_as_admin(self):
        self.client.login(username='adminuser', password='password123')
        response = self.client.get(self.adminhome_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Admin/adminhome.html')
        self.assertIn('users', response.context)
        self.assertIn(self.regular_user, response.context['users'])
        self.assertNotIn(self.admin_user, response.context['users'])

    def test_adminhome_get_as_non_admin(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.adminhome_url)
        self.assertEqual(response.status_code, 200)

    def test_admin_update_userstatus(self):
        self.client.login(username='adminuser', password='password123')
        initial_status = self.regular_user.is_active
        url = reverse('admin_update_userstatus', args=[self.regular_user.id])
        response = self.client.get(url)
        self.assertRedirects(response, self.adminhome_url)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.is_active, not initial_status)

    @mock.patch('matplotlib.pyplot.savefig')
    def test_admingraphs_get(self, mock_savefig):
        self.client.login(username='adminuser', password='password123')
        Prediction.objects.create(user_input="spam message", result="Spam")
        Prediction.objects.create(user_input="ham message", result="Ham")

        response = self.client.get(self.admingraphs_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Admin/admingraph.html')
        self.assertIn('line_graph', response.context)
        self.assertIn('pie_chart', response.context)
        self.assertIsInstance(response.context['line_graph'], str)
        self.assertIsInstance(response.context['pie_chart'], str)
        self.assertEqual(mock_savefig.call_count, 2)
        for call_args in mock_savefig.call_args_list:
            self.assertIsInstance(call_args[0][0], BytesIO)

    def test_adminaccuracy_get(self):
        self.client.login(username='adminuser', password='password123')
        response = self.client.get(self.adminaccuracy_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Admin/adminaccuracy.html')

    @mock.patch.object(FileSystemStorage, 'delete')
    def test_adminaccuracy_post_with_file(self, mock_delete):
        self.client.login(username='adminuser', password='password123')
        csv_content = "Message,EncodedClass\nThis is a test,0\nAnother test,1"
        dummy_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'), content_type="text/csv")

        response = self.client.post(self.adminaccuracy_url, {'csv_file': dummy_file})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Admin/adminaccuracy.html')
        self.assertIn('results', response.context)
        self.assertEqual(response.context['results'], [])
        mock_delete.assert_called_once()

    def test_admindisplaypredictions_get(self):
        self.client.login(username='adminuser', password='password123')

        response_no_preds = self.client.get(self.admindisplaypredictions_url)
        self.assertEqual(response_no_preds.status_code, 200)
        self.assertTemplateUsed(response_no_preds, 'Admin/admindisplaypredictions.html')
        self.assertIn('page_obj', response_no_preds.context)
        self.assertEqual(len(response_no_preds.context['page_obj']), 0)

        for i in range(12):
            Prediction.objects.create(user_input=f"Test input {i}", result="Ham" if i % 2 == 0 else "Spam")

        response_with_preds = self.client.get(self.admindisplaypredictions_url)
        self.assertEqual(response_with_preds.status_code, 200)
        self.assertTemplateUsed(response_with_preds, 'Admin/admindisplaypredictions.html')
        self.assertIn('page_obj', response_with_preds.context)
        self.assertTrue(len(response_with_preds.context['page_obj']) > 0)
        self.assertTrue(response_with_preds.context['page_obj'].has_next())

        response_page2 = self.client.get(self.admindisplaypredictions_url + "?page=2")
        self.assertEqual(response_page2.status_code, 200)
        self.assertTemplateUsed(response_page2, 'Admin/admindisplaypredictions.html')
        self.assertIn('page_obj', response_page2.context)
        self.assertTrue(len(response_page2.context['page_obj']) > 0)
        self.assertFalse(response_page2.context['page_obj'].has_next())
        self.assertEqual(response_page2.context['page_obj'].number, 2)


class AdminWorkflowIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='mainadmin',
            password='password123',
            email='mainadmin@example.com'
        )
        self.workflow_user = User.objects.create_user(
            username='workflowreguser',
            password='password123',
            first_name='Workflow',
            last_name='Regular',
            is_active=True # Explicitly set initial state
        )
        self.adminhome_url = reverse('adminhome')
        self.update_status_url_template = 'admin_update_userstatus' # Name of the URL pattern

    def test_admin_activate_deactivate_user_workflow(self):
        # Log in as admin
        self.client.login(username=self.admin_user.username, password='password123')

        # Check user is present in adminhome
        response_home1 = self.client.get(self.adminhome_url)
        self.assertEqual(response_home1.status_code, 200)
        # Ensure our specific workflow_user is in the list of users
        self.assertIn(self.workflow_user, response_home1.context['users'])

        initial_status = self.workflow_user.is_active

        # Update user status (deactivate if active, activate if inactive)
        update_url = reverse(self.update_status_url_template, args=[self.workflow_user.id])
        # Follow redirect to get messages from the rendered page
        response_update1 = self.client.get(update_url, follow=True)
        self.assertEqual(response_update1.status_code, 200) # Check final page is OK

        self.workflow_user.refresh_from_db()
        self.assertEqual(self.workflow_user.is_active, not initial_status, "User status did not toggle the first time")

        # Check messages for the first update
        messages1 = list(get_messages(response_update1.wsgi_request)) # Messages from the final request
        self.assertTrue(len(messages1) > 0, "No message after first status update")
        expected_message_text1 = f"User {self.workflow_user.username} has been {'activated' if self.workflow_user.is_active else 'deactivated'}."
        self.assertEqual(str(messages1[0]), expected_message_text1)

        # Toggle status back
        # Follow redirect for the second update as well
        response_update2 = self.client.get(update_url, follow=True)
        self.assertEqual(response_update2.status_code, 200) # Check final page is OK

        self.workflow_user.refresh_from_db()
        self.assertEqual(self.workflow_user.is_active, initial_status, "User status did not toggle back to original")

        # Check messages for the second update
        messages2 = list(get_messages(response_update2.wsgi_request)) # Messages from the final request
        self.assertTrue(len(messages2) > 0, "No message after second status update")
        # After 2nd toggle (initial True -> False -> True), message should be "activated"
        expected_message_text2 = f"User {self.workflow_user.username} has been activated."
        self.assertEqual(str(messages2[0]), expected_message_text2)

        # Verify user is still listed in adminhome (status change doesn't remove them)
        response_home2 = self.client.get(self.adminhome_url)
        self.assertEqual(response_home2.status_code, 200)
        self.assertIn(self.workflow_user, response_home2.context['users'])
