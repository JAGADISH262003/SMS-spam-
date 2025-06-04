from django.db import models
from django.utils import timezone

# Create your models here.

class TestRunReport(models.Model):
    run_at = models.DateTimeField(default=timezone.now)
    total_tests = models.IntegerField(default=0)
    passed_tests = models.IntegerField(default=0)
    failed_tests = models.IntegerField(default=0)
    skipped_tests = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    report_output = models.TextField(blank=True, null=True)
    was_successful = models.BooleanField(default=False)

    def __str__(self):
        return f"Test Run at {self.run_at.strftime('%Y-%m-%d %H:%M:%S')} - {'Success' if self.was_successful else 'Failed'}"

    class Meta:
        ordering = ['-run_at']
