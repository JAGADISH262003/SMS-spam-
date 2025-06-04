import pandas as pd
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.text import Tokenizer
import joblib
import os

# Create model directory if it doesn't exist
os.makedirs('model', exist_ok=True)

# Load Dataset
data = pd.read_csv("model/dataset.csv")
data['Message'] = data['Message'].astype(str)

# Split the dataset (consistent with User/views.py)
X = data['Message']
y = data['EncodedClass']
X_train, _, _, _ = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Tokenize and fit
tokenizer = Tokenizer()
tokenizer.fit_on_texts(X_train)

# Save the tokenizer
joblib.dump(tokenizer, "model/tokenizer.joblib")
print("Tokenizer saved to model/tokenizer.joblib")
