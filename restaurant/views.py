from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count

from .models import UserProfile, Category, SubCategory, Product, Order, Cart, CartItem, OrderItem, OrderFeedback

def home_redirect(request):
    return redirect('login_url')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists!'})

        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user, role=role, phone=phone, address=address)
        return redirect('login_url')

    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        uname_or_email = request.POST.get('username')
        upass = request.POST.get('password')
        
        user = None
        if '@' in uname_or_email:
            try:
                matched_user = User.objects.get(email=uname_or_email)
                user = authenticate(request, username=matched_user.username, password=upass)
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=uname_or_email, password=upass)

        if user is not None:
            login(request, user)
            try:
                profile = user.userprofile
                if profile.role and profile.role.lower() == 'seller':
                    return redirect('seller_dashboard')
                elif profile.role and profile.role.lower() == 'admin':
                    return redirect('admin_dashboard')
                else:
                    if user.is_superuser:
                        return redirect('admin_dashboard')
                    return redirect('customer_dashboard')
            except UserProfile.DoesNotExist:
                if user.is_superuser:
                    return redirect('admin_dashboard')
                return redirect('customer_dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid Credentials'})

    return render(request, 'login.html')

@login_required
def admin_dashboard(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'add_category':
            name = request.POST.get('category_name')
            if name:
                Category.objects.create(name=name)
        elif form_type == 'add_subcategory':
            cat_id = request.POST.get('category_id')
            name = request.POST.get('subcategory_name')
            if cat_id and name:
                category = Category.objects.get(id=cat_id)
                SubCategory.objects.create(category=category, name=name)
        elif form_type == 'add_product':
            subcat_id = request.POST.get('subcategory_id')
            name = request.POST.get('product_name')
            price = request.POST.get('price')
            image = request.FILES.get('image')
            if subcat_id and name and price:
                subcat = SubCategory.objects.get(id=subcat_id)
                Product.objects.create(sub_category=subcat, name=name, price=price, image=image, available=True)
        elif form_type == 'toggle_product':
            prod_id = request.POST.get('product_id')
            if prod_id:
                product = Product.objects.get(id=prod_id)
                product.available = not product.available 
                product.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'available': product.available})
        elif form_type == 'update_order_status':
            order_id = request.POST.get('order_id')
            new_status = request.POST.get('new_status')
            if order_id and new_status:
                order = Order.objects.get(id=order_id)
                order.status = new_status
                order.save()
        
        return redirect('admin_dashboard')

    context = {
        'customers': UserProfile.objects.filter(role__iexact='Customer'),
        'sellers': UserProfile.objects.filter(role__iexact='seller'),
        'categories': Category.objects.all(),
        'subcategories': SubCategory.objects.all(),
        'products': Product.objects.all(),
        'orders': Order.objects.exclude(status__iexact='Cancelled'),
        'carts': Cart.objects.all(),
        'cart_items': CartItem.objects.all(),
        'order_items': OrderItem.objects.all(),
        'feedbacks': OrderFeedback.objects.all().order_by('-created_at'),
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def customer_dashboard(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'direct_order':
            prod_id = request.POST.get('product_id')
            if prod_id:
                product = Product.objects.get(id=prod_id)
                order = Order.objects.create(
                    customer=request.user,
                    total_amount=product.price,
                    status='Pending'
                )
                OrderItem.objects.create(order=order, product=product, quantity=1, price_at_time=product.price)
                messages.success(request, f"Order placed successfully! Item: 1 x {product.name} | Total: ₹{product.price}")
        
        elif form_type == 'add_to_cart':
            prod_id = request.POST.get('product_id')
            if prod_id:
                product = Product.objects.get(id=prod_id)
                cart, _ = Cart.objects.get_or_create(user=request.user)
                cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
                if not created:
                    cart_item.quantity += 1
                    cart_item.save()
                messages.success(request, f"{product.name} added to cart!")
        
        elif form_type == 'clear_cart':
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                CartItem.objects.filter(cart=cart).delete()
                messages.success(request, "Your cart has been cleared.")

        elif form_type == 'checkout':
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_items_qs = CartItem.objects.filter(cart=cart)
                if cart_items_qs.exists():
                    total_amt = sum(item.product.price * item.quantity for item in cart_items_qs)
                    order = Order.objects.create(
                        customer=request.user,
                        total_amount=total_amt,
                        status='Pending'
                    )
                    item_names = []
                    for item in cart_items_qs:
                        OrderItem.objects.create(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            price_at_time=item.product.price
                        )
                        item_names.append(f"{item.quantity} x {item.product.name}")
                    cart_items_qs.delete()
                    items_str = ", ".join(item_names)
                    messages.success(request, f"Order placed successfully! Items: {items_str} | Total: ₹{total_amt}")
        
        elif form_type == 'submit_feedback':
            order_id = request.POST.get('order_id')
            rating = request.POST.get('rating')
            comment = request.POST.get('comment')
            if order_id and rating:
                order = Order.objects.get(id=order_id)
                OrderFeedback.objects.update_or_create(
                    order=order,
                    defaults={
                        'customer': request.user,
                        'rating': rating,
                        'comment': comment
                    }
                )
                messages.success(request, "Thank you! Your feedback has been submitted.")
        
        elif form_type == 'cancel_order':
            order_id = request.POST.get('order_id')
            if order_id:
                order = Order.objects.filter(id=order_id, customer=request.user, status='Pending').first()
                if order:
                    order.status = 'Cancelled'
                    order.save()
                    messages.success(request, f"Order #{order.id} has been cancelled successfully.")
        
        return redirect('customer_dashboard')

    cart = Cart.objects.filter(user=request.user).first()
    cart_items = []
    if cart:
        raw_cart_items = CartItem.objects.filter(cart=cart)
        for item in raw_cart_items:
            item.item_total = item.product.price * item.quantity
            cart_items.append(item)

    user_orders = Order.objects.filter(customer=request.user).exclude(status__iexact='Cancelled').order_by('-id')
    for ord in user_orders:
        ord.feedback_obj = OrderFeedback.objects.filter(order=ord).first()

    context = {
        'categories': Category.objects.all(),
        'subcategories': SubCategory.objects.all(),
        'products': Product.objects.all(),
        'cart_items': cart_items,
        'orders': user_orders,
    }
    return render(request, 'customer_dashboard.html', context)

@login_required
def seller_dashboard(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'update_order_status':
            order_id = request.POST.get('order_id')
            new_status = request.POST.get('new_status')
            if order_id and new_status:
                order = Order.objects.get(id=order_id)
                order.status = new_status
                order.save()
        elif form_type == 'toggle_product':
            prod_id = request.POST.get('product_id')
            if prod_id:
                product = Product.objects.get(id=prod_id)
                product.available = not product.available 
                product.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'available': product.available})
        return redirect('seller_dashboard')

    orders = Order.objects.exclude(status__iexact='Cancelled').order_by('-id')
    context = {
        'orders': orders,
        'products': Product.objects.all(),
        'categories': Category.objects.all(),
        'subcategories': SubCategory.objects.all(),
        'customers': UserProfile.objects.filter(role__iexact='Customer'),
        'feedbacks': OrderFeedback.objects.all().order_by('-created_at'),
    }
    return render(request, 'seller_dashboard.html', context)

def logout_view(request):
    logout(request)
    return redirect('login_url')