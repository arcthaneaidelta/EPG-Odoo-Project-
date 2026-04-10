from odoo import models, fields, api, _
from odoo.tools import human_size

class DmsStorage(models.Model):
    _inherit = 'dms.storage'

    total_quota = fields.Float(string='Total Quota (MB)', default=1024.0, help="Total capacity in MB")
    
    used_space = fields.Float(string='Used Space (Bytes)', compute='_compute_storage_usage', store=True)
    used_space_human = fields.Char(string='Used Space', compute='_compute_storage_usage')
    
    available_space = fields.Float(string='Available Space (Bytes)', compute='_compute_storage_usage')
    available_space_human = fields.Char(string='Available Space', compute='_compute_storage_usage')
    
    usage_rate = fields.Float(string='Usage Rate (%)', compute='_compute_storage_usage')

    @api.depends('storage_file_ids.size', 'total_quota')
    def _compute_storage_usage(self):
        for storage in self:
            used = sum(storage.storage_file_ids.mapped('size'))
            quota_bytes = storage.total_quota * 1024 * 1024
            storage.used_space = used
            storage.used_space_human = human_size(used)
            storage.available_space = max(0, quota_bytes - used)
            storage.available_space_human = human_size(max(0, quota_bytes - used))
            storage.usage_rate = (used / quota_bytes * 100) if quota_bytes > 0 else 0
