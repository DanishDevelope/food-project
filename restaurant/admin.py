from django.contrib import admin
from .models import UserProfile, Category, SubCategory, Product, Cart, CartItem, Order, OrderItem

admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)