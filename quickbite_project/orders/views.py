from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from restaurants.models import MenuItem, Restaurant
from .models import Order, OrderItem
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

def get_coordinates(address):
    #Convert address to coordinates
    try:
        geolocator = Nominatim(user_agent="quickbite_app")
        location = geolocator.geocode(address + ", Bangladesh", timeout=5)
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        pass
    return None


def calculate_delivery_charge(customer_address, restaurant_address):
    customer_coords = get_coordinates(customer_address)
    restaurant_coords = get_coordinates(restaurant_address)

    if customer_coords and restaurant_coords:
        # Get distance in km
        distance_km = geodesic(restaurant_coords, customer_coords).km

        # Charge based on distance
        if distance_km <= 2:
            charge = 30
        elif distance_km <= 5:
            charge = 50
        elif distance_km <= 10:
            charge = 70
        elif distance_km <= 20:
            charge = 100
        else:
            charge = 150

        return charge, round(distance_km, 1)

    # Default (incase can't get location)
    return 50, None

def add_to_cart(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    cart = request.session.get('cart', {})

    cart_restaurant_id = request.session.get('cart_restaurant_id')

    if cart_restaurant_id and int(cart_restaurant_id) != item.restaurant.id:
        cart = {}
        messages.warning(request, '⚠️ Your cart was cleared because you switched restaurants.')

    # This correctly increases quantity instead of adding duplicate
    if str(item_id) in cart:
        cart[str(item_id)]['quantity'] += 1
    else:
        cart[str(item_id)] = {'quantity': 1}

    request.session['cart'] = cart
    request.session['cart_restaurant_id'] = item.restaurant.id

    messages.success(request, f'✅ {item.name} added to cart!')
    return redirect('restaurants:restaurant_detail', pk=item.restaurant.id)
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_restaurant_id = request.session.get('cart_restaurant_id')

    items = []
    total = 0
    restaurant = None

    if cart_restaurant_id:
        try:
            restaurant = Restaurant.objects.get(id=cart_restaurant_id)
        except Restaurant.DoesNotExist:
            pass

    for item_id, item_data in cart.items():
        try:
            menu_item = MenuItem.objects.get(id=item_id)
            quantity = item_data['quantity']
            subtotal = menu_item.price * quantity
            total += subtotal
            items.append({
                'item': menu_item,
                'quantity': quantity,
                'subtotal': subtotal,
            })
        except MenuItem.DoesNotExist:
            pass

    return render(request, 'orders/cart.html', {
        'items': items,
        'total': total,
        'restaurant': restaurant,
    })


def remove_from_cart(request, item_id):
    cart = request.session.get('cart', {})
    cart.pop(str(item_id), None)
    request.session['cart'] = cart

    if not cart:
        request.session['cart_restaurant_id'] = None

    messages.success(request, '🗑️ Item removed from cart.')
    return redirect('orders:view_cart')





@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    cart_restaurant_id = request.session.get('cart_restaurant_id')

    if not cart:
        messages.warning(request, 'Your cart is empty!')
        return redirect('home')

    restaurant = get_object_or_404(Restaurant, id=cart_restaurant_id)

    items = []
    subtotal = 0
    for item_id, item_data in cart.items():
        menu_item = get_object_or_404(MenuItem, id=item_id)
        quantity = item_data['quantity']
        item_subtotal = menu_item.price * quantity
        subtotal += item_subtotal
        items.append({
            'item': menu_item,
            'quantity': quantity,
            'subtotal': item_subtotal,
        })

    delivery_charge = 30

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        payment_method = request.POST.get('payment_method', 'COD')

        if not phone or not address:
            messages.error(request, '❌ Phone and address are required!')
            return render(request, 'orders/checkout.html', {
                'items': items,
                'subtotal': subtotal,
                'delivery_charge': delivery_charge,
                'total': subtotal + delivery_charge,
                'restaurant': restaurant,
                'user': request.user,
            })

        if len(phone) < 11:
            messages.error(request, '❌ Please enter a valid phone number!')
            return render(request, 'orders/checkout.html', {
                'items': items,
                'subtotal': subtotal,
                'delivery_charge': delivery_charge,
                'total': subtotal + delivery_charge,
                'restaurant': restaurant,
                'user': request.user,
            })

        delivery_charge, distance_km = calculate_delivery_charge(
            address,
            restaurant.address
        )

        grand_total = subtotal + delivery_charge

        order = Order.objects.create(
            user=request.user,
            restaurant=restaurant,
            total_price=subtotal,
            delivery_charge=delivery_charge,
            payment_method=payment_method,
            customer_phone=phone,
            customer_address=address,
            status='PENDING',
        )

        for item_id, item_data in cart.items():
            menu_item = get_object_or_404(MenuItem, id=item_id)
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                price=menu_item.price,
            )

        request.session['cart'] = {}
        request.session['cart_restaurant_id'] = None

        if payment_method in ['BKASH', 'NAGAD']:
            return redirect('orders:dummy_payment', order_id=order.id)

        messages.success(request, '🎉 Order placed successfully!')
        return redirect('orders:order_success', order_id=order.id)

    return render(request, 'orders/checkout.html', {
        'items': items,
        'subtotal': subtotal,
        'delivery_charge': 50,
        'distance_km': None,
        'total': subtotal + 50,
        'restaurant': restaurant,
        'user': request.user,
    })

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    #  Can only cancel if pending - not if already  preparing or beyond
    if order.status == 'PENDING':
        order.status = 'CANCELED'
        order.save()

        # Notify the restaurant
        from orders.models import Notification
        if order.restaurant and order.restaurant.owner:
            Notification.objects.create(
                user=order.restaurant.owner,
                message=f'❌ Customer {request.user.username} canceled Order #{order.id}.'
            )

        messages.success(request, '✅ Order canceled successfully.')
    elif order.status in ['PREPARING', 'ON_THE_WAY', 'DELIVERED']:
        messages.error(
            request,
            f'❌ Cannot cancel - your order is already {order.get_status_display()}!'
        )
    else:
        messages.error(request, '❌ This order cannot be canceled.')

    return redirect('orders:my_orders')


@login_required
def dummy_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/dummy_payment.html', {'order': order})


@login_required
def confirm_dummy_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.is_paid = True
    order.status = 'PREPARING'
    order.save()
    messages.success(request, '✅ Payment confirmed!')
    return redirect('orders:order_success', order_id=order.id)

def update_cart_quantity(request, item_id, action):
    cart = request.session.get('cart', {})

    if str(item_id) in cart:
        if action == 'increase':
            cart[str(item_id)]['quantity'] += 1
        elif action == 'decrease':
            cart[str(item_id)]['quantity'] -= 1
            if cart[str(item_id)]['quantity'] <= 0:
                cart.pop(str(item_id))
                if not cart:
                    request.session['cart_restaurant_id'] = None

    request.session['cart'] = cart
    return redirect('orders:view_cart')
@login_required
def notifications(request):
    notifs = request.user.notifications.order_by('-created_at')
    # Mark all as read
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'orders/notifications.html', {'notifs': notifs})
def notification_count(request):
    if request.user.is_authenticated:
        count = request.user.notifications.filter(is_read=False).count()
        return {'unread_notifications': count}
    return {'unread_notifications': 0}
from django.http import JsonResponse

def calculate_delivery_ajax(request):
    #Called by JavaScript when customer types address
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        customer_address = data.get('address', '')
        restaurant_id = data.get('restaurant_id', '')

        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
            charge, distance = calculate_delivery_charge(
                customer_address,
                restaurant.address
            )
            return JsonResponse({
                'charge': charge,
                'distance': distance
            })
        except Exception:
            return JsonResponse({'charge': 50, 'distance': None})

    return JsonResponse({'charge': 50, 'distance': None})