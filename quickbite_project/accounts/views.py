from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import (
    CustomUserCreationForm,
    RestaurantOwnerRegistrationForm,
    UserProfileForm
)


def register_view(request):
    #Customer registration
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f'🎉 Welcome to QuickBite, {user.first_name}!'
            )
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


def restaurant_register_view(request):
    #Restaurant owner registration
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RestaurantOwnerRegistrationForm(
            request.POST,
            request.FILES
        )
        if form.is_valid():

            user = form.save()


            from restaurants.models import Restaurant
            Restaurant.objects.create(
                owner=user,
                name=form.cleaned_data['restaurant_name'],
                description=form.cleaned_data['restaurant_description'],
                address=form.cleaned_data['restaurant_address'],
                phone=form.cleaned_data['restaurant_phone'],
                image=form.cleaned_data.get('restaurant_image'),
            )

            # Log them in
            login(request, user)
            messages.success(
                request,
                f'🎉 Welcome {user.first_name}! '
                f'Your restaurant has been created!'
            )
            return redirect('restaurants:owner_dashboard')
    else:
        form = RestaurantOwnerRegistrationForm()

    return render(request, 'accounts/restaurant_register.html', {
        'form': form
    })


def customer_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_restaurant_owner:
                messages.error(
                    request,
                    '❌ Please use the Restaurant Login page!'
                )
                return redirect('accounts:restaurant_login')
            login(request, user)
            messages.success(
                request,
                f'✅ Welcome back, {user.first_name or user.username}!'
            )
            return redirect('home')
        else:
            messages.error(request, '❌ Invalid username or password!')

    return render(request, 'accounts/customer_login.html')


def restaurant_login(request):
    if request.user.is_authenticated:
        if request.user.is_restaurant_owner:
            return redirect('restaurants:owner_dashboard')
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_restaurant_owner:
                messages.error(
                    request,
                    '❌ This is not a restaurant account!'
                )
                return redirect('accounts:login')
            login(request, user)
            messages.success(
                request,
                f'✅ Welcome back, {user.username}!'
            )
            return redirect('restaurants:owner_dashboard')
        else:
            messages.error(request, '❌ Invalid username or password!')

    return render(request, 'accounts/restaurant_login.html')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(
            request.POST,
            request.FILES,
            instance=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Profile updated!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})