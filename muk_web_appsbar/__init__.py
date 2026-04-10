from . import models
import base64
import logging
from odoo.tools import file_open

_logger = logging.getLogger(__name__)


def _setup_module(env):
    company = env.ref('base.main_company', raise_if_not_found=False)
    if company:
        # Load the custom logo if it exists
        logo_path = 'muk_web_appsbar/static/src/img/companylogo.png'
        try:
            with file_open(logo_path, 'rb') as file:
                logo_data = base64.b64encode(file.read())
            if logo_data:
                company.write({
                    'logo': logo_data,
                    'appbar_image': logo_data,
                    'name': 'EPG' if company.name == 'YourCompany' else company.name,
                })
                _logger.info("EPG Branding: Custom logo applied to %s", company.name)
        except Exception:
            # Fallback to default if custom logo is not found
            with file_open('base/static/img/res_company_logo.png', 'rb') as file:
                logo_data = base64.b64encode(file.read())
                company.write({
                    'appbar_image': logo_data
                })