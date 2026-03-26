from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('conductores/', include('conductores.urls')),
    path('', lambda req: redirect('conductores:lista')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
