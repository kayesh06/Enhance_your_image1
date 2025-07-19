# my_new_django_project/myapp/urls.py

from django.urls import path
from . import views # Correct way to import views from the same app

# Define the application namespace. This is crucial for {% url %} template tag.
app_name = 'myapp'

urlpatterns =[
    path('process-image/', views.image_processing_view, name='image_processing'),
]