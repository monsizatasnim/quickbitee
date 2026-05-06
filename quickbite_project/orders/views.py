from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from menu.models import MenuItem
from .models import Order, OrderItem
from django.utils.crypto import get_random_string
from payments.models import Payment

@login_required
def create_order(request):
    cart = request.session.get('cart', {})

    if not cart:
        return redirect('/')

    total_price = 0

    # Calculate total
    for item_id, quantity in cart.items():
        menu_item = MenuItem.objects.get(id=item_id)
        total_price += menu_item.price * quantity

    # Create order
    order = Order.objects.create(
        user=request.user,
        total_price=total_price
    )

    # Create order items
    for item_id, quantity in cart.items():
        menu_item = MenuItem.objects.get(id=item_id)
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=quantity,
            price=menu_item.price
        )

    # Clear cart
    request.session['cart'] = {}

    # Redirect to success page
    return redirect('order_success', order_id=order.id)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'order_success.html', {'order': order, 'items': items})
from django.contrib.auth.decorators import login_required

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'order_detail.html', {
        'order': order,
        'items': items
    })




@login_required
def make_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_paid:
        return redirect('order_detail', order_id=order.id)

    transaction_id = get_random_string(12)

    Payment.objects.create(
        order=order,
        transaction_id=transaction_id,
        amount=order.total_price,
        paid_by=request.user
    )

    order.is_paid = True
    order.status = "PREPARING"
    order.save()

    return render(request, 'payment_success.html', {
        'order': order,
        'transaction_id': transaction_id
    })