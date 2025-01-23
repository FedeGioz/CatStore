import stripe
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from django.conf import settings
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import *

from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView


def index(request):
    return render(request, 'index.html')

def buy(request, cat_id=-1):
    if cat_id == -1:
        return render(request, 'error.html', {'message': 'No cat selected'})

    # cat = get_object_or_404(Cat, pk=cat_id)



    #return render(request, 'buy.html', {'cat': cat})

    # Sample data because DB is not yet implemented
    return render(request, 'buy.html', {'cat': {'id': 1, 'name': 'Urur', 'age': 98, 'color': 'Rosa', 'breed': 'Sphynx', 'price': 1000, 'image_url': 'https://i.pinimg.com/736x/8f/ab/45/8fab45c0d2f8173ac047119d57b71ef6.jpg', 'description': 'Chi mai vorrebbe sto gatto?'}})

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
    # Check if the HTTP request method is POST (form submission)
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if a user with the provided username exists
        if not User.objects.filter(username=username).exists():
            # Display an error message if the username does not exist
            messages.error(request, 'Invalid Username')
            return redirect('/login/')

        # Authenticate the user with the provided username and password
        user = authenticate(username=username, password=password)

        if user is None:
            # Display an error message if authentication fails (invalid password)
            messages.error(request, "Invalid Password")
            return redirect('/login/')
        else:
            # Log in the user and redirect to the home page upon successful login
            login(request, user)
            return redirect('/')

    # Render the login page template (GET request)
    return render(request, 'login.html')


def logout_page(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            logout(request)
            return render(request, 'logout_page.html')

    return redirect('/')


def register_page(request):
    # Check if the HTTP request method is POST (form submission)
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if a user with the provided username already exists
        user = User.objects.filter(username=username)

        if user.exists():
            # Display an information message if the username is taken
            messages.info(request, "Username already taken!")
            return redirect('/register/')

        # Create a new User object with the provided information
        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            username=username
        )

        # Set the user's password and save the user object
        user.set_password(password)
        user.save()

        # Display an information message indicating successful account creation
        messages.info(request, "Account created Successfully!")
        return redirect('/register/')

    # Render the registration page template (GET request)
    return render(request, 'register.html')

def wishlist(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            cat_id = request.POST.get('cat_id')
            return render(request, 'wishlist.html')

class SuccessView(TemplateView):
    template_name = 'payment_success.html'


class CancelledView(TemplateView):
    template_name = 'payment_cancelled.html'