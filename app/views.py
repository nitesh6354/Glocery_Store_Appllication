from django.http import JsonResponse
from django.db.models import Count
from django.shortcuts import render,redirect
import razorpay
from django.views import View
from . models import Product,Customer,Cart,Payment,OrderPlaced
from django.contrib.auth.decorators import login_required
from . forms import CustomerProfileForm,CustomerRegistrationForm
from django.contrib import messages
from django.http import Http404
from django.db.models import Q
from django.conf import settings



# Create your views here.

def home(request):
    return render(request,"app/home.html")

def about(request):
    return render(request,"app/about.html")

def contact(request):
    return render(request,"app/contact.html")



class CategoryView(View):
    def get(self,request,val): 
        product=Product.objects.filter(category=val)
        title=Product.objects.filter(category=val).values('title')
        return render(request,"app/category.html",locals())

class CategoryTitle(View):
    def get(self,request,val):
        product=Product.objects.filter(title=val)
        title=Product.objects.filter(category=product[0].category).values('title')
        return render(request,"app/category.html",locals())

class ProductDetail(View):
    def get(self,request,pk):
        product=Product.objects.get(pk=pk)
        return render(request,"app/productdetail.html",locals())

class CustomerRegistraionView(View):
    def get(self,request):
        form=CustomerRegistrationForm()
        return render(request,'app/customerregistration.html',locals())
    def post(self,request):
        form=CustomerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Congratulation ! User Register Successfully")
        else:
            messages.warning(request,"Invalid Input data")
        return render(request,'app/customerregistration.html',locals())
    
class ProfileView(View):
    def get(self,request):
        form =CustomerProfileForm()
        return render(request,'app/profile.html',locals())
    def post(self,request):
        form=CustomerProfileForm(request.POST)
        if form.is_valid():
            user=request.user
            name=form.cleaned_data['name']
            locality=form.cleaned_data['locality']
            city=form.cleaned_data['city']
            mobile=form.cleaned_data['mobile']
            state=form.cleaned_data['state']
            zipcode=form.cleaned_data['zipcode']

            reg= Customer(user=user,name=name,locality=locality,mobile=mobile,city=city,state=state,
            zipcode=zipcode)
            reg.save()
            messages.success(request,"Congratulations! Profile Save Successfully")
        else:
            messages.warning(request,"Invalid Input Data")
        return render(request,'app/profile.html',locals())

def address(request):
    add=Customer.objects.filter(user=request.user)
    return render(request,'app/address.html',locals())

class updateAddress(View):
    def get(self,request,pk):
        add=Customer.objects.get(pk=pk)
        form=CustomerProfileForm(instance=add)
        return render(request,'app/updateAddress.html',locals())
    def post(self,request,pk):
        form=CustomerProfileForm(request.POST)
        if form.is_valid():
            add=Customer.objects.get(pk=pk)
            add.name=form.cleaned_data['name']
            add.locality=form.cleaned_data['locality']
            add.city=form.cleaned_data['city']
            add.mobile=form.cleaned_data['mobile']
            add.state=form.cleaned_data['state']
            add.zipcode=form.cleaned_data['zipcode']
            add.save()
            messages.success(request,"Congratulation ! Profile Update Successfully")
        else:
            messages.warning(request,"Invalid Input Data")
        return redirect("address")
            
def add_to_cart(request):
    user=request.user 
    product_id=request.GET.get('prod_id')
    product=Product.objects.get(id=product_id)
    Cart(user=user,product=product).save()
    return redirect("/cart")
            
def show_cart(request):
    user=request.user
    cart=Cart.objects.filter(user=user)

    amount=0
    for p in cart:
        value=p.quantity * p.product.discounted_price
        amount=amount +value 
    totalamount=amount + 40 
    return render(request,'app/addtocart.html',locals() )

class checkout(View):
    def get(self,request):
        user=request.user
        add=Customer.objects.filter(user=user)
        cart_items=Cart.objects.filter(user=user)
        famount= 0
        for p in cart_items:
            value=p.quantity + p.product.discounted_price
            famount=famount+ value
        totalamount=famount+40
        razoramount=int(totalamount * 100)
        client=razorpay.Client(auth=(settings.RAZOR_KEY_ID,settings.RAZOR_KEY_SECRET))
        data={"amount":razoramount,"currency":"INR","receipt":"order_rcptid_12"}
        payment_response=client.order.create(data=data)
        print(payment_response)
        
        # {'amount': 37400, 'amount_due': 37400, 'amount_paid': 0, 'attempts': 0, 'created_at': 1745388881, 'currency': 'INR', 'entity': 'order', 'id': 'order_QMOdGKQBM5xVwq', 'notes': [], 'offer_id': None, 'receipt': 'order_rcptid_12', 'status': 'created'}
        
        order_id = payment_response['id']
        order_status = payment_response['status']

        if order_status == 'created':
            payment = Payment(
                user=user,
                amount=totalamount,
                razorpay_order_id=order_id,
                razorpay_payment_status=order_status
            )
            payment.save()
        return render(request,'app/checkout.html',locals())
    
# @login_required
# def payment_done(request):
#     order_id = request.GET.get('order_id')
#     payment_id = request.GET.get('payment_id')
#     cust_id = request.GET.get('cust_id')
#     user = request.user

#     # Get customer instance
#     customer = Customer.objects.get(id=cust_id)

#     # Update payment info
#     payment = Payment.objects.get(razorpay_order_id=order_id)
#     payment.paid = True
#     payment.razorpay_payment_id = payment_id
#     payment.save()

#     # Save order details
#     cart = Cart.objects.filter(user=user)
#     for c in cart:
#         OrderPlaced(
#             user=user,
#             customer=customer,
#             product=c.product,
#             quantity=c.quantity,
#             payment=payment
#         ).save()
#         c.delete()

#     return redirect("order")

@login_required
def payment_done(request):
    order_id = request.GET.get('order_id')
    payment_id = request.GET.get('payment_id')
    cust_id = request.GET.get('cust_id')

    # Ensure the user is logged in
    if not request.user.is_authenticated:
        return redirect('login')  # Redirect to login page if not authenticated

    try:
        # Get the customer instance
        customer = Customer.objects.get(id=cust_id)
    except Customer.DoesNotExist:
        raise Http404("Customer not found.")

    try:
        # Get payment instance and update payment status
        payment = Payment.objects.get(razorpay_order_id=order_id)
        payment.paid = True
        payment.razorpay_payment_id = payment_id
        payment.save()
    except Payment.DoesNotExist:
        raise Http404("Payment record not found.")

    # Save the order and delete cart items
    cart_items = Cart.objects.filter(user=request.user)
    for item in cart_items:
        OrderPlaced.objects.create(
            user=request.user,
            customer=customer,
            product=item.product,
            quantity=item.quantity,
            payment=payment
        )
        item.delete()  # Deleting cart item after placing the order

    return redirect('home')  # Redirect to orders page


def orders(request):
    order_placed=OrderPlaced.objects.filter(user=request.user)
    return render(request,'app/orders',locals())

 
def plus_cart(request): 
    prod_id = request.GET.get('prod_id')
    
    try:
        cart_item = Cart.objects.filter(Q(product=prod_id) & Q(user=request.user)).first()
        if cart_item:
            cart_item.quantity += 1
            cart_item.save()
        else:
            return JsonResponse({'error': 'Item not found in cart'}, status=404)

        cart = Cart.objects.filter(user=request.user)
        amount = sum(item.quantity * item.product.discounted_price for item in cart)
        totalamount = amount + 40

        data = {
            'quantity': cart_item.quantity,
            'amount': amount,
            'totalamount': totalamount
        }
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def minus_cart(request): 
    prod_id = request.GET.get('prod_id')
    
    try:
        cart_item = Cart.objects.filter(Q(product=prod_id) & Q(user=request.user)).first()
        if cart_item:
            cart_item.quantity -=1
            cart_item.save()
        else:
            return JsonResponse({'error': 'Item not found in cart'}, status=404)

        cart = Cart.objects.filter(user=request.user)
        amount = sum(item.quantity * item.product.discounted_price for item in cart)
        totalamount = amount + 40

        data = {
            'quantity': cart_item.quantity,
            'amount': amount,
            'totalamount': totalamount
        }
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def remove_cart(request): 
    prod_id = request.GET.get('prod_id')
    
    try:
        cart_item = Cart.objects.filter(Q(product=prod_id) & Q(user=request.user)).first()
        if cart_item:
            cart_item.delete()
        else:
            return JsonResponse({'error': 'Item not found in cart'}, status=404)

        cart = Cart.objects.filter(user=request.user)
        amount = sum(item.quantity * item.product.discounted_price for item in cart)
        totalamount = amount + 40

        data = {
            'amount': amount,
            'totalamount': totalamount
        }
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

