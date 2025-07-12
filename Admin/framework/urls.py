"""framework URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
                  # path('admin/', admin.site.urls), # Admin URL is commented out
                  path('', include('app.urls')), # Includes URLs from your 'app'
              ]

# This part is crucial for serving media files during development (when DEBUG is True)
# It maps the MEDIA_URL to the MEDIA_ROOT directory
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Note: In production, you should configure your web server (like Nginx or Apache)
# to serve files from MEDIA_ROOT directly, rather than relying on Django.

