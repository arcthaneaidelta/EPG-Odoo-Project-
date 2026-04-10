from odoo import models, fields, api, _
import base64

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_generate_dms_document(self):
        """Generates a PDF of the sale order and saves it to DMS."""
        self.ensure_one()
        
        # 1. Get the PDF report
        report_template = 'sale.action_report_saleorder'
        pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(report_template, self.id)
        
        # 2. Find or create the root directory for Sales
        # Use with_company to ensure we operate in the correct context
        DMSDir = self.env['dms.directory'].with_company(self.company_id)
        DMSFile = self.env['dms.file'].with_company(self.company_id)
        DMSStorage = self.env['dms.storage'].with_company(self.company_id)

        root_dir = DMSDir.search([('name', '=', 'Sales'), ('is_root_directory', '=', True)], limit=1)
        if not root_dir:
            # Create a default storage and root directory if missing
            storage = DMSStorage.search([], limit=1)
            if not storage:
                storage = DMSStorage.create({
                    'name': 'DMS Principal', 
                    'save_type': 'database',
                    'company_id': self.company_id.id
                })
            root_dir = DMSDir.create({
                'name': 'Sales',
                'is_root_directory': True,
                'storage_id': storage.id,
                'company_id': self.company_id.id,
                'group_ids': [(4, self.env.ref('client_document_management.dms_access_invoice_user').id)]
            })
            
        # 3. Create a subdirectory for the specific order
        order_dir = DMSDir.search([('name', '=', self.name), ('parent_id', '=', root_dir.id)], limit=1)
        if not order_dir:
            order_dir = DMSDir.create({
                'name': self.name,
                'parent_id': root_dir.id,
                'res_model': 'sale.order',
                'res_id': self.id,
                'company_id': self.company_id.id
            })
            
        # 4. Create the document record
        return DMSFile.create({
            'name': f"{self.name}.pdf",
            'directory_id': order_dir.id,
            'content': base64.b64encode(pdf_content),
            'document_type': 'budget' if self.state in ['draft', 'sent'] else 'invoice',
            'partner_id': self.partner_id.id,
            'status': 'sent' if self.state == 'sent' else 'draft',
            'company_id': self.company_id.id
        })
