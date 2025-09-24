from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/content/', include('content.urls')),
    path('api/ads/', include('ads.urls')),
    path('api/administrator/', include('administrator.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customization
admin.site.site_header = 'Classified Ads Admin'
admin.site.site_title = 'Classified Ads Admin Portal'
admin.site.index_title = 'Welcome to Classified Ads Administration'