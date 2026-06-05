# -*- coding: utf-8 -*-

from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    company_type_industry = fields.Selection([
        ('services', 'Servicios'),
        ('tech', 'Tecnología e IT'),
        ('retail', 'Comercio / Retail'),
        ('real_estate', 'Real Estate / Inmobiliaria'),
        ('accounting', 'Contabilidad / Gestoría'),
        ('manufacturing', 'Fabricación / Industria'),
        ('other', 'Otro')
    ], string="Sector de la Empresa")
    
    employee_count_range = fields.Selection([
        ('1-5', '1-5 empleados'),
        ('6-20', '6-20 empleados'),
        ('21-50', '21-50 empleados'),
        ('50+', 'Más de 50 empleados')
    ], string="Número de Empleados")
    
    primary_use_case = fields.Selection([
        ('crm', 'Ventas y CRM'),
        ('accounting', 'Facturación y Contabilidad'),
        ('projects', 'Gestión de Proyectos / Operaciones'),
        ('all', 'Todo en Uno (Gestión integral)')
    ], string="Uso Principal")
