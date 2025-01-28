from django.contrib import admin
from django.contrib.auth.models import User, Group, Permission
from django.urls import path, include
from CatStore import views
from CatStore.views import login_page, register_page
from CatStore.views import login_page, register_page

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(username="admin", email="admin@admin.com", password="Admin123!")
    group = Group.objects.get_or_create(name='admin')
    # add Catstore | cat | Can add cat permission to the group
    group[0].permissions.add(Permission.objects.get(name='Can add cat'))
    group[0].permissions.add(Permission.objects.get(name='Can change cat'))
    group[0].permissions.add(Permission.objects.get(name='Can delete cat'))
    group[0].permissions.add(Permission.objects.get(name='Can view cat'))

    user_group = Group.objects.get_or_create(name='user')
    group[0].permissions.add(Permission.objects.get(name='Can view cat'))
    group[0].permissions.add(Permission.objects.get(name='Can view wishlist'))


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
    path('accounts/logout/', views.logout_page, name='logout'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('administration/new/', views.new_cat, name='new_cat'),
    path('administration/manage/', views.manage_cats, name='manage_cats'),
    path('accounts/orders/', views.orders, name='orders'),
    path('administration/edit/<cat_id>', views.edit_cat, name='edit_cat'),
    path('administration/delete/<cat_id>', views.delete_cat, name='delete_cat'),
    path('switch/', views.switch_sections, name='switch_sections'),
]