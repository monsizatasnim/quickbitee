# restaurants/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Restaurant, MenuItem
from orders.models import Order



# PUBLIC VIEWS (anyone can see)


def restaurant_list(request):
    restaurants = Restaurant.objects.filter(is_active=True)
    return render(request, 'restaurants/restaurant_list.html', {
        'restaurants': restaurants
    })


def restaurant_detail(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    menu_items = MenuItem.objects.filter(
        restaurant=restaurant,
        is_available=True
    )

    # Allergy detection
    user_allergies = []
    if request.user.is_authenticated and request.user.allergies:
        user_allergies = [
            a.strip().lower()
            for a in request.user.allergies.split(',')
        ]

    return render(request, 'restaurants/restaurant_detail.html', {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'user_allergies': user_allergies,
    })



# OWNER DASHBOARD VIEWS (only restaurant owners)


def owner_required(view_func):
    """Custom decorator to check if user is a restaurant owner"""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_restaurant_owner:
            messages.error(request, '❌ You are not a restaurant owner!')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@owner_required
def owner_dashboard(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    menu_items = MenuItem.objects.filter(restaurant=restaurant)
    orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')

    # Count orders by status
    pending_count = orders.filter(status='PENDING').count()
    preparing_count = orders.filter(status='PREPARING').count()
    delivered_count = orders.filter(status='DELIVERED').count()

    return render(request, 'restaurants/owner_dashboard.html', {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'orders': orders,
        'pending_count': pending_count,
        'preparing_count': preparing_count,
        'delivered_count': delivered_count,
    })


@owner_required
def add_menu_item(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        ingredients = request.POST.get('ingredients', '').strip()
        image = request.FILES.get('image')

        if not name or not price:
            messages.error(request, '❌ Name and price are required!')
        else:
            MenuItem.objects.create(
                restaurant=restaurant,
                name=name,
                description=description,
                price=price,
                ingredients=ingredients,
                image=image,
            )
            messages.success(request, f'✅ {name} added to menu!')
            return redirect('restaurants:owner_dashboard')

    return render(request, 'restaurants/add_menu_item.html', {
        'restaurant': restaurant
    })


@owner_required
def edit_menu_item(request, item_id):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)

    if request.method == 'POST':
        item.name = request.POST.get('name', item.name).strip()
        item.description = request.POST.get('description', item.description).strip()
        item.price = request.POST.get('price', item.price)
        item.ingredients = request.POST.get('ingredients', item.ingredients).strip()
        item.is_available = 'is_available' in request.POST

        if request.FILES.get('image'):
            item.image = request.FILES.get('image')

        item.save()
        messages.success(request, f'✅ {item.name} updated!')
        return redirect('restaurants:owner_dashboard')

    return render(request, 'restaurants/edit_menu_item.html', {
        'restaurant': restaurant,
        'item': item,
    })


@owner_required
def delete_menu_item(request, item_id):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)

    # Check if item has active orders
    from orders.models import OrderItem
    active_orders = OrderItem.objects.filter(
        menu_item=item,
        order__status__in=['PENDING', 'PREPARING']
    ).exists()

    if active_orders:
        messages.error(
            request,
            f'❌ Cannot delete "{item.name}" because it has active orders!'
            ' Cancel those orders first.'
        )
        return redirect('restaurants:owner_dashboard')

    item_name = item.name
    item.delete()
    messages.success(request, f'✅ {item_name} deleted!')
    return redirect('restaurants:owner_dashboard')


@owner_required
def update_order_status(request, order_id):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid = ['PENDING', 'CONFIRMED', 'PREPARING',
                 'ON_THE_WAY', 'DELIVERED', 'CANCELED']

        if new_status in valid:
            order.status = new_status
            order.save()

            # Send notification to customer
            from orders.models import Notification

            status_messages = {
                'PENDING':    '🕐 Your order has been received.',
                'CONFIRMED':  '✅ Your order has been confirmed by the restaurant!',
                'PREPARING':  '👨‍🍳 The restaurant is now preparing your order!',
                'ON_THE_WAY': '🚴 Your order is on the way!',
                'DELIVERED':  '🎉 Your order has been delivered. Enjoy your meal!',
                'CANCELED':   f'❌ Your order #{order.id} from {restaurant.name} has been canceled by the restaurant.',
            }

            Notification.objects.create(
                user=order.user,
                message=status_messages.get(new_status, 'Your order status has been updated.')
            )

            messages.success(
                request,
                f'✅ Order #{order.id} updated to {new_status}!'
            )

    return redirect('restaurants:owner_dashboard')


@owner_required
def edit_restaurant(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)

    if request.method == 'POST':
        restaurant.name = request.POST.get('name', restaurant.name).strip()
        restaurant.description = request.POST.get('description', restaurant.description).strip()
        restaurant.address = request.POST.get('address', restaurant.address).strip()
        restaurant.phone = request.POST.get('phone', restaurant.phone).strip()

        if request.FILES.get('image'):
            restaurant.image = request.FILES.get('image')

        restaurant.save()
        messages.success(request, '✅ Restaurant info updated!')
        return redirect('restaurants:owner_dashboard')

    return render(request, 'restaurants/edit_restaurant.html', {
        'restaurant': restaurant
    })