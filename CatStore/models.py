from enum import Enum

from django.db import models
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class Cat(models.Model):
    def __init__(self):
        self.id = 0
        self.name = ""
        self.age = 0
        self.color = ""
        self.breed = ""
        self.price = 0
        self.image_url = ""
        self.description = ""

    @property
    def id(self):
        return self.id

    @id.setter
    def id(self, value):
        self.id = value

    @property
    def name(self):
        return self.name

    @name.setter
    def name(self, value):
        if not value:
            raise ValueError("Name cannot be null")
        self.name = value

    @property
    def age(self):
        return self.age

    @age.setter
    def age(self, value):
        self.age = value

    @property
    def color(self):
        return self.color

    @color.setter
    def color(self, value):
        self.color = value

    @property
    def breed(self):
        return self.breed

    @breed.setter
    def breed(self, value):
        self.breed = value

    @property
    def price(self):
        return self.price

    @price.setter
    def price(self, value):
        self.price = value

    @property
    def image_url(self):
        return self.imageUrl

    @image_url.setter
    def image_url(self, value):
        self.imageUrl = value

    @property
    def description(self):
        return self.description

    @description.setter
    def description(self, value):
        self.description = value


class Color(Enum):
    UNDEFINED = 0
    BLACK = 1
    WHITE = 2
    BROWN = 3
    GRAY = 4
    ORANGE = 5
    YELLOW = 6
    MIXED = 6

class CatSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cat
        fields = "__all__"


class CatCreateAPIView(APIView):
    def get(self, request):
        cats = Cat.objects.filter(available=True)
        serializer = CatSerializer(cats, many=True)
        return Response(serializer.data)
      
      