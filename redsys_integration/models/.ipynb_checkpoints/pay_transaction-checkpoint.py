# Part of System. See LICENSE file for full copyright and licensing details.

import logging
import base64
import hashlib
import hmac
import json
import logging
import urllib

from werkzeug import urls
from pprint import pprint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo import http
from odoo.addons.payment import utils as payment_utils
from odoo.tools import config

_logger = logging.getLogger(__name__)

try:
    from Crypto.Cipher import DES3
except ImportError:
    _logger.info("Dependencia no encontrada (pycryptodome).")

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    redsys_payment_ref = fields.Char(string="Referencia de pago de Redsys")
    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Redsys-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)

        if self.provider_code != 'redsys' and self.provider_code != 'bizum':

            return res

        base_url = self.provider_id.get_base_url()
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)
        sqlTestMethod = """select state from payment_provider where code = '%s'
                        """ % ('redsys')
        http.request.cr.execute(sqlTestMethod)
        resultTestMethod = http.request.cr.fetchall() or []
        if resultTestMethod:
            (state) = resultTestMethod[0]
        for testMethod in state:
            test = testMethod
        testPayment = 'true' if test == 'test' \
            else 'false'
        lang = 'es' if self.partner_lang == 'es_CO' else 'en'
        split_reference = self.reference.split('-')
        reference = split_reference[0]
        sql = """select amount_tax from sale_order where name = '%s'
                        """ % (reference)
        http.request.cr.execute(sql)
        result = http.request.cr.fetchall() or []
        if not result:
            reference = self.reference
            sql = """select amount_tax from sale_order where name = '%s'
                        """ % (reference)
            http.request.cr.execute(sql)
            result = http.request.cr.fetchall() or []
            if result:
                (amount_tax) = result[0]
        else:
            (amount_tax) = result[0]        
        for tax_amount in amount_tax:
            tax = tax_amount
        
        values = {
            "Ds_Sermepa_Url": self.provider_id._redsys_get_api_url(),
            "Ds_Merchant_Amount": str(int(round(self.amount * 100))),
            "Ds_Merchant_Currency": self.provider_id.redsys_currency or "978",
            "Ds_Merchant_Order": (
                str(self.reference) and "SYSTEM-"+str(self.reference)[-12:] or False
            ),
            "Ds_Merchant_MerchantCode": (
                self.provider_id.redsys_merchant_code and self.provider_id.redsys_merchant_code[:9]
            ),
            "Ds_Merchant_Terminal": self.provider_id.redsys_terminal or "1",
            "Ds_Merchant_TransactionType": (self.provider_id.redsys_transaction_type or "0"),
            "Ds_Merchant_Titular": partner_first_name + ' '+ partner_last_name,
            "Ds_Merchant_MerchantName": (
                self.provider_id.redsys_merchant_name and self.provider_id.redsys_merchant_name[:25]
            ),
            "Ds_Merchant_MerchantUrl": (
                "%s/payment/redsys/return" % (base_url)
            )[:250],
            "Ds_Merchant_MerchantData": self.provider_id.redsys_merchant_data or "",
            "Ds_Merchant_ProductDescription": (
                self._product_description(str(self.reference))
                or self.provider_id.redsys_merchant_description
                and self.provider_id.redsys_merchant_description[:125]
            ),
            "Ds_Merchant_ConsumerLanguage": (self.provider_id.redsys_merchant_lang or "001"),
            "Ds_Merchant_UrlOk": urls.url_join(base_url, '/payment/redsys/result/redsys_result_ok'),
            "Ds_Merchant_UrlKo": urls.url_join(base_url, '/payment/redsys/result/redsys_result_ko'),
            "Ds_Merchant_Paymethods": self.provider_id.redsys_pay_method or "T",
        }
        
        #_logger.info(values)
        
        merchant_parameters = self._url_encode64(json.dumps(values))
        
        return {
                "Ds_SignatureVersion": str(self.provider_id.redsys_signature_version),
                "Ds_MerchantParameters": merchant_parameters.decode("utf-8"),
                "Ds_Signature": self.sign_parameters(
                    self.provider_id.redsys_secret_key, merchant_parameters.decode("utf-8")
                ),
                'api_url': self.provider_id._redsys_get_api_url(),
            }
        """return {
            'public_key': self.provider_id.redsys_public_key,
            'address1': self.partner_address,
            'amount': self.amount,
            'tax': tax,
            'base_tax': base_tax,
            'city': self.partner_city,
            'country': self.partner_country_id.code,
            'currency_code': self.currency_id.name,
            'email': self.partner_email,
            'first_name': partner_first_name,
            'last_name': partner_last_name,
            "phone_number":'',
            'lang': lang,
            'checkout_external': external,
            "test": testPayment,
            'confirmation_url': urls.url_join(base_url, '/redsys/confirmation/backend'),
            'response_url': urls.url_join(base_url,'/redsys/redirect/backend'),
            'api_url': 'https://sis-t.redsys.es:25443/sis/realizarPago/',
            'extra1': str(tx.id),
            'extra2': self.reference,
            'reference': str(reference),
            "Ds_SignatureVersion": '12345',
            "Ds_MerchantParameters": self._url_encode64(json.dumps(values)),
            "Ds_Signature": '123435',

        }"""

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        _logger.info("TX_FROM_FEEDBACK_DATA")
        _logger.info(data)
        """ Override of payment to find the transaction based on Paypal data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        #tx = super()._get_tx_from_feedback_data(provider, data)

        if provider != 'redsys' and provider != 'bizum':

            return tx
        try:
            parameters = data.get("Ds_MerchantParameters", "")
            parameters_dic = json.loads(base64.b64decode(parameters).decode())
            reference = urllib.parse.unquote(parameters_dic.get("Ds_Order", ""))
            pay_id = parameters_dic.get("Ds_AuthorisationCode")
            shasign = data.get("Ds_Signature", "").replace("_", "/").replace("-", "+")
            test_env = config["test_enable"]
            _logger.info(parameters_dic)
            _logger.info(reference)
            _logger.info(pay_id)
            _logger.info(test_env)
            if not reference or not pay_id or not shasign:
                error_msg = (
                    "Redsys: received data with missing reference"
                    " (%s) or pay_id (%s) or shashign (%s)" % (reference, pay_id, shasign)
                )
                if not test_env:
                    _logger.info(error_msg)
                    raise ValidationError(error_msg)
            
            tx = self.env['payment.transaction'].search([('reference', '=', reference)])
            if not tx or len(tx) > 1:
                error_msg = "Redsys: received data for reference %s" % (reference)
                if not tx:
                    error_msg += "; no order found"
                else:
                    error_msg += "; multiple order found"
                if not test_env:
                    _logger.info(error_msg)
                    raise ValidationError(error_msg)
                
            if tx and not test_env:
                shasign_check = self.sign_parameters(
                    tx.provider_id.redsys_secret_key, parameters
                )
                if shasign_check != shasign:
                    error_msg = (
                        "Redsys: invalid shasign, received %s, computed %s, "
                        "for data %s" % (shasign, shasign_check, data)
                    )
                    _logger.info(error_msg)
                    raise ValidationError(error_msg)
                
        except Exception as e:
            raise ValidationError(
                    "Redsys: " + _("No transaction found")
                )
        return tx

    def _process_feedback_data(self, data):
        _logger.info("PROCESS_FEEDBACK_DATA")
        _logger.info(data)
        """ Override of payment to process the transaction based on Redsys data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        #super()._process_feedback_data(data)

        if self.provider_code != 'redsys' and self.provider_code != 'bizum':

            return
        
        parameters = data.get("Ds_MerchantParameters", "")
        parameters_dic = json.loads(base64.b64decode(parameters).decode())
        reference = urllib.parse.unquote(parameters_dic.get("Ds_Order", ""))
        status_code = int(parameters_dic.get("Ds_Response", "29999"))
        state = self._get_redsys_state(status_code)
        authorisationCode = urllib.parse.unquote(parameters_dic.get("Ds_AuthorisationCode"))
        vals = {
            "state": state,
            "redsys_payment_ref": authorisationCode
        }
        
        tx = ''
        if data:
            sql = """select state from sale_order where name = '%s'
                                        """ % (data.get(reference))
            http.request.cr.execute(sql)
            result = http.request.cr.fetchall() or []
            if result:
                (state) = result[0]
            for testMethod in state:
                tx = testMethod

            if tx not in ['draft']:
                if state not in ["done", "pending"]:
                    self.manage_status_order(data.get(reference), 'sale_order')
                else:
                    if state == 1:
                        self.redsys_payment_ref = authorisationCode
                        self._set_done()
                        self._finalize_post_processing()
            else:
                if state == "done":
                    vals["state_message"] = _("Ok: %s") % parameters_dic.get("Ds_Response")
                    self.redsys_payment_ref = authorisationCode
                    self._set_done()
                    self._finalize_post_processing()
                elif state == "pending":  # 'Payment error: code: %s.'
                    state_message = _("Error: %s (%s)")
                    self._set_pending()
                elif state == "cancel":  # 'Payment error: bank unavailable.'
                    state_message = _("Bank Error: %s (%s)")
                    self.manage_status_order(data.get(reference),'sale_order')
                    self._set_canceled()
                else:
                    state_message = _("Redsys: feedback error %s (%s)")
                    self._set_error(state_message)
            
            self.write(vals)
            return state != "error"

    def _handle_feedback_data(self, provider, data):
        """ Match the transaction with the feedback data, update its state and return it.
        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction
        :rtype: recordset of `payment.transaction`
        """
        tx = self._get_tx_from_feedback_data(provider, data)
        tx._process_feedback_data(data)
        tx._execute_callback()
        return tx

    def query_update_status(self, table, values, selectors):
        """ Update the table with the given values (dict), and use the columns in
            ``selectors`` to select the rows to update.
        """
        UPDATE_QUERY = "UPDATE {table} SET {assignment} WHERE {condition} RETURNING id"
        setters = set(values) - set(selectors)
        assignment = ",".join("{0}='{1}'".format(s, values[s]) for s in setters)
        condition = " AND ".join("{0}='{1}'".format(s, selectors[s]) for s in selectors)
        query = UPDATE_QUERY.format(
            table=table,
            assignment=assignment,
            condition=condition,
        )
        self.env.cr.execute(query, values)
        self.env.cr.fetchall()

    def reflect_params(self, name, confirmation=False):
        """ Return the values to write to the database. """
        if not confirmation:
            return {'name': name}
        else:
            return {'origin': name}

    def manage_status_order(self, order_name, model_name, confirmation=False):
        condition = self.reflect_params(order_name, confirmation)
        params = {'state': 'draft'}
        self.query_update_status(model_name, params, condition)
        self.query_update_status(model_name, {'state': 'cancel'}, condition)
        

    def _url_encode64(self, data):
        data = base64.b64encode(data.encode())
        return data

    def _url_decode64(self, data):
        return json.loads(base64.b64decode(data).decode("utf-8"))

    def sign_parameters(self, secret_key, params64):
        params_dic = self._url_decode64(params64)
        if "Ds_Merchant_Order" in params_dic:
            order = str(params_dic["Ds_Merchant_Order"])
        else:
            order = str(urllib.parse.unquote(params_dic.get("Ds_Order", "Not found")))
        cipher = DES3.new(
            key=base64.b64decode(secret_key), mode=DES3.MODE_CBC, IV=b"\0\0\0\0\0\0\0\0"
        )
        diff_block = len(order) % 8
        zeros = diff_block and (b"\0" * (8 - diff_block)) or b""
        key = cipher.encrypt(str.encode(order + zeros.decode("utf-8")))
        if isinstance(params64, str):
            params64 = params64.encode()
        dig = hmac.new(key=key, msg=params64, digestmod=hashlib.sha256).digest()
        return base64.b64encode(dig).decode("utf-8")
    
    def _product_description(self, order_ref):
        sale_order = self.env["sale.order"].search([("name", "=", order_ref)])
        res = ""
        if sale_order:
            description = "|".join(x.name for x in sale_order.order_line)
            res = description[:125]
        return res        
    
    @api.model
    def _get_redsys_state(self, status_code):
        if 0 <= status_code <= 100:
            return "done"
        elif status_code <= 203:
            return "pending"
        elif 912 <= status_code <= 9912:
            return "cancel"
        else:
            return "error"

