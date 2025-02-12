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
    path('', views.index, name='home'),
    path('buy/<cat_id>', views.buy, name='buy'),
    path('verify/', views.verify, name='verify'),
    path('config/', views.stripe_config),
    path('create-checkout-session/', views.create_checkout_session),
    path('payment_success/', views.payment_success, name='payment-success'),
    path('payment_cancelled/', views.CancelledView.as_view()),
    path('accounts/login/', login_page, name='login_page'),
    path('accounts/register/', register_page, name='register'),
    path('accounts/logout/', views.logout_page, name='logout'),
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/add/<int:cat_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:cat_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('administration/new/', views.new_cat, name='new_cat'),
    path('administration/manage/', views.manage_cats, name='manage_cats'),
    path('accounts/orders/', views.orders, name='orders'),
    path('administration/edit/<int:cat_id>/', views.edit_cat, name='edit_cat'),
    path('administration/delete_cat/<int:cat_id>/', views.delete_cat, name='delete'),
    path('switch/', views.switch_sections, name='switch_sections'),
    path('cats/', views.all_cats, name='cats'),
    path('mass_edit_cats/', views.mass_edit_cats, name='mass_edit_cats'),
    path('webhook/', views.stripe_webhook, name='stripe-webhook'),
    path('verified/<order_id>/<inquiry_id>', views.verified, name='verified'),
    path('generate_cat_pdf/<int:cat_id>/', views.generate_cat_pdf, name='generate_cat_pdf'),
]