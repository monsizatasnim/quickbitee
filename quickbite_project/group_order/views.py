from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import GroupOrder
from menu.models import MenuItem
from .models import GroupOrderItem
from orders.models import Order, OrderItem

@login_required
def group_list(request):
    groups = GroupOrder.objects.all()
    return render(request, 'group_list.html', {'groups': groups})

@login_required
def create_group(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            group = GroupOrder.objects.create(
                name=name,
                created_by=request.user
            )
            group.members.add(request.user)  # Creator is also a member
            return redirect('group_list')
    return render(request, 'create_group.html')


@login_required
def group_detail(request, group_id):
    group = get_object_or_404(GroupOrder, id=group_id)

    if request.user not in group.members.all():
        return redirect('group_list')

    items = MenuItem.objects.all()
    group_items = GroupOrderItem.objects.filter(group=group)

    # ✅ ADD ITEM LOGIC
    if request.method == 'POST' and 'item_id' in request.POST:
        item_id = request.POST.get('item_id')
        menu_item = get_object_or_404(MenuItem, id=item_id)

        group_item, created = GroupOrderItem.objects.get_or_create(
            group=group,
            user=request.user,
            menu_item=menu_item
        )

        if not created:
            group_item.quantity += 1
            group_item.save()

        return redirect('group_detail', group_id=group.id)

    # ✅ FINALIZE LOGIC
    if request.method == 'POST' and 'finalize_group' in request.POST:
        if request.user == group.created_by:
            user_totals = {}

            for entry in group_items:
                if entry.user not in user_totals:
                    user_totals[entry.user] = entry.get_subtotal()
                else:
                    user_totals[entry.user] += entry.get_subtotal()

            for user, total in user_totals.items():
                order = Order.objects.create(
                    user=user,
                    total_price=total,
                    status='PENDING'
                )

                user_entries = group_items.filter(user=user)

                for entry in user_entries:
                    OrderItem.objects.create(
                        order=order,
                        menu_item=entry.menu_item,
                        quantity=entry.quantity,
                        price=entry.menu_item.price
                    )

            group_items.delete()
            group.is_active = False
            group.save()

            return redirect('my_orders')

    # ✅ BILL CALCULATION
    user_totals = {}
    total_group_bill = 0

    for entry in group_items:
        subtotal = entry.get_subtotal()
        total_group_bill += subtotal

        if entry.user.username not in user_totals:
            user_totals[entry.user.username] = subtotal
        else:
            user_totals[entry.user.username] += subtotal

    return render(request, 'group_detail.html', {
        'group': group,
        'items': items,
        'group_items': group_items,
        'user_totals': user_totals,
        'total_group_bill': total_group_bill
    })
@login_required
def join_group(request, group_id):
    group = get_object_or_404(GroupOrder, id=group_id)
    group.members.add(request.user)
    return redirect('group_detail', group_id=group.id)