from django.urls import path
from . import views


urlpatterns = [
    path('create-link/', views.create_link),
    path('pin-check/', views.enter_pin),
    path('pin-check/<pinCode>', views.pin_check),
    path('<awb>', views.direct_link),
]