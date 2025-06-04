import joblib
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model
from django.shortcuts import render
from .models import Prediction
from django.utils.timezone import now
import sys

# Initialize tokenizer and model as None
tokenizer = None
hybrid_model = None

try:
    # Load tokenizer and model globally
    tokenizer = joblib.load("model/tokenizer.joblib")
    hybrid_model = load_model("model/hybrid_lstm_cnn_model.h5")
except FileNotFoundError:
    print("Error: Model or tokenizer file not found. Predictions will not work.", file=sys.stderr)
except Exception as e: # Catch other potential errors during model loading
    print(f"Error loading model/tokenizer in User.views: {e}", file=sys.stderr)
    # Ensure hybrid_model and tokenizer are None if loading failed
    tokenizer = None
    hybrid_model = None

# Create your views here.
def userhome(request):
    user = request.user
    return render(request, 'User/userhome.html', {'user':user})

def userpredict(request):
    if tokenizer is None or hybrid_model is None:
        return render(request, 'User/userpredict.html', {'error_message': 'Prediction service is currently unavailable due to missing model files.'})

    if request.method == 'POST':
        # Get user input
        user_input = request.POST.get('user_input', '')

        # Tokenize and pad the user input
        input_seq = tokenizer.texts_to_sequences([user_input])
        input_pad = pad_sequences(input_seq, maxlen=100, padding='post')

        # Predict using the model
        prediction = hybrid_model.predict(input_pad)
        result = "Spam" if prediction[0] > 0.5 else "Ham"

        # Save user input and result to the database
        Prediction.objects.create(user_input=user_input, result=result, created_at=now())

        # Pass prediction result to template
        return render(request, 'User/userpredict.html', {'result': result, 'input': user_input})

    return render(request, 'User/userpredict.html')
