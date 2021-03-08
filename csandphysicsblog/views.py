from django.http.response import HttpResponseRedirect 
from django.shortcuts import redirect, render
from django.http import HttpResponse
from .models import Subject, Detail, Connect, Article
from .forms import Contact

# Create your views here.
def home(request):
    #return HttpResponse("Hello, Welcome to my blog")
    return render(request, 'Home.html')

def topic(request):
    topics = Subject.objects.all()
    context = {'topics': topics}
    return render(request, 'Topic.html',context)

def details(request, topic_id):
    info = Subject.objects.get(id=topic_id)
    entries = info.detail_set.all()
    context = {'info': info, 'entries':entries}
    return render(request, 'Details.html',context)

def description(request, study_id):
    entries = Detail.objects.get(id=study_id)
    context = {'entries':entries}
    return render(request, 'Describe.html',context)

def contact(request):
    if request.method=="POST":
       form = Contact(request.POST)
       if form.is_valid():
            Name = request.POST.get('Name',())
            Email = request.POST.get('Email',())
            Topic = request.POST.get('Topic',())
            Message = request.POST.get('Message',())
            connected = Connect(Name=Name, Email=Email, Topic=Topic, Message=Message)
            connected.save()
            
            return redirect('contact')
    else:
       form = Contact()

    context = {'form':form}
    return render(request, 'ContactUs.html',context)

def about(request):
    return render(request, 'About.html')

def publish(request):
    obj = Article.objects.all()
    context = {'article': obj}
    return render(request, 'Publish.html', context)



   



