from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import logout, login, authenticate
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.models import User

import json
import datetime
from .utils import cartData, guestOrder
from .models import *


def register(request):
    data = cartData(request)
    cartItems = data['cartItems']

    if request.method == 'POST':
        username = request.POST.get('username')
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password1')
        if not username:
            messages.error(request, 'Username can\'t be empty.')
        if not name:
            messages.error(request, 'Name can\'t be empty.')
        if not email:
            messages.error(request, 'Email can\'t be empty.')
        if password:
            if password == request.POST.get('password2'):
                try:
                    new_user = User.objects.create_user(username=username, email=email, password=password)
                    Customer.objects.create(user=new_user, name=name, email=email)
                    object = authenticate(request, username=username, password=password)
                    login(request, object)
                    return redirect('store')

                except:
                    messages.error(request, 'Pick another username.')
            else:
                messages.error(request, 'Passwords do not match.')
        else:
            messages.error(request, 'Password can not be empty.')
    return render(request, 'auth/register.html', {'cartItems': cartItems})


def login_view(request):
    data = cartData(request)
    cartItems = data['cartItems']

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            object = authenticate(request, username=username, password=password)
            login(request, object)
            return redirect('store')
        except:
            messages.error(request, 'User or password does not exist.')
    return render(request, 'auth/login.html', {'cartItems': cartItems})


def logout_view(request):
    logout(request)
    response = redirect('store')
    response.delete_cookie('csrftoken')
    # print(request.COOKIES)
    return response


def store(request):
    data = cartData(request)
    cartItems = data['cartItems']
    products = Product.objects.all()

    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/store.html', context)


def cart(request):
    data = cartData(request)
    order = data['order']
    items = data['items']
    cartItems = data['cartItems']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/cart.html', context)


def checkout(request):
    data = cartData(request)
    order = data['order']
    items = data['items']
    cartItems = data['cartItems']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/checkout.html', context)


def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']

    print('Action:', action)
    print('productId:', productId)

    customer = request.user.customer
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)

    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action == 'add':
        orderItem.quantity = (orderItem.quantity + 1)
    elif action == 'remove':
        orderItem.quantity = (orderItem.quantity - 1)

    orderItem.save()

    if orderItem.quantity <= 0:
        orderItem.delete()

    return JsonResponse('Item was added', safe=False)


@csrf_exempt
def processOrder(request):
    # print('Data:', request.body)
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
    else:
        customer, order = guestOrder(request, data)

    total = float(data['form']['total'])
    order.transaction_id = transaction_id
    print(total)

    if total == float(order.get_cart_total):
        order.complete = True
    order.save()

    if order.shipping == True:
        ShippingAddress.objects.get_or_create(
            customer=customer,
            order=order,
            address=data['shipping']['address'],
            city=data['shipping']['city'],
            state=data['shipping']['state'],
            zipcode=data['shipping']['zipcode'],
        )

    return JsonResponse('Payment submitted..', safe=False)
