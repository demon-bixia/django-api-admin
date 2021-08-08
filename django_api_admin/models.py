"""
    Test Models
"""
from django.db import models
from django.urls import reverse


class Author(models.Model):
    age_choices = ((60, 'senior'), (1, 'baby'), (2, 'also a baby'))
    name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, choices=age_choices)
    is_vip = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('author-detail', kwargs={'pk': self.pk})
