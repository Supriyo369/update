from django.shortcuts import render
import requests

def token(request):
    get_token = requests.post('https://shipment.xpressbees.com/api/users/login', json={"email": "supriyochowdhury001@gmail.com", "password": "Supriyo"}).json()
    bearer_token2 = get_token['data']
    return bearer_token2

def tracking(request, awb):
    try:
        bearer_token = token(request)
        get_tracking = requests.get('https://shipment.xpressbees.com/api/shipments2/track/' + awb, headers={"Authorization": f"Bearer {bearer_token}"}).json()
        all_messages = get_tracking['data']['history']
        return all_messages
    except:
        all_messages = "Invalid AWB"
        return all_messages



def direct_link(request, awb):
    track = tracking(request, awb)
    return render(request, 'dlt.html', {'all_messages': track})


def create_link(request):
    return render(request, 'create_link.html')




def enter_pin(request):
    return render(request, 'pin-check.html')


def pin_check(request, pinCode):
    try:
        pinLength = len(pinCode)
        if pinLength == 6:
            bearer_token = token(request)
            url = str(requests.post(
            'https://shipment.xpressbees.com/api/courier/serviceability', 
            headers={"Authorization": f"Bearer {bearer_token}"}, 
            json={"origin" : "700035",
            "destination" : f"{pinCode}",
            "payment_type" : "cod",
            "order_amount" : "999",
            }).json()['status'])
            if url == "True":
                message = f"{pinCode} pincode is serviceable with COD"
                return render(request, 'pin-check.html', context={'message': message})
            else:
                message = f"{pinCode} pincode is not serviceable."
                return render(request, 'pin-check.html', context={'message': message})
        else:
            message = "Please enter 6 character valid Pincode "
            return render(request, 'pin-check.html', context={'message': message})
    except:
        message = "Something went wrong, please contact administrator"
        return render(request, 'pin-check.html', context={'message': message})