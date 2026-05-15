from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import GroupOrder, GroupOrderItem, GroupMemberPayment
from restaurants.models import MenuItem, Restaurant
from orders.models import Order, OrderItem, Notification
from orders.views import calculate_delivery_charge


@login_required
def group_list(request):
    my_active_groups = GroupOrder.objects.filter(
        members=request.user,
        is_active=True
    )
    # ✅ Show finalized groups too
    my_finalized_groups = GroupOrder.objects.filter(
        members=request.user,
        is_active=False
    ).order_by('-created_at')[:10]

    return render(request, 'group_order/group_list.html', {
        'groups': my_active_groups,
        'finalized_groups': my_finalized_groups,
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

    # ✅ If group is finalized, redirect to payment summary
    if not group.is_active:
        return redirect(
            'group_order:group_payment_summary', group_id=group.id
        )

    menu_items = MenuItem.objects.filter(
        restaurant=group.restaurant,
        is_available=True
    )
    group_items = GroupOrderItem.objects.filter(group=group)

    # ✅ Get payment preference from items or session
    my_item = group_items.filter(user=request.user).first()
    if my_item:
        my_payment = my_item.payment_method
    else:
        my_payment = request.session.get(
            f'group_{group_id}_payment', 'COD'
        )

    my_payment_record = GroupMemberPayment.objects.filter(
        group=group,
        user=request.user
    ).first()

    # ✅ Handle UPDATE PROFILE (address/phone)
    if request.method == 'POST' and 'update_profile' in request.POST:
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        if phone and address:
            request.user.phone_number = phone
            request.user.address = address
            request.user.save()
            messages.success(request, '✅ Contact info updated!')
        else:
            messages.error(request, '❌ Phone and address are required!')
        return redirect('group_order:group_detail', group_id=group.id)

    # ✅ Handle SET PAYMENT METHOD
    if request.method == 'POST' and 'set_payment' in request.POST:
        payment = request.POST.get('payment_method', 'COD')

        # Save to session so new items get this payment
        request.session[f'group_{group_id}_payment'] = payment

        # Update existing items if any
        updated = group_items.filter(user=request.user).update(
            payment_method=payment
        )

        payment_name = dict(
            GroupOrderItem.PAYMENT_CHOICES
        ).get(payment, payment)

        if updated:
            messages.success(
                request,
                f'✅ Payment method saved as {payment_name}!'
            )
        else:
            messages.success(
                request,
                f'✅ Payment method set to {payment_name}! '
                f'Add items to continue.'
            )
        return redirect('group_order:group_detail', group_id=group.id)

    # ✅ Handle ADD ITEM
    if request.method == 'POST' and 'item_id' in request.POST:
        item_id = request.POST.get('item_id')
        menu_item = get_object_or_404(MenuItem, id=item_id)

        # Get saved payment preference
        saved_payment = request.session.get(
            f'group_{group_id}_payment', 'COD'
        )
        existing_item = group_items.filter(user=request.user).first()
        if existing_item:
            saved_payment = existing_item.payment_method

        group_item, created = GroupOrderItem.objects.get_or_create(
            group=group,
            user=request.user,
            menu_item=menu_item,
            defaults={'payment_method': saved_payment}
        )
        if not created:
            group_item.quantity += 1
            group_item.save()

        messages.success(request, f'✅ {menu_item.name} added!')
        return redirect('group_order:group_detail', group_id=group.id)

    # ✅ Handle FINALIZE
    if request.method == 'POST' and 'finalize_group' in request.POST:
        if request.user == group.created_by:
            if not group_items.exists():
                messages.error(request, '❌ No items in the order!')
                return redirect(
                    'group_order:group_detail', group_id=group.id
                )

            creator_address = request.user.address
            creator_phone = request.user.phone_number

            if not creator_address or not creator_phone:
                messages.error(
                    request,
                    '❌ Please update your phone and address first!'
                )
                return redirect(
                    'group_order:group_detail', group_id=group.id
                )

            members_list = list(group.members.all())
            total_members = len(members_list)

            delivery_charge, _ = calculate_delivery_charge(
                creator_address,
                group.restaurant.address
            )
            delivery_charge = Decimal(str(delivery_charge))
            delivery_per_person = round(
                delivery_charge / total_members, 2
            )

            total_food = sum(e.get_subtotal() for e in group_items)

            creator_item = group_items.filter(
                user=request.user
            ).first()
            creator_payment = (
                creator_item.payment_method if creator_item else 'COD'
            )

            main_order = Order.objects.create(
                user=request.user,
                restaurant=group.restaurant,
                total_price=total_food,
                delivery_charge=delivery_charge,
                payment_method=creator_payment,
                customer_phone=creator_phone,
                customer_address=creator_address,
                status='PENDING',
                is_paid=False,
            )

            for entry in group_items:
                OrderItem.objects.create(
                    order=main_order,
                    menu_item=entry.menu_item,
                    quantity=entry.quantity,
                    price=entry.menu_item.price,
                )

            # ✅ Create payment records
            for member in members_list:
                member_items = group_items.filter(user=member)
                member_food = sum(
                    e.get_subtotal() for e in member_items
                )
                member_payment_item = member_items.first()
                payment_method = (
                    member_payment_item.payment_method
                    if member_payment_item else 'COD'
                )

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
            group.main_order = main_order
            group.save()

            # ✅ Notify restaurant
            if group.restaurant and group.restaurant.owner:
                all_payments = GroupMemberPayment.objects.filter(
                    group=group
                )
                online_count = all_payments.exclude(
                    payment_method='COD'
                ).count()
                cod_count = all_payments.filter(
                    payment_method='COD'
                ).count()

                Notification.objects.create(
                    user=group.restaurant.owner,
                    message=(
                        f'🍽️ New group order #{main_order.id} '
                        f'from "{group.name}" '
                        f'({total_members} members). '
                        f'Total: ৳{total_food + delivery_charge}. '
                        f'{online_count} paying online, '
                        f'{cod_count} paying COD.'
                    )
                )

            # ✅ Notify all OTHER members with PAY LINK
            for member in members_list:
                if member != request.user:
                    member_pay = GroupMemberPayment.objects.filter(
                        group=group, user=member
                    ).first()
                    if member_pay:
                        if member_pay.payment_method != 'COD':
                            Notification.objects.create(
                                user=member,
                                message=(
                                    f'🍽️ Group order "{group.name}" '
                                    f'has been placed! '
                                    f'Your share: '
                                    f'৳{member_pay.total_amount}. '
                                    f'Please pay via '
                                    f'{member_pay.get_payment_method_display()} now! '
                                    f'<a href="/groups/{group.id}/payment-summary/" '
                                    f'style="color:#80ffdb;'
                                    f'font-weight:bold;">'
                                    f'👉 Pay Now</a>'
                                )
                            )
                        else:
                            Notification.objects.create(
                                user=member,
                                message=(
                                    f'🍽️ Group order "{group.name}" '
                                    f'has been placed! '
                                    f'Your share: '
                                    f'৳{member_pay.total_amount} '
                                    f'(Cash on Delivery). '
                                    f'<a href="/groups/{group.id}/payment-summary/" '
                                    f'style="color:#80ffdb;'
                                    f'font-weight:bold;">'
                                    f'👉 View Details</a>'
                                )
                            )

            messages.success(
                request,
                '✅ Group order placed! '
                'Each member can now pay their share.'
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
                'total': Decimal('0'),
                'payment_method': entry.payment_method,
            }
        user_bills[username]['food'] += subtotal

    for username in user_bills:
        user_bills[username]['total'] = (
            user_bills[username]['food']
            + user_bills[username]['delivery']
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
    group = get_object_or_404(GroupOrder, id=group_id)

    if request.user not in group.members.all():
        return redirect('group_order:group_list')

    member_payments = GroupMemberPayment.objects.filter(group=group)
    my_payment = member_payments.filter(user=request.user).first()

    total_members = member_payments.count()
    paid_count = member_payments.filter(is_paid=True).count()
    unpaid_count = member_payments.filter(is_paid=False).count()

    total_bill = sum(p.total_amount for p in member_payments)
    total_paid = sum(
        p.total_amount for p in member_payments if p.is_paid
    )
    total_remaining = total_bill - total_paid

    cod_total = sum(
        p.total_amount for p in member_payments
        if p.payment_method == 'COD'
    )
    online_total = sum(
        p.total_amount for p in member_payments
        if p.payment_method != 'COD'
    )
    online_collected = sum(
        p.total_amount for p in member_payments
        if p.payment_method != 'COD' and p.is_paid
    )
    online_pending = online_total - online_collected

    return render(request, 'group_order/group_payment_summary.html', {
        'group': group,
        'member_payments': member_payments,
        'my_payment': my_payment,
        'total_members': total_members,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'total_bill': total_bill,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'cod_total': cod_total,
        'online_total': online_total,
        'online_collected': online_collected,
        'online_pending': online_pending,
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

    if payment_record.payment_method == 'COD':
        messages.info(
            request,
            '💵 Your payment method is Cash on Delivery. '
            'No online payment needed!'
        )
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

        all_payments = GroupMemberPayment.objects.filter(group=group)

        if group.main_order:
            online_collected = sum(
                p.total_amount for p in all_payments
                if p.is_paid and p.payment_method != 'COD'
            )
            online_pending = sum(
                p.total_amount for p in all_payments
                if not p.is_paid and p.payment_method != 'COD'
            )
            cod_total = sum(
                p.total_amount for p in all_payments
                if p.payment_method == 'COD'
            )

            # Check if ALL online paid
            all_online_paid = not all_payments.exclude(
                payment_method='COD'
            ).filter(is_paid=False).exists()

            # Check if everyone paid (no COD members)
            all_paid = not all_payments.filter(is_paid=False).exists()

            if all_paid:
                group.main_order.is_paid = True
                group.main_order.save()

            # ✅ Notify restaurant
            if (group.main_order.restaurant
                    and group.main_order.restaurant.owner):
                Notification.objects.create(
                    user=group.main_order.restaurant.owner,
                    message=(
                        f'💰 {request.user.username} paid '
                        f'৳{payment_record.total_amount} '
                        f'via '
                        f'{payment_record.get_payment_method_display()} '
                        f'for group order #{group.main_order.id} '
                        f'"{group.name}". '
                        f'Online collected: ৳{online_collected}. '
                        f'Online pending: ৳{online_pending}. '
                        f'COD: ৳{cod_total}.'
                    )
                )

            # ✅ Notify the user
            Notification.objects.create(
                user=request.user,
                message=(
                    f'✅ Your payment of '
                    f'৳{payment_record.total_amount} '
                    f'for group order "{group.name}" confirmed! '
                    f'Transaction ID: {payment_record.transaction_id}'
                )
            )

            # ✅ Notify group creator
            if request.user != group.created_by:
                Notification.objects.create(
                    user=group.created_by,
                    message=(
                        f'💰 {request.user.username} paid '
                        f'৳{payment_record.total_amount} '
                        f'for group "{group.name}" via '
                        f'{payment_record.get_payment_method_display()}.'
                    )
                )

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


@login_required
def delete_group(request, group_id):
    group = get_object_or_404(GroupOrder, id=group_id)

    #Only the creator can delete the group
    if request.user != group.created_by:
        messages.error(request, '❌ Only the group creator can delete this group!')
        return redirect('group_order:group_detail', group_id=group.id)

    #Cannot delete if the order is already finalized
    if not group.is_active:
        messages.error(request, '❌ Cannot delete a finalized group. The order has already been placed!')
        return redirect('group_order:group_payment_summary', group_id=group.id)

    group_name = group.name
    #This will auto delete all group order items and group member payments because of on_delete=CASCADE
    group.delete()

    messages.success(request, f'🗑️ Group "{group_name}" has been deleted.')
    return redirect('group_order:group_list')