# my_new_django_project/mysite/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    # Redirect the root URL (http://127.0.0.1:8000/) to your image processing page
    path('', RedirectView.as_view(url='myapp/process-image/', permanent=False), name='index'),

    path('admin/', admin.site.urls),

    # Include your 'myapp' URLs under the 'myapp/' prefix
    path('myapp/', include('myapp.urls')),
]

# Serve media and static files ONLY in DEBUG mode (for development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
