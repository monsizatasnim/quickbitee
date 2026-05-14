from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import GroupOrder, GroupOrderItem, GroupMemberPayment
from restaurants.models import MenuItem, Restaurant
from orders.models import Order, OrderItem
from orders.views import calculate_delivery_charge


@login_required
def group_list(request):
    my_groups = GroupOrder.objects.filter(
        members=request.user,
        is_active=True
    )
    return render(request, 'group_order/group_list.html', {
        'groups': my_groups
    })


@login_required
def create_group(request):
    restaurants = Restaurant.objects.filter(is_active=True)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        restaurant_id = request.POST.get('restaurant_id')

        if not name or not restaurant_id:
            messages.error(request, '❌ Name and restaurant are required!')
        else:
            restaurant = get_object_or_404(Restaurant, id=restaurant_id)
            group = GroupOrder.objects.create(
                name=name,
                created_by=request.user,
                restaurant=restaurant
            )
            group.members.add(request.user)
            messages.success(
                request,
                f'✅ Group created! Share code: {group.invite_code}'
            )
            return redirect('group_order:group_detail', group_id=group.id)

    return render(request, 'group_order/create_group.html', {
        'restaurants': restaurants
    })


@login_required
def join_group(request):
    if request.method == 'POST':
        invite_code = request.POST.get('invite_code', '').strip().upper()
        try:
            group = GroupOrder.objects.get(
                invite_code=invite_code,
                is_active=True
            )
            group.members.add(request.user)
            messages.success(request, f'✅ You joined "{group.name}"!')
            return redirect('group_order:group_detail', group_id=group.id)
        except GroupOrder.DoesNotExist:
            messages.error(request, '❌ Invalid invite code!')

    return render(request, 'group_order/join_group.html')


@login_required
def group_detail(request, group_id):
    group = get_object_or_404(GroupOrder, id=group_id)

    if request.user not in group.members.all():
        messages.error(request, '❌ You are not a member!')
        return redirect('group_order:group_list')

    menu_items = MenuItem.objects.filter(
        restaurant=group.restaurant,
        is_available=True
    )
    group_items = GroupOrderItem.objects.filter(group=group)

    # Get current user's payment method
    my_item = group_items.filter(user=request.user).first()
    my_payment = my_item.payment_method if my_item else 'COD'

    # Check if member already has a payment record
    my_payment_record = GroupMemberPayment.objects.filter(
        group=group,
        user=request.user
    ).first()

    # Handle SET PAYMENT METHOD
    if request.method == 'POST' and 'set_payment' in request.POST:
        payment = request.POST.get('payment_method', 'COD')
        group_items.filter(user=request.user).update(payment_method=payment)
        messages.success(request, '✅ Payment method saved!')
        return redirect('group_order:group_detail', group_id=group.id)

    # Handle ADD ITEM
    if request.method == 'POST' and 'item_id' in request.POST:
        item_id = request.POST.get('item_id')
        menu_item = get_object_or_404(MenuItem, id=item_id)

        group_item, created = GroupOrderItem.objects.get_or_create(
            group=group,
            user=request.user,
            menu_item=menu_item,
            defaults={'payment_method': my_payment}
        )
        if not created:
            group_item.quantity += 1
            group_item.save()

        messages.success(request, f'✅ {menu_item.name} added!')
        return redirect('group_order:group_detail', group_id=group.id)

    # Handle FINALIZE
    if request.method == 'POST' and 'finalize_group' in request.POST:
        if request.user == group.created_by:
            if not group_items.exists():
                messages.error(request, '❌ No items in the order!')
                return redirect('group_order:group_detail', group_id=group.id)

            members_list = list(group.members.all())
            total_members = len(members_list)

            # Calculate delivery
            creator_address = request.user.address or 'Dhaka'
            delivery_charge, _ = calculate_delivery_charge(
                creator_address,
                group.restaurant.address
            )
            delivery_charge = Decimal(str(delivery_charge))
            delivery_per_person = round(delivery_charge / total_members, 2)

            # Total food cost
            total_food = sum(e.get_subtotal() for e in group_items)

            # Create ONE main order
            main_order = Order.objects.create(
                user=request.user,
                restaurant=group.restaurant,
                total_price=total_food,
                delivery_charge=delivery_charge,
                payment_method='COD',
                customer_phone=request.user.phone_number or 'N/A',
                customer_address=request.user.address or 'N/A',
                status='PENDING',
            )

            # Add all items to the order
            for entry in group_items:
                OrderItem.objects.create(
                    order=main_order,
                    menu_item=entry.menu_item,
                    quantity=entry.quantity,
                    price=entry.menu_item.price,
                )

            # Create payment records for each member
            for member in members_list:
                member_items = group_items.filter(user=member)
                member_food = sum(e.get_subtotal() for e in member_items)
                member_payment = group_items.filter(
                    user=member
                ).first()
                payment_method = member_payment.payment_method if member_payment else 'COD'

                GroupMemberPayment.objects.get_or_create(
                    group=group,
                    user=member,
                    defaults={
                        'food_amount': member_food,
                        'delivery_share': delivery_per_person,
                        'total_amount': member_food + delivery_per_person,
                        'payment_method': payment_method,
                        'is_paid': False,
                    }
                )

            group_items.delete()
            group.is_active = False
            group.save()

            messages.success(
                request,
                f'✅ Group order placed! '
                f'Each member can now pay their share.'
            )
            return redirect(
                'group_order:group_payment_summary',
                group_id=group.id
            )

    # Bill calculation
    members_count = group.get_total_members() or 1
    delivery_charge, _ = calculate_delivery_charge(
        request.user.address or 'Dhaka',
        group.restaurant.address
    )
    delivery_charge = Decimal(str(delivery_charge))
    delivery_per_person = round(delivery_charge / members_count, 2)

    user_bills = {}
    total_group_bill = Decimal('0')

    for entry in group_items:
        username = entry.user.username
        subtotal = entry.get_subtotal()
        total_group_bill += subtotal

        if username not in user_bills:
            user_bills[username] = {
                'food': Decimal('0'),
                'delivery': delivery_per_person,
                'total': Decimal('0')
            }
        user_bills[username]['food'] += subtotal

    for username in user_bills:
        user_bills[username]['total'] = (
            user_bills[username]['food'] +
            user_bills[username]['delivery']
        )

    total_group_bill += delivery_charge

    return render(request, 'group_order/group_detail.html', {
        'group': group,
        'menu_items': menu_items,
        'group_items': group_items,
        'user_bills': user_bills,
        'total_group_bill': total_group_bill,
        'delivery_per_person': delivery_per_person,
        'my_payment': my_payment,
        'my_payment_record': my_payment_record,
    })


@login_required
def group_payment_summary(request, group_id):
    #Shows payment status for all members after finalization
    group = get_object_or_404(GroupOrder, id=group_id)

    if request.user not in group.members.all():
        return redirect('group_order:group_list')

    member_payments = GroupMemberPayment.objects.filter(group=group)
    my_payment = member_payments.filter(user=request.user).first()

    return render(request, 'group_order/group_payment_summary.html', {
        'group': group,
        'member_payments': member_payments,
        'my_payment': my_payment,
    })


@login_required
def group_pay(request, group_id):
    group = get_object_or_404(GroupOrder, id=group_id)
    payment_record = get_object_or_404(
        GroupMemberPayment,
        group=group,
        user=request.user
    )

    if payment_record.is_paid:
        messages.info(request, '✅ You have already paid!')
        return redirect(
            'group_order:group_payment_summary',
            group_id=group.id
        )

    return render(request, 'group_order/group_pay.html', {
        'group': group,
        'payment_record': payment_record,
    })


@login_required
def group_pay_confirm(request, group_id):
    """Confirm payment for a member"""
    group = get_object_or_404(GroupOrder, id=group_id)
    payment_record = get_object_or_404(
        GroupMemberPayment,
        group=group,
        user=request.user
    )

    if not payment_record.is_paid:
        payment_record.is_paid = True
        payment_record.transaction_id = get_random_string(12).upper()
        payment_record.paid_at = timezone.now()
        payment_record.save()

        messages.success(
            request,
            f'✅ Payment confirmed! '
            f'Transaction ID: {payment_record.transaction_id}'
        )

    return redirect(
        'group_order:group_payment_summary',
        group_id=group.id
    )


@login_required
def remove_group_item(request, item_id):
    item = get_object_or_404(
        GroupOrderItem,
        id=item_id,
        user=request.user
    )
    group_id = item.group.id
    item.delete()
    messages.success(request, '🗑️ Item removed.')
    return redirect('group_order:group_detail', group_id=group_id)