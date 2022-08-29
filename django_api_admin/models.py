"""Test Models"""
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse

User = get_user_model()


class Publisher(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Author(models.Model):
    age_choices = ((60, 'senior'), (1, 'baby'), (2, 'also a baby'))
    name = models.CharField(max_length=100)
    age = models.IntegerField(choices=age_choices)
    is_vip = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    publisher = models.ManyToManyField(Publisher)
    gender = models.CharField(max_length=20, blank=False, null=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=20, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('author-detail', kwargs={'pk': self.pk})


class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    credits = models.ManyToManyField(Author, related_name='credits')

    def __str__(self):
        return self.title


class GuestEntry(models.Model):
    date_entered = models.DateField()
