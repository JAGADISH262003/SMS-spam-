from django.contrib import admin
from .models import TestRunReport # Add TestRunReport here

# Register your models here.

@admin.register(TestRunReport)
class TestRunReportAdmin(admin.ModelAdmin):
    list_display = ('run_at', 'total_tests', 'passed_tests', 'failed_tests', 'skipped_tests', 'errors', 'was_successful')
    list_filter = ('was_successful', 'run_at')
    readonly_fields = ('run_at', 'total_tests', 'passed_tests', 'failed_tests', 'skipped_tests', 'errors', 'report_output', 'was_successful') # Make all fields read-only in admin

    def has_add_permission(self, request):
        return False # Prevent adding reports manually via admin

    def has_change_permission(self, request, obj=None):
        return False # Prevent changing reports manually via admin (allow view only)

# Ensure other models like Prediction are also registered if they were previously.
# For example, if User.models.Prediction was managed here:
# from User.models import Prediction
# if not admin.site.is_registered(Prediction):
#     admin.site.register(Prediction)
