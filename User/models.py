from django.db import models

# Create your models here.
class Prediction(models.Model):
    user_input = models.TextField()
    result = models.CharField(max_length=10)  # e.g., 'Spam' or 'Ham'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_input[:50]} - {self.result}"