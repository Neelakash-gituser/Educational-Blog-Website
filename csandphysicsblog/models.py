from django.db.models.deletion import CASCADE
from django.db.models.fields import DateField
from django.db.models.fields.files import ImageField
from django.db import models
from django.db.models.base import Model

# Create your models here.
class Subject(models.Model):
    Topic = models.CharField(max_length=200, default='')
    
    def __str__(self):
        return self.Topic

class Detail(models.Model):
    Heading = models.ForeignKey(Subject, on_delete=CASCADE)
    Sub_Topic = models.CharField(max_length=200, default='')
    Date_added = DateField()
    Added_by = models.TextField(max_length=2000, default='')
    Content = models.TextField(max_length=20000,default='')
    Image = models.ImageField(blank=True, upload_to='blog_images')                  # blank = True for optional fields .
    Author_pic = models.ImageField(blank=True, upload_to='static/blog_images')

    def __str__(self):
        return "   Subject :  "+self.Sub_Topic+" |  Added By :  "+self.Added_by[: 50]+"..."

class Connect(models.Model):
    Name = models.CharField(max_length=100)
    Email = models.EmailField(max_length=100)
    Topic = models.CharField(max_length=100)
    Message = models.TextField(max_length=500)

    def __str__(self):
        return self.Email+" | "+self.Topic
    
    class Meta:
        db_table="Connect"

class Article(models.Model):
    Author = models.CharField(max_length=100, default='')
    Topic = models.CharField(max_length=100, default='')
    Sub_Topic = models.CharField(max_length=100, default='')
    Matter = models.TextField(max_length=20000, default='')


    def __str__(self):
        return self.Author+" | "+self.Sub_Topic


