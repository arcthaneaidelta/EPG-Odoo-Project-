# -*- coding: utf-8 -*-

from . import models
from . import services
from . import wizards

def post_init_hook(env):
    """Post-installation hook to set up initial data"""
    # Create Real Estate team if it doesn't exist
    team = env['crm.team'].search([('name', '=', 'Real Estate')], limit=1)
    if not team:
        team = env['crm.team'].create({
            'name': 'Real Estate',
            'use_opportunities': True,
        })
    
    # Create default property types
    property_types = [
        {'name': 'Apartment', 'code': 'APT'},
        {'name': 'House', 'code': 'HSE'},
        {'name': 'Commercial', 'code': 'COM'},
        {'name': 'Land', 'code': 'LND'},
        {'name': 'Office', 'code': 'OFF'},
    ]
    
    for pt_data in property_types:
        exists = env['real.estate.property.type'].search([('code', '=', pt_data['code'])], limit=1)
        if not exists:
            env['real.estate.property.type'].create(pt_data)
