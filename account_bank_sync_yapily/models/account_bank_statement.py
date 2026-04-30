import logging
import requests
import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests.auth

_logger = logging.getLogger(__name__)

class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @api.model
    def _cron_sync_yapily_accounts(self, journals=None):
        if not journals:
            journals = self.env['account.journal'].search([
                ('yapily_consent_token', '!=', False),
                ('yapily_account_id', '!=', False)
            ])
            
        for journal in journals:
            try:
                company = journal.company_id
                app_uuid = company.yapily_application_uuid
                secret = company.yapily_secret
                base_url = company.yapily_api_url or "https://api.yapily.com"
                
                if not app_uuid or not secret:
                    _logger.warning("Yapily credentials not configured for company %s", company.name)
                    continue
                    
                self._sync_journal_yapily(journal, app_uuid, secret, base_url)
            except Exception as e:
                _logger.error("Error syncing Yapily for journal %s: %s", journal.id, str(e))

    @api.model
    def _sync_journal_yapily(self, journal, app_uuid, secret, base_url):
        # API requires Basic Auth: uuid:secret
        auth = requests.auth.HTTPBasicAuth(app_uuid, secret)
        headers = {
            'Consent': journal.yapily_consent_token,
        }
        
        # Calculate from limit
        # Default fetch from last sync or 89 days back to comply with strict PSD2 institution limits
        from_date = journal.yapily_last_sync_date or (datetime.now() - timedelta(days=89))
        from_date_str = from_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        url = f"{base_url}/accounts/{journal.yapily_account_id}/transactions"
        params = {
            'from': from_date_str,
            'limit': 1000
        }
        
        response = requests.get(url, headers=headers, auth=auth, params=params)
        
        if response.status_code != 200:
            raise UserError(_("Yapily API HTTP Error %s: %s") % (response.status_code, response.text))
            
        data = response.json()
        transactions = data.get('data', [])
        
        if not transactions:
            journal.yapily_last_sync_date = fields.Datetime.now()
            raise UserError(f"Yapily returned 0 transactions. Response payload: {str(data)[:500]}")
            
        # Create bank statement for this sync
        statement_vals = {
            'name': f"Yapily Sync {fields.Date.today()}",
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'line_ids': []
        }
        
        skipped_status = set()
        
        for txn in transactions:
            txn_id = txn.get('id')
            # Skip if we already have it
            existing_line = self.env['account.bank.statement.line'].search([
                ('unique_import_id', '=', txn_id),
                ('journal_id', '=', journal.id)
            ], limit=1)
            
            if existing_line:
                continue
                
            amount = float(txn.get('amount', 0))
            txn_amount_details = txn.get('transactionAmount', {})
            amount = txn_amount_details.get('amount', amount)
            
            if txn.get('status') not in ('BOOKED', 'COMPLETED'):
                skipped_status.add(txn.get('status'))
                continue # Skip pending transactions
                
            date_str = txn.get('date')[:10] if txn.get('date') else fields.Date.today().strftime('%Y-%m-%d')
            
            statement_vals['line_ids'].append((0, 0, {
                'date': date_str,
                'payment_ref': txn.get('description', txn.get('reference', 'Yapily Txn')),
                'amount': amount,
                'unique_import_id': txn_id,
            }))
            
        if not statement_vals['line_ids']:
            raise UserError(f"0 lines processed out of {len(transactions)} fetched transactions. Skipped statuses: {skipped_status}")
            
        if statement_vals['line_ids']:
            statement = self.env['account.bank.statement'].create(statement_vals)
            _logger.info("Created Statement %s with %s lines", statement.id, len(statement_vals['line_ids']))
            
        journal.yapily_last_sync_date = fields.Datetime.now()


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    unique_import_id = fields.Char(string='Import ID', readonly=True, copy=False)
