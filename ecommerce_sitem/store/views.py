from django.shortcuts import render, get_object_or_404
from .models import Product, Order

def home(request):
    products = Product.objects.all()
    return render(request, 'store/home.html', {'products': products})

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

from django.contrib.auth import login, logout, authenticate
from .forms import UserRegistration
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages

def register_user(request):
    if request.method == 'POST':
        form = UserRegistration(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            # Send verification email
            from django.contrib.sites.shortcuts import get_current_site
            from django.template.loader import render_to_string
            from django.http import HttpResponse

            current_site = get_current_site(request)
            mail_subject = 'Activate your account.'
            message = render_to_string('store/account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            user.email_user(mail_subject, message)
            return HttpResponse('Please confirm your email address to complete the registration.')
        else:
            return render(request, 'store/register.html', {'form': form, 'error': 'Invalid registration details.'})
    else:
        form = UserRegistration()
    return render(request, 'store/register.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated! You can now log in.')
        return redirect('store:login_user')
    else:
        messages.error(request, 'Activation link is invalid!')
        return redirect('store:register_user')

from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('store:home')
    else:
        form = AuthenticationForm()
        if 'next' in request.GET:
            messages.info(request, "Please login/register first to proceed to checkout.")
    return render(request, 'store/login.html', {'form': form})

def logout_user(request):
    logout(request)
    return redirect('store:home')

def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    cart[product_id] = cart.get(product_id, 0) + 1
    request.session['cart'] = cart
    return redirect('store:cart')

def cart(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(id__in=[int(pid) for pid in cart.keys()])
    cart_items = []
    total = 0
    for product in products:
        quantity = cart.get(str(product.id), 0)
        subtotal = product.price * quantity
        total += subtotal
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal  # <-- use 'subtotal'
        })
    return render(request, 'store/cart.html', {'cart_items': cart_items, 'total': total})

@login_required(login_url='store:login_user')
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('store:cart')
    
    products = Product.objects.filter(id__in=cart.keys())
    
    for product in products:
        quantity = cart.get(str(product.id))
        Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            product=product,
            quantity=quantity
        )
        
    request.session['cart'] = {}  # Clear the cart after checkout
    messages.success(request, "Your order has been placed successfully.")
    return redirect('store:cart')

def search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(name__icontains=query) if query else []
    return render(request, 'store/search_results.html', {'products': products, 'query': query})