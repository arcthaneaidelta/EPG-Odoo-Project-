# -*- coding: utf-8 -*-

from odoo import models, _

class BaseLanguageInstall(models.TransientModel):
    _inherit = "base.language.install"

    def lang_install(self):
        # Call the original method to perform the installation and get the action dict
        res = super(BaseLanguageInstall, self).lang_install()
        
        # Override the action dictionary to set a white-labeled title instead of falling back to "Odoo"
        if isinstance(res, dict):
            # If it's a window action (the dialog), set the 'name' explicitly
            if res.get('type') == 'ir.actions.act_window':
                res['name'] = _("EPG")
            
            # If it's a client action (display_notification), set the title in params
            elif res.get('type') == 'ir.actions.client' and res.get('tag') == 'display_notification':
                if 'params' in res:
                    res['params']['title'] = _("EPG")
                    
        return res
