from odoo import models, fields, api

class LLMConfigWizard(models.TransientModel):
    _name = 'llm.config.wizard'
    _description = 'LLM Configuration Wizard'
    
    api_key = fields.Char(string='API Key', required=True)
    endpoint = fields.Char(string='Endpoint URL', required=True, default='https://api.openai.com/v1/chat/completions')
    
    def action_save_config(self):
        """Save configuration to system parameters"""
        self.env['ir.config_parameter'].sudo().set_param('ai_assistant.api_key', self.api_key)
        self.env['ir.config_parameter'].sudo().set_param('ai_assistant.endpoint', self.endpoint)
        return {'type': 'ir.actions.act_window_close'}