from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from restaurants.models import MenuItem, Restaurant
from .models import Order, OrderItem

def calculate_delivery_charge(address):
    address_lower = address.lower()

    far_keywords = ['uttara', 'gazipur', 'narayanganj',
                    'savar', 'keraniganj', 'tongi']

    medium_keywords = ['mirpur', 'mohammadpur', 'demra',
                       'badda', 'khilgaon', 'rampura']

    for keyword in far_keywords:
        if keyword in address_lower:
            return 80

    for keyword in medium_keywords:
        if keyword in address_lower:
            return 50

    return 30

def add_to_cart(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    cart = request.session.get('cart', {})

    cart_restaurant_id = request.session.get('cart_restaurant_id')

    if cart_restaurant_id and int(cart_restaurant_id) != item.restaurant.id:
        cart = {}
        messages.warning(request, '⚠️ Your cart was cleared because you switched restaurants.')

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

        delivery_charge = calculate_delivery_charge(address)
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
        'delivery_charge': delivery_charge,
        'total': subtotal + delivery_charge,
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

    if order.status == 'PENDING':
        order.status = 'CANCELED'
        order.save()
        messages.success(request, '✅ Order cancelled successfully.')
    else:
        messages.error(request, '❌ You can only cancel pending orders.')

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