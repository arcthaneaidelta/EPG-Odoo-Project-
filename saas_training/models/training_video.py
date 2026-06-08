from odoo import models, fields, api
from odoo.exceptions import UserError

class SaasTrainingVideo(models.Model):
    _name = 'saas.training.video'
    _description = 'Training Video'
    _order = 'sequence, id'

    name = fields.Char('Title', required=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection([
        ('sales', 'Sales'),
        ('accounting', 'Accounting'),
        ('pipeline', 'Pipeline'),
        ('general', 'General')
    ], string='Category', required=True, default='general')
    video_url = fields.Char('YouTube Link', required=True)
    description = fields.Text('Description')

    def action_open_video(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.video_url,
            'target': 'new',
        }

    def action_push_to_tenants(self):
        if 'saas.subscription' in self.env:
            self.env['saas.subscription'].sync_training_videos(self)
        else:
            raise UserError('This action is only available on the master database.')
