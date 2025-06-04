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
from .models import TestRunReport # Added for TestRunReport
# from django.shortcuts import render # render is already imported via the first line
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
        
        # TODO: Implement evaluation against a pre-trained model
        
        # Delete uploaded file after processing
        fs.delete(filename)

        # Pass results to template (results will be empty for now)
        return render(request, 'Admin/adminaccuracy.html', {'results': []})

    return render(request, 'Admin/adminaccuracy.html')

def admindisplaypredictions(request):
    # Fetch all Prediction objects
    predictions = Prediction.objects.all().order_by('-created_at')
    
    # Paginate with 10 objects per page
    paginator = Paginator(predictions, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'Admin/admindisplaypredictions.html', {'page_obj': page_obj})

def view_test_report(request):
    latest_report = TestRunReport.objects.order_by('-run_at').first()
    # Or: latest_report = TestRunReport.objects.latest('run_at')
    # .first() is safer if the table might be empty.

    context = {
        'report': latest_report,
    }
    return render(request, 'Admin/test_report.html', context)
