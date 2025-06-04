import pandas as pd
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model
from django.shortcuts import render
from .models import Prediction
from django.utils.timezone import now

# Create your views here.
def userhome(request):
    user = request.user
    return render(request, 'User/userhome.html', {'user':user})

def userpredict(request):
    if request.method == 'POST':
        # Load Dataset
        data = pd.read_csv("model/dataset.csv")
        data['Message'] = data['Message'].astype(str)

        # Split the dataset into training and testing sets
        X = data['Message']
        y = data['EncodedClass']
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Tokenize and pad sequences for deep learning models
        tokenizer = Tokenizer()
        tokenizer.fit_on_texts(X_train)
        X_train_seq = tokenizer.texts_to_sequences(X_train)
        X_test_seq = tokenizer.texts_to_sequences(X_test)
        X_train_pad = pad_sequences(X_train_seq, maxlen=100, padding='post')
        X_test_pad = pad_sequences(X_test_seq, maxlen=100, padding='post')
        vocab_size = len(tokenizer.word_index) + 1

        # Get user input
        user_input = request.POST.get('user_input', '')

        # Tokenize and pad the user input
        input_seq = tokenizer.texts_to_sequences([user_input])
        input_pad = pad_sequences(input_seq, maxlen=100, padding='post')

        # Load the pre-trained model
        hybrid_model = load_model("model/hybrid_lstm_cnn_model.h5")

        # Predict using the model
        prediction = hybrid_model.predict(input_pad)
        result = "Spam" if prediction[0] > 0.5 else "Ham"

        # Save user input and result to the database
        Prediction.objects.create(user_input=user_input, result=result, created_at=now())

        # Pass prediction result to template
        return render(request, 'User/userpredict.html', {'result': result, 'input': user_input})

    return render(request, 'User/userpredict.html')
