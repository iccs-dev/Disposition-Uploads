from django.urls import path
from .views import upload_file
from .views import upload_file, user_login, user_logout

urlpatterns = [
    path('upload/', upload_file, name='upload_file'),
    path('login/', user_login, name='login'),
    path('', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
]
