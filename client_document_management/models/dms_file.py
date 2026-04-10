from odoo import models, fields, api, _
from odoo.exceptions import UserError

class DmsFile(models.Model):
    _inherit = 'dms.file'

    document_type = fields.Selection([
        ('contract', 'Contract'),
        ('invoice', 'Invoice'),
        ('budget', 'Budget'),
        ('internal', 'Internal Document')
    ], string='Document Type', tracking=True)

    partner_id = fields.Many2one('res.partner', string='Associated Client', tracking=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('signed', 'Signed'),
        ('archived', 'Archived')
    ], string='Status', default='draft', tracking=True)
    
    version_number = fields.Integer(string='Version Number', default=1, tracking=True)
    
    sign_request_id = fields.Many2one('sign.oca.request', string='Signature Request', readonly=True, tracking=True)
    
    def write(self, vals):
        if 'content' in vals or 'attachment_id' in vals:
            # Increment version when content changes
            for record in self:
                vals['version_number'] = record.version_number + 1
        return super(DmsFile, self).write(vals)

    def action_send_for_signature(self):
        self.ensure_one()
        if not self.content:
            raise UserError(_("No content found in the file to sign."))
        
        # Determine signers
        signer_vals = []
        if self.partner_id:
            role = self.env['sign.oca.role'].search([], limit=1)
            if not role:
                role = self.env['sign.oca.role'].create({'name': 'Signer'})
            signer_vals.append((0, 0, {
                'partner_id': self.partner_id.id,
                'role_id': role.id,
            }))
            
        # Create Signature Request
        sign_request = self.env['sign.oca.request'].create({
            'name': f"Sign: {self.name}",
            'data': self.content,
            'record_ref': f"dms.file,{self.id}",
            'signer_ids': signer_vals,
        })
        
        self.write({
            'sign_request_id': sign_request.id,
            'status': 'sent'
        })
        
        # Return action to open the sign request
        return {
            'name': _('Signature Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'sign.oca.request',
            'res_id': sign_request.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_approve_signature(self):
        self.write({'status': 'signed'})
