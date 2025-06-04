from django.urls import path
# Explicitly import views to make it clear which ones are used
from Admins.views import adminhome, admin_update_userstatus, adminaccuracy, admingraphs, admindisplaypredictions, view_test_report

urlpatterns = [
    path('adminhome/', adminhome, name='adminhome'),
    path('admin_update_userstatus/<int:user_id>/', admin_update_userstatus, name='admin_update_userstatus'),
    path('adminaccuracy/', adminaccuracy, name='adminaccuracy'),
    path('admingraphs/', admingraphs, name='admingraphs'),
    path('admindisplaypredictions/',admindisplaypredictions, name='admindisplaypredictions'),
    path('test-report/', view_test_report, name='view_test_report'), # New URL
]