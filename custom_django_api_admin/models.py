from django.db import models

parent_choices = ((True, 'the person is a parent'), (False, 'the person is not a parent'))


class Person(models.Model):
    name = models.CharField(max_length=50)
    is_parent = models.BooleanField(choices=parent_choices)
    age = models.IntegerField()

    def __str__(self):
        return self.name


class Job(models.Model):
    title = models.CharField(max_length=50)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)

    def __str__(self):
        return self.title
