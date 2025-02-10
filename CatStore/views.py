import base64
import random
import requests
import stripe
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.views.generic import TemplateView
from django.conf import settings
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import *


def index(request):
    response = requests.get('http://127.0.0.1:9000/')
    if response.status_code == 200:
        cats = response.json()
        featured_cats = random.sample(cats, min(len(cats), 3))
    else:
        print("Failed to fetch cats")
        featured_cats = []
    return render(request, 'index.html', {'featured_cats': featured_cats})

def all_cats(request):
    response = requests.get('http://127.0.0.1:9000/')
    if response.status_code == 200:
        all_cats = response.json()
    else:
        print("Failed to fetch cats")
        all_cats = []

    # Get sorting and filtering parameters
    sort_by = request.GET.get('sort_by', 'id')
    name_filter = request.GET.get('name', '')
    color_filter = request.GET.get('color', '')
    min_age = request.GET.get('min_age', '0')
    max_age = request.GET.get('max_age', '100')
    min_price = request.GET.get('min_price', '0')
    max_price = request.GET.get('max_price', '10000')
    breed_filter = request.GET.get('breed', '')

    # Convert parameters to appropriate types
    try:
        min_age = int(min_age) if min_age else 0
        max_age = int(max_age) if max_age else 100
        min_price = int(min_price) if min_price else 0
        max_price = int(max_price) if max_price else 10000
    except ValueError:
        messages.error(request, 'Invalid filter values')
        return render(request, 'all_cats.html', {'all_cats': []})

    # Apply filters
    filtered_cats = [
        cat for cat in all_cats
        if ((not name_filter or name_filter.lower() in cat['name'].lower()) and
            (not color_filter or color_filter.lower() in cat['color'].lower()) and
            min_age <= cat['age'] <= max_age and
            min_price <= cat['price'] <= max_price and
            (not breed_filter or breed_filter.lower() in cat['breed'].lower()))
    ]

    # Apply sorting
    reverse = sort_by.startswith('-')
    sort_key = sort_by.lstrip('-')
    filtered_cats.sort(key=lambda x: x[sort_key], reverse=reverse)

    return render(request, 'all_cats.html', {'all_cats': filtered_cats})

def buy(request, cat_id=-1):
    if cat_id == -1:
        return render(request, 'error.html', {'message': 'No cat selected'})

    response = requests.get(f'http://127.0.0.1:9000/{cat_id}')
    if response.status_code == 200:
        cat = response.json()
        return render(request, 'buy.html', {'cat': cat})
    else:
        return render(request, 'error.html', {'message': 'Cat not found'})

def verify(request):
    return render(request, 'verify.html')

@csrf_exempt
def stripe_config(request):
    if request.method == 'GET':
        stripe_config = {'publicKey': settings.STRIPE_PUBLISHABLE_KEY}
        return JsonResponse(stripe_config, safe=False)

@csrf_exempt
def create_checkout_session(request):
    if request.method == 'GET':
        domain_url = 'http://127.0.0.1:8000/'
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            checkout_session = stripe.checkout.Session.create(
                success_url=domain_url + 'payment_success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=domain_url + 'payment_cancelled/',
                payment_method_types=['card'],
                mode='payment',
                line_items=[
                    {
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': 'Cat',
                            },
                            'unit_amount': 1000,
                        },
                        'quantity': 1,
                    }
                ]
            )
            return JsonResponse({'sessionId': checkout_session['id']})
        except Exception as e:
            return JsonResponse({'error': str(e)})


def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Ensure the 'user' group exists
        group, created = Group.objects.get_or_create(name='user')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'You have successfully logged in.')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
            return redirect('login')

    return render(request, 'login.html')

def logout_page(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            logout(request)
            return render(request, 'logout_page.html')

    return redirect('/')

def register_page(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.info(request, "Username already taken!")
            return redirect('/accounts/register/')

        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            username=username
        )

        user.set_password(password)
        user.save()

        messages.info(request, "Account created Successfully!")
        return redirect('/accounts/register/')

    return render(request, 'register.html')

def wishlist(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            cat_id = request.POST.get('cat_id')
            user = request.user
            Wishlist.objects.filter(user=user, cat=1)
            return render(request, 'wishlist.html')
        else:
            return render(request, 'wishlist.html')
    else:
        return redirect('/accounts/login/')

def is_staff(user):
    return user.groups.filter(name='Administrator').exists()

def new_cat(request):
    if not request.user.is_authenticated:
        return render(request, 'error.html', {'message': 'You are not logged in!'})

    if not request.user.groups.filter(name='admin').exists():
        return render(request, 'error.html', {'message': 'You aren\'t allowed to create a new cat!'})

    if request.method == "POST":
        image = request.FILES.get('image')
        if image:
            image_data = base64.b64encode(image.read()).decode('utf-8')
            url = "https://api.imgbb.com/1/upload"
            payload = {
                'key': 'bdab6f6c1bc67079265851991fe0e292',
                'image': image_data
            }
            response = requests.post(url, data=payload)
            print(response.json())
            if response.status_code == 200:
                image_url = response.json()['data']['url']
            else:
                messages.error(request, 'Failed to upload image')
                return redirect('/administration/new/')

            data = {
                'id': 0, # Solo per far workare il modello dell'API, in realta' non modifica
                'name': request.POST.get('name'),
                'age': request.POST.get('age'),
                'color': request.POST.get('color'),
                'breed': request.POST.get('breed'),
                'price': int(request.POST.get('price')),
                'description': request.POST.get('description'),
                'image_url': image_url
            }

            headers = {'Authorization': 'Bearer i$&$aDz,9Z:b}n{2ZnnBj1r}-B{_2SX)rAjye3F;}&X;pw0zgdkjFCz!(+/2*P66'}
            print(data)
            response = requests.post('http://127.0.0.1:9000/', json=data, headers=headers)
            print(response.json())
            if response.status_code == 200:
                return redirect('/administration/manage/')
            else:
                messages.error(request, 'Failed to create cat')
                return redirect('/administration/new/')
    return render(request, 'admin/new_cat.html')

def manage_cats(request):
    response = requests.get('http://localhost:9000/')
    if response.status_code == 200:
        all_cats = response.json()
    else:
        print("Failed to fetch cats")
        all_cats = []

    # Get sorting and filtering parameters
    sort_by = request.GET.get('sort_by', 'id')
    name_filter = request.GET.get('name', '')
    color_filter = request.GET.get('color', '')
    min_age = request.GET.get('min_age', '0')
    max_age = request.GET.get('max_age', '100')
    min_price = request.GET.get('min_price', '0')
    max_price = request.GET.get('max_price', '10000')
    breed_filter = request.GET.get('breed', '')

    # Convert parameters to appropriate types
    try:
        min_age = int(min_age) if min_age else 0
        max_age = int(max_age) if max_age else 100
        min_price = int(min_price) if min_price else 0
        max_price = int(max_price) if max_price else 10000
    except ValueError:
        messages.error(request, 'Invalid filter values')
        return render(request, 'admin/manage_cats.html', {'cats': []})

    # Apply filters
    filtered_cats = [
        cat for cat in all_cats
        if ((not name_filter or name_filter.lower() in cat['name'].lower()) and
            (not color_filter or color_filter.lower() in cat['color'].lower()) and
            min_age <= cat['age'] <= max_age and
            min_price <= cat['price'] <= max_price and
            (not breed_filter or breed_filter.lower() in cat['breed'].lower()))
    ]

    # Apply sorting
    reverse = sort_by.startswith('-')
    sort_key = sort_by.lstrip('-')
    filtered_cats.sort(key=lambda x: x[sort_key], reverse=reverse)

    return render(request, 'admin/manage_cats.html', {'cats': filtered_cats})

def edit_cat(request, cat_id):
    if not request.user.groups.filter(name='admin').exists():
        return render(request, 'error.html', {'message': 'You aren\'t allowed to edit a cat!'})

    response = requests.get(f'http://127.0.0.1:9000/{cat_id}')
    if response.status_code == 200:
        cat = response.json()
    else:
        return render(request, 'error.html', {'message': 'Cat not found'})

    if request.method == "POST":
        data = {
            'id': cat_id, # Solo per far workare il modello dell'API, in realta' non modifica
            'name': request.POST.get('name'),
            'age': request.POST.get('age'),
            'color': request.POST.get('color'),
            'breed': request.POST.get('breed'),
            'price': request.POST.get('price'),
            'description': request.POST.get('description'),
            'image_url': request.POST.get('image_url')
        }

        print(data)

        headers = {'Authorization': 'Bearer i$&$aDz,9Z:b}n{2ZnnBj1r}-B{_2SX)rAjye3F;}&X;pw0zgdkjFCz!(+/2*P66'}
        response = requests.put(f'http://127.0.0.1:9000/{cat_id}', json=data, headers=headers)
        if response.status_code == 200:
            return redirect('/administration/manage/')
        else:
            messages.error(request, 'Failed to update cat')
            return redirect(f'/administration/edit/{cat_id}')

    return render(request, 'admin/edit_cat.html', {'cat': cat})

def orders(request):
    return render(request, 'user/orders.html')

def delete_cat(request, cat_id=-1):
    if not request.user.groups.filter(name='admin').exists():
        return render(request, 'error.html', {'message': 'You aren\'t allowed to delete a cat!'})

    headers = {'Authorization': 'Bearer i$&$aDz,9Z:b}n{2ZnnBj1r}-B{_2SX)rAjye3F;}&X;pw0zgdkjFCz!(+/2*P66'}
    response = requests.delete(f'http://127.0.0.1:9000/{cat_id}', headers=headers)
    if response.status_code == 200:
        return redirect('/administration/manage/')
    else:
        messages.error(request, 'Failed to delete cat')
        return redirect('/administration/manage/')

def switch_sections(request):
    if request.user.groups.filter(name='admin').exists():
        return redirect('/administration/manage/')
    elif request.user.groups.filter(name='user').exists():
        return redirect('/accounts/orders')
    else:
        return redirect('/accounts/orders')


@login_required
def add_to_wishlist(request, cat_id):
    try:
        print(f"Attempting to add cat {cat_id}")  # Debug log

        # Verify cat exists in remote API
        response = requests.get(f'http://127.0.0.1:9000/{cat_id}')
        response.raise_for_status()
        print(f"API response valid for cat {cat_id}")  # Debug log

        # Create wishlist entry
        obj, created = Wishlist.objects.get_or_create(
            user=request.user,
            cat_id=cat_id
        )

        if created:
            print(f"Created new entry for cat {cat_id}")  # Debug log
            messages.success(request, 'Added to wishlist!')
        else:
            print(f"Cat {cat_id} already exists")  # Debug log
            messages.info(request, 'Already in wishlist')

    except requests.HTTPError as e:
        print(f"API error for cat {cat_id}: {e}")  # Debug log
        messages.error(request, f'Cat {cat_id} not found')
    except Exception as e:
        print(f"General error for cat {cat_id}: {e}")  # Debug log
        messages.error(request, f'Error: {str(e)}')

    return redirect('view_wishlist')

@login_required
def remove_from_wishlist(request, cat_id):
    try:
        Wishlist.objects.get(cat_id=cat_id, user=request.user).delete()
        messages.success(request, 'Removed from wishlist')
    except Wishlist.DoesNotExist:
        messages.error(request, 'Item not found in wishlist')
    return redirect('view_wishlist')


@login_required
def view_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    valid_cats = []

    # Get sorting and filtering parameters
    sort_by = request.GET.get('sort_by', 'id')
    name_filter = request.GET.get('name', '')
    color_filter = request.GET.get('color', '')
    min_age = request.GET.get('min_age', '0')
    max_age = request.GET.get('max_age', '100')
    min_price = request.GET.get('min_price', '0')
    max_price = request.GET.get('max_price', '10000')
    breed_filter = request.GET.get('breed', '')

    # Convert parameters to appropriate types
    try:
        min_age = int(min_age) if min_age else 0
        max_age = int(max_age) if max_age else 100
        min_price = int(min_price) if min_price else 0
        max_price = int(max_price) if max_price else 10000
    except ValueError:
        messages.error(request, 'Invalid filter values')
        return render(request, 'wishlist.html', {'cats': []})

    for item in wishlist_items:
        try:
            response = requests.get(f'http://127.0.0.1:9000/{item.cat_id}')
            response.raise_for_status()
            cat = response.json()
            cat['local_id'] = item.id  # For removal

            # Apply filters
            if ((not name_filter or name_filter.lower() in cat['name'].lower()) and
                (not color_filter or color_filter.lower() in cat['color'].lower()) and
                min_age <= cat['age'] <= max_age and
                min_price <= cat['price'] <= max_price and
                (not breed_filter or breed_filter.lower() in cat['breed'].lower())):
                valid_cats.append(cat)
        except requests.HTTPError:
            # Auto-remove invalid entries
            item.delete()

    # Apply sorting
    reverse = sort_by.startswith('-')
    sort_key = sort_by.lstrip('-')
    valid_cats.sort(key=lambda x: x[sort_key], reverse=reverse)

    return render(request, 'wishlist.html', {'cats': valid_cats})

def mass_edit_cats(request):
    if request.method == 'POST':
        headers = {'Authorization': 'Bearer i$&$aDz,9Z:b}n{2ZnnBj1r}-B{_2SX)rAjye3F;}&X;pw0zgdkjFCz!(+/2*P66'}
        cat_ids = request.POST.getlist('cat_ids')
        new_price = request.POST.get('new_price')
        delete_selected = request.POST.get('delete_selected')

        for cat_id in cat_ids:
            if delete_selected:
                requests.delete(f'http://localhost:9000/{cat_id}', headers=headers)
            else:
                response = requests.get(f'http://localhost:9000/{cat_id}')
                if response.status_code == 200:
                    cat = response.json()
                    if new_price:
                        cat['price'] = new_price

                    requests.put(f'http://localhost:9000/{cat_id}', json=cat, headers=headers)

        return redirect('manage_cats')
    else:
        return redirect('manage_cats')

class SuccessView(TemplateView):
    template_name = 'payment_success.html'

class CancelledView(TemplateView):
    template_name = 'payment_cancelled.html'