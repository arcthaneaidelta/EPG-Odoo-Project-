import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Update ALL countries address format: State -> City -> Zip"""
    # New Format: Street 1, Street 2, State, City, Zip, Country
    new_format = "%(street)s\n%(street2)s\n%(state_name)s %(city)s %(zip)s\n%(country_name)s"
    
    countries = env['res.country'].search([])
    if countries:
        countries.write({'address_format': new_format})
        _logger.info("CRM Base: Global address format updated for %s countries", len(countries))
