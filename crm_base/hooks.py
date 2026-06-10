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

    # Force Menu Translations (Odoo sometimes stubbornly overwrites these with native base translations)
    menus_to_update = {
        'crm.crm_menu_root': {
            'en_US': 'Pipeline',
            'es_ES': 'Flujo',
        },
        'sale.menu_sale_report': {
            'en_US': 'Reports',
            'es_ES': 'Informes',
        }
    }
    
    for xml_id, translations in menus_to_update.items():
        menu = env.ref(xml_id, raise_if_not_found=False)
        if menu:
            for lang_code, translated_text in translations.items():
                menu.with_context(lang=lang_code).write({'name': translated_text})
            _logger.info(f"CRM Base: Forced translation for {xml_id}")
