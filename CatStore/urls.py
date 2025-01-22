from django.contrib import admin
from django.urls import path, include
from CatStore import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('buy/<cat_id>', views.buy, name='buy'),
    path('verify/', views.verify, name='verify'),
    path('config/', views.stripe_config),
    path('create-checkout-session/', views.create_checkout_session),
    path('payment_success/', views.SuccessView.as_view()), # new
    path('payment_cancelled/', views.CancelledView.as_view()), # new
]