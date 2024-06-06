from django.shortcuts import render
import requests
from datetime import datetime
from xml.etree import ElementTree as et



def token(request):
    get_token = requests.post('https://shipment.xpressbees.com/api/users/login', json={"email": "supriyochowdhury001@gmail.com", "password": "Supriyo"}).json()
    bearer_token2 = get_token['data']
    return bearer_token2



def convert_datetime(datetime_str):
    input_format = "%d %b, %Y, %H:%M"
    output_format = "%d/%m/%Y, %I:%M %p"
    dt = datetime.strptime(datetime_str.strip(), input_format)
    formatted_date = dt.strftime(output_format)
    return formatted_date


def convert_date(date_str):
    input_format = "%d-%b-%Y"
    output_format = "%d/%m/%Y"
    dt = datetime.strptime(date_str.strip(), input_format)
    return dt.strftime(output_format)


def ecom_tracking(request, awb):
    try:
        # url = "https://clbeta.ecomexpress.in/track_me/api/mawbd/"
        # payload={'username': 'internaltest_staging',
        # 'password': '@^2%d@xhH^=9xK4U',
        # 'awb': '114970250'}
        # files=[]
        # headers = {}
        # response = requests.request("POST", url, headers=headers, data=payload, files=files)
        root = et.parse('C:\\Users\\Supriyo\\Desktop\\SWS\\courier\\tracking\\myxml.xml').getroot()
        awb_info = {}
        for field in root.findall(".//object[@model='awb']/field"):
            field_name = field.attrib['name']
            field_value = field.text
            
            # Convert the expected_date field
            if field_name == 'expected_date':
                awb_info[field_name] = convert_date(field_value) if field_value else 'Will be available soon'
            else:
                awb_info[field_name] = field_value
        
        
        
        scan_stages = []
        for scan in root.findall(".//object[@model='scan_stages']"):
            scan_info = {}
            for field in scan.findall('field'):
                if field.attrib['name'] == 'updated_on':
                    scan_info[field.attrib['name']] = convert_datetime(field.text)
                elif field.attrib['name'] == 'status' and field.text == 'Soft data uploaded':
                    scan_info[field.attrib['name']] = 'Parcel booked'
                else:
                    scan_info[field.attrib['name']] = field.text
            scan_stages.append(scan_info)
        return render(request, 'ecomtracking.html', {'all_messages': scan_stages, 'awb': awb_info})
    except:
        data = "Something went wrong!"
        return render(request, 'ecomtracking.html', {'all_messages': data})



def tracking(request, awb):
    try:
        bearer_token = token(request)
        get_tracking = requests.get('https://shipment.xpressbees.com/api/shipments2/track/' + awb, headers={"Authorization": f"Bearer {bearer_token}"}).json()
        data = get_tracking['data']['history']
        if data == [{"status": True}]:
            data = "Please check after sometime"
            return data
        else:
            for item in data:
                parts = item['location'].split(', ')
                if len(parts) > 1:
                    item['location'] = parts[1] + ', ' + parts[2]
                    event_time = datetime.strptime(item['event_time'], '%Y-%m-%d %H:%M')
                    item['event_time'] = event_time.strftime('%d/%m/%Y %I:%M %p').lstrip("0").replace(" 0", " ")
                    if item['message'] == 'Data Received':
                        item['message'] = 'Order Booked'
                    elif item['message'] == 'Reached At Destination':
                        item['message'] = 'Reached at Nearest Hub'
            return data
    except:
        data = "Something went wrong!"
        return data



def direct_link(request, awb):
    awb_len = len(awb)
    if awb_len == 10 or awb_len == 14:
        if awb_len > 10:
            data = tracking(request, awb)
            return render(request, 'dlt.html', {'all_messages': data})
        else:
            return ecom_tracking(request, awb)
    else:
        data = "Something went wrong!"
        return render(request, 'dlt.html', {'all_messages': data})


def create_link(request):
    return render(request, 'create_link.html')



def enter_pin(request):
    return render(request, 'pin-check.html')


def enter_pickup_pin(request):
    return render(request, 'pickup-check.html')


def ecom_pin_check(pincode):
    url = "https://api.ecomexpress.in/apiv2/pincode/"
    payload={'username': 'SUPRIYOCHOWDHURY229756',
    'password': 'A0H8FTfAE6',
    'pincode': pincode}
    files=[]
    headers = {}
    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    return response.json()[0]['active']


def pin_check(request, pinCode):
    try:
        pinLength = len(pinCode)
        if pinLength == 6:
            try:
                ecom_pin_check(pincode=pinCode)
                message = f"{pinCode}: Ecom service is available 🤩"
                return render(request, 'pin-check.html', context={'message': message})
            except:
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
                    message = f"{pinCode}: Xpressbees service is available 🤩"
                    return render(request, 'pin-check.html', context={'message': message})
                else:
                    message = f"{pinCode}: Not serviceable by both Ecom & Xpressbees 😔"
                    return render(request, 'pin-check.html', context={'message': message})
        else:
            message = "Not valid! Please enter 6 character valid Pincode 😐"
            return render(request, 'pin-check.html', context={'message': message})
    except:
        message = "Something went wrong, please contact administrator 😐"
        return render(request, 'pin-check.html', context={'message': message})
    


def pickup_check(request, pinCode):
    try:
        pinLength = len(pinCode)
        if pinLength == 6:
            bearer_token = token(request)
            url = str(requests.post(
            'https://shipment.xpressbees.com/api/courier/serviceability', 
            headers={"Authorization": f"Bearer {bearer_token}"}, 
            json={"origin" : f"{pinCode}",
            "destination" : "700056",
            "payment_type" : "cod",
            "order_amount" : "999",
            }).json()['status'])
            if url == "True":
                message = f"{pinCode}: Home pickup available 🤩"
                return render(request, 'pickup-check.html', context={'message': message})
            else:
                message = f"{pinCode}: Pickup not available 😔"
                return render(request, 'pickup-check.html', context={'message': message})
        else:
            message = "Not valid! Please enter 6 character valid Pincode 😐"
            return render(request, 'pickup-check.html', context={'message': message})
    except:
        message = "Something went wrong, please contact administrator 😐"
        return render(request, 'pickup-check.html', context={'message': message})