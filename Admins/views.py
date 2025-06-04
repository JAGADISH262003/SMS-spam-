from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from User.models import Prediction
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from django.core.paginator import Paginator
import pandas as pd
from django.core.files.storage import FileSystemStorage
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Conv1D, MaxPooling1D, GlobalMaxPooling1D
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

def adminhome(request):
    users = User.objects.filter(is_staff=False, is_superuser=False) 
    return render(request, "Admin/adminhome.html", {"users": users})

def admin_update_userstatus(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        # Toggle the is_active status
        user.is_active = not user.is_active
        user.save()

        # Display message based on the action
        if user.is_active:
            messages.success(request, f"User {user.username} has been activated.")
        else:
            messages.success(request, f"User {user.username} has been deactivated.")
        
        return redirect('adminhome')  # Redirect back to the admin home page
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('adminhome')
    
def admingraphs(request):
    # Query the database to get counts of Ham and Spam
    spam_count = Prediction.objects.filter(result="Spam").count()
    ham_count = Prediction.objects.filter(result="Ham").count()

    # Generate Line Chart
    plt.figure(figsize=(6, 4))
    categories = ['Ham', 'Spam']
    counts = [ham_count, spam_count]
    plt.plot(categories, counts, marker='o')
    plt.title('Ham vs Spam Predictions (Line Chart)')
    plt.xlabel('Category')
    plt.ylabel('Count')
    plt.grid(True)
    plt.tight_layout()

    # Save the line chart to a BytesIO buffer
    buffer_line = BytesIO()
    plt.savefig(buffer_line, format='png')
    buffer_line.seek(0)
    line_image_png = buffer_line.getvalue()
    buffer_line.close()
    line_graph_image = base64.b64encode(line_image_png).decode('utf-8')

    # Generate Pie Chart
    plt.figure(figsize=(6, 6))
    plt.pie(
        counts,
        labels=categories,
        autopct='%1.1f%%',
        startangle=90,
        colors=['lightblue', 'orange'],
    )
    plt.title('Ham vs Spam Predictions (Pie Chart)')
    plt.tight_layout()

    # Save the pie chart to a BytesIO buffer
    buffer_pie = BytesIO()
    plt.savefig(buffer_pie, format='png')
    buffer_pie.seek(0)
    pie_image_png = buffer_pie.getvalue()
    buffer_pie.close()
    pie_chart_image = base64.b64encode(pie_image_png).decode('utf-8')

    # Render the template with both graphs
    return render(request, 'Admin/admingraph.html', {
        'line_graph': line_graph_image,
        'pie_chart': pie_chart_image
    })
    
def adminaccuracy(request):
    if request.method == 'POST' and request.FILES['csv_file']:
        # Save the uploaded file
        csv_file = request.FILES['csv_file']
        fs = FileSystemStorage()
        filename = fs.save(csv_file.name, csv_file)
        file_path = fs.path(filename)
        
        # Read the CSV file
        data = pd.read_csv(file_path)
        data['Message'] = data['Message'].astype(str)
        
        # Split data
        X = data['Message']
        y = data['EncodedClass']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Feature Extraction
        vectorizer = TfidfVectorizer()
        X_train_tfidf = vectorizer.fit_transform(X_train)
        X_test_tfidf = vectorizer.transform(X_test)
        
        # Initialize tokenizer for deep learning models
        tokenizer = Tokenizer()
        tokenizer.fit_on_texts(X_train)
        X_train_seq = tokenizer.texts_to_sequences(X_train)
        X_test_seq = tokenizer.texts_to_sequences(X_test)
        X_train_pad = pad_sequences(X_train_seq, maxlen=100, padding='post')
        X_test_pad = pad_sequences(X_test_seq, maxlen=100, padding='post')
        vocab_size = len(tokenizer.word_index) + 1

        # Algorithms and Accuracies
        results = []

        # SVM
        svm_model = SVC()
        svm_model.fit(X_train_tfidf, y_train)
        svm_pred = svm_model.predict(X_test_tfidf)
        results.append({'Model': 'SVM', 'Accuracy': accuracy_score(y_test, svm_pred)})

        # Random Forest
        rf_model = RandomForestClassifier()
        rf_model.fit(X_train_tfidf, y_train)
        rf_pred = rf_model.predict(X_test_tfidf)
        results.append({'Model': 'Random Forest', 'Accuracy': accuracy_score(y_test, rf_pred)})

        # LSTM+CNN Hybrid
        hybrid_model = Sequential([
            Embedding(input_dim=vocab_size, output_dim=128, input_length=100),
            LSTM(128, return_sequences=True),
            Conv1D(filters=64, kernel_size=3, activation='relu'),
            MaxPooling1D(pool_size=2),
            GlobalMaxPooling1D(),
            Dense(64, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        hybrid_model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        hybrid_model.fit(X_train_pad, y_train, validation_data=(X_test_pad, y_test), epochs=5, batch_size=32, verbose=0)
        loss, accuracy = hybrid_model.evaluate(X_test_pad, y_test, verbose=0)
        results.append({'Model': 'LSTM+CNN Hybrid', 'Accuracy': accuracy})
        
        # Delete uploaded file after processing
        fs.delete(filename)

        # Pass results to template
        return render(request, 'Admin/adminaccuracy.html', {'results': results})

    return render(request, 'Admin/adminaccuracy.html')

def admindisplaypredictions(request):
    # Fetch all Prediction objects
    predictions = Prediction.objects.all().order_by('-created_at')
    
    # Paginate with 10 objects per page
    paginator = Paginator(predictions, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'Admin/admindisplaypredictions.html', {'page_obj': page_obj})
