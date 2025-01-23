from django.contrib import admin
from django.urls import path, include
from CatStore import views
from CatStore.views import login_page, register_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('buy/<cat_id>', views.buy, name='buy'),
    path('verify/', views.verify, name='verify'),
    path('config/', views.stripe_config),
    path('create-checkout-session/', views.create_checkout_session),
    path('payment_success/', views.SuccessView.as_view()),
    path('payment_cancelled/', views.CancelledView.as_view()),
    path('accounts/login/', login_page, name='login_page'),
    path('accounts/register/', register_page, name='register'),
    path('logout/', views.logout_page, name='logout'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('new_cat/', views.new_cat, name='new_cat'),
    path('manage_cats/', views.manage_cats, name='manage_cats'),
]