from django.db import models
class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.FloatField()
    ingredients = models.TextField()

    def __str__(self):
        return self.name

