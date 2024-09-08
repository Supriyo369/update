from django.shortcuts import render, redirect
import requests, os, json
from clients.backends import Clients, Orders, Centralized
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User as auth_user
from clients.forms import LoginForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from clients.utility import sws_charge, company_rates
from clients.utils import DecimalEncoder
from django.core.cache import cache
from django.http import HttpResponse
from clients.generate_labels import *
from clients.sws_profit import *
from clients.sws_COD_ledger import *
from decimal import Decimal


@login_required
def labels_page(request):
    if request.method == 'POST':
        awbs_string = request.POST.get('awbs', '')
        awbs = awbs_string.split(',')
        url = 'https://shipment.xpressbees.com/api/shipments2/manifest'
        token = btoken()
        response = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json={"awbs": awbs}).text
    user_orders = Orders.objects.filter(username=request.user.username).exclude(awb__isnull=True).exclude(awb__exact='').order_by('id').reverse()[:30]
    return render(request, "labels.html", {'user_orders': user_orders})

@login_required
def all_orders(request):
    user_orders = Orders.objects.filter(username=request.user.username).order_by('id').reverse()[:50]
    return render(request, "allorders.html", {'user_orders': user_orders})

@login_required
def dashboard(request):
    user = Clients.objects.get(username=request.user.username)
    name = user.name
    wallet = user.wallet
    return render(request, "dashboard.html", {'name': name, 'wallet': wallet})

@login_required
def recharge(request):
    user = Clients.objects.get(username=request.user.username)
    name = user.name
    wallet = user.wallet
    return render(request, "recharge.html", {'name': name, 'wallet': wallet})


@login_required
def download_labels(request):
    if request.method == 'POST':
        awbs_string = request.POST.get('awbs', '')
        awbs = awbs_string.split(',')
        url = 'https://shipment.xpressbees.com/api/shipments2/manifest'
        token = btoken()
        response = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json={"awbs": awbs}).text
        labels_data = []
        for awb in awbs:
            try:
                order = Orders.objects.get(awb=awb)
                labels_data.append({
                    'to_name': order.name,
                    'address_line': order.address,
                    'barcode_data': order.awb,
                    'mop': order.mode_of_payment,
                    'price': order.price,
                    'from_name': order.booked_by_raw_name,
                    'from_mob': order.booked_mob_no
                })
            except Orders.DoesNotExist:
                print(f'Order with AWB {awb} does not exist.')
        
        if not labels_data:
            raise ValueError("No valid orders found for the given AWBs.")


    
    pdf_filename = generate_shipping_labels(labels_data)
    
    response = HttpResponse(open(pdf_filename, 'rb').read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
    
    # Cleanup files after sending response
    cleanup_files(pdf_filename)
    
    return response

def login_view(request):
    nxt = request.GET.get('next')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if nxt != None:
                    return redirect(nxt)
                else:
                    return redirect('/dashboard/')
            else:
                try:
                    check_ph = auth_user.objects.get(username=username)
                    messages.error(request, "Incorrect Password!")
                    return redirect('/login/')

                except:
                    messages.error(request, "Invalid Username!")
                    return redirect('/login/')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})



def btoken():
    token = cache.get('xpressbees_token')
    TOKEN_URL = 'https://shipment.xpressbees.com/api/users/login'
    if not token:
        get_token = requests.post(TOKEN_URL, json={"email": "supriyochowdhury001@gmail.com", "password": "Supriyo"}).json()
        token = get_token['data']
        cache.set('xpressbees_token', token, timeout=10500)  
    return token



def dateTime(): 
    from django.utils import timezone
    now = timezone.localtime(timezone.now())
    # Get hour in 12-hour format without leading zero
    hour = now.strftime('%I').lstrip('0')
    formatted_time = now.strftime(f'%d/%m/%Y {hour}:%M %p')
    return formatted_time




@login_required
def create_order(request):
    if request.method == 'POST':
        user = Clients.objects.get(username=request.user.username)
        so = Orders()
        get_company_rates = company_rates(user.pincode, request.POST['pincode'], request.POST['mode-of-payment'], request.POST['price'], request.POST.get('hcw'))
        so.name = customer = request.POST['name']
        so.username = request.user.username
        so.address = request.POST['address']
        so.pincode = request.POST['pincode']
        so.city = request.POST['city']
        so.state = delivery_state = request.POST['state']
        so.phone = request.POST['phone-no']
        if request.POST['alt-phone-no'] != "":
            so.alt_phone = request.POST['alt-phone-no']
        else:
            pass
        so.length = request.POST['length']
        so.width = request.POST['width']
        so.height = request.POST['height']
        so.weight = chargeable_weight = request.POST.get('hcw')
        so.price = price = request.POST['price']
        so.mode_of_payment = mop = request.POST['mode-of-payment']
        so.booked_by = user.name + " SWS"
        so.booked_by_raw_name = user.name
        so.booked_mob_no = user.phone
        so.company_charge = company_charge = get_company_rates['charge']
        get_sws_charge = so.sws_charge = sws_charge(request.user.username, chargeable_weight, user.pickup_state, delivery_state, mop, price)
        user.total_company_charge = float(user.total_company_charge) + company_charge
        user.total_sws_charge = user.total_sws_charge + get_sws_charge
        profit = so.sws_profit = float(get_sws_charge) - company_charge

        if int(company_charge) > int(get_sws_charge):
            messages.error(request, "Issue with delivery location ( E-1 ). Please contact Owner")
            return redirect('/dashboard/')
        
        if user.wallet <= 35:
            messages.error(request, "Not enough balance in Wallet! Please recharge.")
            return redirect('/recharge/')
        else:
            get_order_id = Centralized.objects.all()[0]
            so.order_id = get_order_id.order_id = order_id = get_order_id.order_id + 1
            courier_id = get_company_rates['id']
            so.save()
            user.save()
            get_order_id.save()
        return render(request, 'courier_charges.html', {'charges': get_sws_charge, 'customer': customer, 'order_id': order_id, 'courier_id': courier_id})
    
    else:
        user = Clients.objects.get(username=request.user.username)
        if user.wallet <= 35:
                messages.error(request, "Not enough balance in Wallet! Please recharge.")
                return redirect('/recharge/')
        else:
            return render(request, 'booking.html')



def book(request):
    if request.method == 'POST':
        user = Clients.objects.get(username=request.user.username)
        get_order_id = request.POST['order_id']
        get_courier_id = request.POST['courier_id']
        order = Orders.objects.get(order_id=get_order_id)
        bearer_token = btoken()
        url = "https://shipment.xpressbees.com/api/shipments2"
        payload = {
            "order_number": "#001",
            'payment_type': order.mode_of_payment,
            'order_amount': order.price,
            'consignee': {
                "name": order.name,
                "address": order.address,
                "city": order.city,
                "state": order.state,
                "pincode": order.pincode,
                "phone": order.phone
            },
            "pickup": {
            "warehouse_name": user.name,
            "name" : user.name,
            "address": user.pickup_address,
            "city": user.pickup_city,
            "state": user.pickup_state,
            "pincode": user.pincode,
            "phone": user.phone
            },
             "order_items": [{
            "name": order.booked_by,
            "qty": "1",
            "price": order.price,
            }],
            "package_weight": order.weight,
            "collectable_amount": "0",
            "courier_id" : get_courier_id
        }
        if order.alt_phone:
            payload['consignee']['alt-phone'] = order.alt_phone

        if order.mode_of_payment.lower() == "cod":
            payload["collectable_amount"] = order.price
        
        payload_json = json.dumps(payload, cls=DecimalEncoder)


        try:
            response = requests.post(url, headers={"Authorization": f"Bearer {bearer_token}"}, data=payload_json).text
            json_data = json.loads(response)
            if json_data["status"] == True:
                order.awb = json_data['data']['awb_number']
                user.wallet = user.wallet - order.get_sws_charge
                order.created_on = dateTime()
                order.save()
                user.save()
                try:
                    append_to_google_sheet_for_sws_profit(f'="{order.created_on}"', order.booked_by_raw_name, int(order.company_charge), int(order.sws_charge))
                    try:
                        if order.mode_of_payment.lower() == "cod":
                            price = float(order.price) if isinstance(order.price, Decimal) else order.price  # Convert Decimal to float
                            append_to_google_sheet_for_COD(f'="{order.created_on}"', order.booked_by_raw_name, order.name, price, request.user.username)
                        messages.success(request, f'Order successfully booked for: {order.name}')
                        return redirect('/booking/')
                    except:
                        messages.error(request, "Failed to book order! (E-5). Contact Owner.")
                        return redirect('/dashboard/')
                except:    
                    messages.error(request, "Failed to book order! (E-4). Contact Owner.")
                    return redirect('/dashboard/')
            else:
                messages.error(request, "Failed to book order! (E-2). Contact Owner.")
                return redirect('/dashboard/')
            
        except:
            messages.error(request, "Failed to book order! (E-3). Contact Owner.")
            return redirect('/dashboard/')
        
    




@login_required
def pending_orders(request):
    user = Orders.objects.filter(username=request.user.username, awb__isnull=True)
    return render(request, 'pending-orders.html', {'orders': user})




def get_city_state(request):
    user = Clients.objects.get(username=request.user.username)
    pincode = request.GET.get('pincode')
    bearer_token = btoken()
    url = str(requests.post(
    'https://shipment.xpressbees.com/api/courier/serviceability', 
    headers={"Authorization": f"Bearer {bearer_token}"}, 
    json={"origin" : f"{user.pincode}",
    "destination" : f"{pincode}",
    "payment_type" : "cod",
    "order_amount" : "999",
    }).json()['status'])
    if url == "True":
        file_path = os.path.join(os.path.dirname(__file__), 'pincode_data.json')
        with open(file_path, 'r') as json_file:
            pincode_data = json.load(json_file)          
        if pincode in pincode_data:
            return JsonResponse({
                'success': True,
                'city': pincode_data[pincode]['City'],
                'state': pincode_data[pincode]['State'],
            })

    return JsonResponse({'success': False, 'error': 'Pincode not found'})


def pincode(request):
    return render(request, 'pincode.html')





