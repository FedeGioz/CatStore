from enum import Enum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404, redirect


class Cat(models.Model):
    name = models.CharField(max_length=100, default=None)
    age = models.IntegerField(default=0)
    color = models.CharField(max_length=50, default=None)
    breed = models.CharField(max_length=100, default=None)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=1000000)
    image_url = models.URLField(default=None)
    description = models.TextField(default=None)

    def __str__(self):
        return self.name


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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cat_id = models.IntegerField()

    def __str__(self):
        return f"Wishlist item for user {self.user.username} and cat {self.cat_id}"