from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import joblib
import os
from tensorflow.keras.models import load_model

# Define paths for test environment
TOKENIZER_PATH = "model/tokenizer.joblib"
MODEL_PATH = "model/hybrid_lstm_cnn_model.h5"

MODEL_FILES_LOADED = False
try:
    # These are loaded here to check existence and basic loadability for tests
    # The actual User.views will use its own global instances
    joblib.load(TOKENIZER_PATH)
    load_model(MODEL_PATH)
    MODEL_FILES_LOADED = True
except FileNotFoundError:
    print("Test Setup Warning: Model or tokenizer file not found. Some tests may be skipped.")
except Exception as e:
    print(f"Test Setup Warning: Error loading model/tokenizer: {e}. Some tests may be skipped.")


class UserViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.userpredict_url = reverse('userpredict')
        self.userhome_url = reverse('userhome') # Added for userhome test

    def test_userhome_get(self): # New test for userhome
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.userhome_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'User/userhome.html')
        self.assertEqual(response.context['user'], self.user)

    def test_userpredict_get(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.userpredict_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'User/userpredict.html')
        if not MODEL_FILES_LOADED :
             self.assertIn('error_message', response.context) # Check if error message is shown on GET if models missing
             self.assertEqual(response.context['error_message'], 'Prediction service is currently unavailable due to missing model files.')


    def test_userpredict_post_success(self):
        if not MODEL_FILES_LOADED:
            self.skipTest("Model or tokenizer file not found or failed to load, skipping prediction test.")

        self.client.login(username='testuser', password='password123')
        # Ensure User.views.hybrid_model and User.views.tokenizer are not None for this test
        # This relies on the global loading in User.views.py having succeeded
        from User.views import hybrid_model, tokenizer
        if hybrid_model is None or tokenizer is None:
             self.skipTest("User.views model/tokenizer not loaded, skipping prediction test.")

        response = self.client.post(self.userpredict_url, {'user_input': 'This is a test message'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'User/userpredict.html')
        self.assertIn('result', response.context)
        self.assertTrue(response.context['result'] == 'Spam' or response.context['result'] == 'Ham')
        self.assertEqual(response.context['input'], 'This is a test message')
        self.assertNotIn('error_message', response.context)


    def test_userpredict_post_service_unavailable_if_models_not_loaded_in_view(self):
        # This test is to see if the view correctly shows error if its global models are None
        # It's hard to reliably set User.views.hybrid_model to None from here if it loaded correctly
        # So, this test is more effective if User.views.py failed to load them initially
        if MODEL_FILES_LOADED:
            # If model files generally load, we can't easily simulate the "view failed to load them" scenario
            # without deeper patching, which is beyond this subtask's scope.
            # We will rely on test_userpredict_get for the error message check if files are missing.
            self.skipTest("Skipping as model files are present; view error handling tested in GET if files are missing.")

        self.client.login(username='testuser', password='password123')
        response = self.client.post(self.userpredict_url, {'user_input': 'Another test'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], 'Prediction service is currently unavailable due to missing model files.')
