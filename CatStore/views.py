import base64
import logging
import random
import requests
import stripe
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.views.generic import TemplateView
from django.conf import settings
from django.http.response import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import *
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def index(request):
    response = requests.get('http://127.0.0.1:9000/')
    if response.status_code == 200:
        cats = response.json()
        sellable_cats = [cat for cat in cats if cat.get('sellable', True)]
        featured_cats = random.sample(sellable_cats, min(len(sellable_cats), 3))
    else:
        print("Failed to fetch cats")
        featured_cats = []
    return render(request, 'index.html', {'featured_cats': featured_cats})

def all_cats(request):
    response = requests.get('http://127.0.0.1:9000/')
    if response.status_code == 200:
        all_cats = response.json()
        sellable_cats = [cat for cat in all_cats if cat.get('sellable', True)]
    else:
        print("Failed to fetch cats")
        sellable_cats = []

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
        cat for cat in sellable_cats
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
        cat_id = request.GET.get('cat_id')
        if not cat_id:
            logging.error('Cat ID not provided')
            return JsonResponse({'error': 'Cat ID not provided'}, status=400)

        response = requests.get(f'http://127.0.0.1:9000/{cat_id}')
        if response.status_code != 200:
            logging.error(f'Cat not found: {response.status_code}')
            return JsonResponse({'error': 'Cat not found'}, status=404)

        cat = response.json()
        stripe_product_id = cat.get('stripe_product')
        price = cat.get('price')  # Ensure this field exists in the API response

        if not stripe_product_id or not price:
            logging.error('Missing Stripe product ID or price')
            return JsonResponse({'error': 'Product configuration error'}, status=400)

        domain_url = 'http://127.0.0.1:8100/'
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
                            'product': stripe_product_id,
                            'unit_amount': int(price * 100),  # Convert EUR to cents
                        },
                        'quantity': 1,
                    }
                ],
                metadata={'cat_id': cat_id},  # Add metadata
                payment_intent_data={
                    'metadata': {'cat_id': cat_id}  # Also store in payment intent
                }
            )

            # Create preliminary order record
            if request.user.is_authenticated:
                Order.objects.create(
                    user=request.user,
                    cat_id=cat_id,
                    stripe_session_id=checkout_session.id,
                    amount=price,
                    status='pending'
                )
            return JsonResponse({'sessionId': checkout_session['id']})
        except Exception as e:
            logging.error(f'Error creating checkout session: {str(e)}')
            return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    # Handle successful payment
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_successful_payment(session)

    return HttpResponse(status=200)


def handle_successful_payment(session):
    try:
        order = Order.objects.get(stripe_session_id=session.id)
        order.status = 'pending_verification'
        order.save()
    except Order.DoesNotExist:
        pass

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

@staff_member_required
def new_cat(request):
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
                'image_url': image_url,
                'sellable': True
            }

            stripe.api_key = settings.STRIPE_SECRET_KEY
            product = stripe.Product.create(
                name=data['name'],
                default_price_data={
                    "unit_amount": str(data['price'] * 100),
                    "currency": "eur"
                },
                expand=["default_price"],
                images=[image_url]
            )

            data['stripe_product'] = product.id

            print(data)

            headers = {'Authorization': 'Bearer i$&$aDz,9Z:b}n{2ZnnBj1r}-B{_2SX)rAjye3F;}&X;pw0zgdkjFCz!(+/2*P66'}
            response = requests.post('http://127.0.0.1:9000/', json=data, headers=headers)
            if response.status_code == 200:
                return redirect('/administration/manage/')
            else:
                messages.error(request, 'Failed to create cat')
                return redirect('/administration/new/')
    return render(request, 'admin/new_cat.html')

@staff_member_required
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

@staff_member_required
def edit_cat(request, cat_id):
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


@login_required
def orders(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    order_details = []

    for order in orders:
        try:
            response = requests.get(f'http://127.0.0.1:9000/{order.cat_id}')
            if response.status_code == 200:
                cat_data = response.json()
                order_details.append({
                    'order': order,
                    'cat': cat_data,
                    'receipt_url': stripe.checkout.Session.retrieve(
                        order.stripe_session_id
                    ).get('charges', {}).get('data', [{}])[0].get('receipt_url')
                })
            else:
                order_details.append({
                    'order': order,
                    'error': 'Cat information unavailable'
                })
        except requests.RequestException:
            order_details.append({
                'order': order,
                'error': 'Cat information unavailable'
            })

    return render(request, 'user/orders.html', {'orders': order_details})

@staff_member_required
def delete_cat(request, cat_id=-1):
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

@staff_member_required
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

@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    order = Order.objects.get(stripe_session_id=session_id)

    return render(request,'payment_success.html', {'userId': request.user.id, 'orderId': order.id})

@login_required
@csrf_exempt
def verified(request, order_id, inquiry_id):
    if request.method == "POST":
        url = f"https://api.withpersona.com/api/v1/inquiries/{inquiry_id}"

        headers = {
            'Persona-Version': '2023-01-05',
            'accept': 'application/json',
            'authorization': 'Bearer persona_sandbox_de565a8c-13df-40a7-8574-7ef5780fe016',
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch inquiry: {e}")
            return JsonResponse({'status': 'error', 'message': 'Failed to fetch inquiry'}, status=500)

        data = response.json()

        if data['data']['attributes']['status'] == "approved":
            try:
                order = Order.objects.get(id=order_id)
                order.status = 'completed'
                order.save()

                # Delete the cat from the database
                cat_id = order.cat_id
                headers = {'Authorization': 'Bearer i$&$aDz,9Z:b}n{2ZnnBj1r}-B{_2SX)rAjye3F;}&X;pw0zgdkjFCz!(+/2*P66'}
                make_unsellable = requests.patch(f'http://127.0.0.1:9000/{cat_id}', headers=headers)
                if make_unsellable.status_code != 200:
                    logging.error(f"Failed to delete cat: {make_unsellable.status_code}")
                    return JsonResponse({'status': 'error', 'message': 'Failed to delete cat'}, status=500)

                return redirect('/accounts/orders/')
            except Order.DoesNotExist:
                logging.error("Order not found")
                return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)
        else:
            logging.error("Inquiry not approved")
            return JsonResponse({'status': 'error', 'message': 'Inquiry not approved'}, status=400)
    logging.error("Invalid method")
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@login_required
def generate_cat_pdf(request, cat_id):
    # Fetch cat details from the database or API
    response = requests.get(f'http://127.0.0.1:9000/{cat_id}')
    if response.status_code != 200:
        return HttpResponse('Cat not found', status=404)

    cat = response.json()

    # Create the PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{cat["name"]}_details.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    p.drawString(100, 750, f"Cat Name: {cat['name']}")
    p.drawString(100, 730, f"Age: {cat['age']}")
    p.drawString(100, 710, f"Breed: {cat['breed']}")
    p.drawString(100, 690, f"Color: {cat['color']}")
    p.drawString(100, 670, f"Price: €{cat['price']}")

    # Draw the cat image
    if cat['image_url']:
        p.drawImage(cat['image_url'], 100, 500, width=200, height=200)

    p.showPage()
    p.save()

    return response

class CancelledView(TemplateView):
    template_name = 'payment_cancelled.html'