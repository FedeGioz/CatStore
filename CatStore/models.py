from enum import Enum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404, redirect


class Cat(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    color = models.CharField(max_length=50)
    breed = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField()
    description = models.TextField()

    def __init__(self, name, age, color, breed, price, image_url, description, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.age = age
        self.color = color
        self.breed = breed
        self.price = price
        self.image_url = image_url
        self.description = description

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not value:
            raise ValueError("Name cannot be null")
        self._name = value

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        self._age = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

    @property
    def breed(self):
        return self._breed

    @breed.setter
    def breed(self, value):
        self._breed = value

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        self._price = value

    @property
    def image_url(self):
        return self._image_url

    @image_url.setter
    def image_url(self, value):
        self._image_url = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value


class Color(Enum):
    UNDEFINED = 0
    BLACK = 1
    WHITE = 2
    BROWN = 3
    GRAY = 4
    ORANGE = 5
    YELLOW = 6
    MIXED = 6


class Wishlist(models.Model):
    cat = models.ForeignKey('Cat', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username}'s wishlist - Cat ID: {self.cat.id}"

    @login_required
    def add_to_wishlist(request, cat_id):
        cat = get_object_or_404(Cat, id=cat_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user, cat=cat)
        if created:
            messages.success(request, f"{cat.name} has been added to your wishlist.")
        else:
            messages.info(request, f"{cat.name} is already in your wishlist.")
        return redirect('/wishlist/')