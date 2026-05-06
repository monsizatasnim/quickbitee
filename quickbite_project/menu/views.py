from django.shortcuts import redirect, get_object_or_404
from .models import MenuItem
from django.shortcuts import render

def add_to_cart(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)

    cart = request.session.get('cart', {})

    if str(item_id) in cart:
        cart[str(item_id)] += 1
    else:
        cart[str(item_id)] = 1

    request.session['cart'] = cart
    print(request.session['cart'])

    return redirect('/')
def home(request):
    items = MenuItem.objects.all()
    user_allergies = []

    if request.user.is_authenticated and request.user.allergies:
        user_allergies = [a.strip().lower() for a in request.user.allergies.split(',')]

    return render(request, 'home.html', {
        'items': items,
        'user_allergies': user_allergies
    })
def view_cart(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0

    for item_id, quantity in cart.items():
        menu_item = MenuItem.objects.get(id=item_id)
        subtotal = menu_item.price * quantity
        total += subtotal
        items.append({
            'item': menu_item,
            'quantity': quantity,
            'subtotal': subtotal,
        })

    return render(request, 'cart.html', {'items': items, 'total': total})