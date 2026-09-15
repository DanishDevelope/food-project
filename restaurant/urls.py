from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_redirect, name='home_redirect'),
    path('register/', views.register_view, name='register_url'),
    path('login/', views.login_view, name='login_url'),
    path('logout/', views.logout_view, name='logout_url'),
    
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('customer-dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('seller-dashboard/', views.seller_dashboard, name='seller_dashboard'),
]