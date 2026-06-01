import requests
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class CurrencyUpdater(models.AbstractModel):
    _name = 'real.estate.currency.updater'
    _description = 'Automatic Currency Updater'

    @api.model
    def run_currency_update(self):
        main_currency = self.env.company.currency_id
        if not main_currency:
            return

        # Fetch from API
        api_url = f"https://open.er-api.com/v6/latest/{main_currency.name}"
        try:
            response = requests.get(api_url, timeout=10)
            data = response.json()
        except Exception:
            return

        if data.get('result') != 'success':
            return

        active_currencies = self.env['res.currency'].search([('active', '=', True)])
        
        for currency in active_currencies:
            if currency == main_currency:
                continue

            new_rate = data['rates'].get(currency.name)
            if new_rate:
                # FIX: Check if rate exists for TODAY before creating
                existing_rate = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currency.id),
                    ('name', '=', fields.Date.today()),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)

                if existing_rate:
                    # Update existing record
                    existing_rate.write({'rate': new_rate})
                else:
                    # Create new record
                    self.env['res.currency.rate'].create({
                        'currency_id': currency.id,
                        'rate': new_rate,
                        'name': fields.Date.today(),
                        'company_id': self.env.company.id,
                    })