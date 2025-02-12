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

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('pending_verification', 'Pending Verification'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cat_id = models.IntegerField()
    stripe_session_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    persona_inquiry_id = models.CharField(max_length=255, blank=True, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class PurchasedCat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cat_id = models.IntegerField()  # ID from external API
    purchase_date = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    documents = models.JSONField(default=dict)  # Store generated documents

    class Meta:
        unique_together = [['user', 'cat_id']]