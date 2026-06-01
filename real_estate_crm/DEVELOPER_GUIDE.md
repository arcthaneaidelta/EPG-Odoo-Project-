# Real Estate CRM - Developer Guide

## Module Structure

```
real_estate_crm/
├── __init__.py                 # Module initialization
├── __manifest__.py             # Module manifest
├── README.md                   # User documentation
├── INSTALLATION_GUIDE.md       # Installation instructions
├── DEVELOPER_GUIDE.md          # This file
│
├── models/                     # Business logic
│   ├── __init__.py
│   ├── real_estate_property.py           # Core property model
│   ├── real_estate_property_type.py      # Property categorization
│   ├── real_estate_rental_contract.py    # Rental contracts
│   ├── real_estate_visit.py              # Visit management
│   ├── real_estate_commission.py         # Commission tracking
│   ├── crm_lead.py                       # CRM extension
│   ├── res_partner.py                    # Partner extension
│   └── account_move.py                   # Invoice extension
│
├── services/                   # Business services
│   ├── __init__.py
│   └── mls_exporter.py                   # MLS integration (Phase 2)
│
├── views/                      # XML views
│   ├── real_estate_property_views.xml
│   ├── real_estate_property_type_views.xml
│   ├── real_estate_rental_contract_views.xml
│   ├── real_estate_visit_views.xml
│   ├── real_estate_commission_views.xml
│   ├── crm_lead_views.xml
│   ├── res_partner_views.xml
│   └── real_estate_menus.xml
│
├── security/                   # Access control
│   ├── real_estate_security.xml          # Groups and rules
│   └── ir.model.access.csv               # Access rights
│
├── data/                       # Initial data
│   ├── real_estate_data.xml              # Property types, CRM stages
│   └── ir_cron_data.xml                  # Scheduled actions
│
├── report/                     # Reports
│   ├── real_estate_reports.xml
│   ├── property_report_template.xml
│   └── commission_report_template.xml
│
├── demo/                       # Demo data
│   └── real_estate_demo.xml
│
├── wizards/                    # Wizard models (future)
│   └── __init__.py
│
└── static/                     # Static assets
    └── description/
        ├── icon.png
        └── index.html
```

## Key Design Principles

### 1. Multi-Tenancy First

Every model MUST include `company_id`:

```python
company_id = fields.Many2one(
    'res.company',
    string='Company',
    required=True,
    default=lambda self: self.env.company,
    index=True  # Important for performance
)
```

Every model MUST have a record rule:

```xml
<record id="model_name_comp_rule" model="ir.rule">
    <field name="name">Model Name Multi-Company</field>
    <field name="model_id" ref="model_model_name"/>
    <field name="domain_force">[('company_id', 'in', company_ids)]</field>
</record>
```

### 2. No Parallel Systems

- Use existing System CRM (`crm.lead`) instead of creating new opportunity system
- Use existing Accounting (`account.move`) instead of creating new invoicing
- Use existing Calendar (`calendar.event`) instead of creating new calendar
- Extend, don't replace

### 3. Proper Inheritance

```python
class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # For chatter and activities
    _order = 'create_date desc, id desc'
```

### 4. Idempotent Operations

Example: Recurring invoice generation

```python
def _create_invoice(self):
    # Check if invoice already exists
    existing_invoice = self.env['account.move'].search([
        ('rental_contract_id', '=', self.id),
        ('invoice_date', '=', self.next_invoice_date),
        ('state', '!=', 'cancel'),
    ], limit=1)
    
    if existing_invoice:
        return False  # Avoid duplicates
    
    # Create invoice...
```

## Model Details

### real.estate.property

**Purpose:** Core property management

**Key Fields:**
- `reference`: Auto-generated sequence (PROP-00001)
- `property_type_id`: Many2one to property types
- `transaction_type`: sale/rent/both
- `state`: available/reserved/sold/rented
- `agent_id`: Assigned sales agent
- `owner_id`: Property owner

**Key Methods:**
- `action_view_leads()`: View related opportunities
- `action_view_rental_contracts()`: View related contracts
- `action_view_visits()`: View scheduled visits
- `action_create_opportunity()`: Create new opportunity

**Computed Fields:**
- `lead_count`: Number of related opportunities
- `visit_count`: Number of scheduled visits
- `rental_contract_count`: Number of contracts
- `full_address`: Computed from address components

### real.estate.rental.contract

**Purpose:** Rental contract lifecycle management

**Key Fields:**
- `property_id`: Rented property
- `partner_id`: Tenant
- `recurring_amount`: Monthly/yearly rent
- `recurring_unit`: month/year
- `next_invoice_date`: Next invoice generation date
- `state`: draft/active/closed/cancelled

**Key Methods:**
- `action_confirm()`: Activate contract, create commission
- `action_close()`: Close contract, free property
- `_create_invoice()`: Generate single invoice
- `cron_create_recurring_invoices()`: Cron job for all contracts

**Business Logic:**
```python
@api.constrains('property_id', 'start_date', 'end_date', 'state')
def _check_property_availability(self):
    """Ensure property is not double-booked"""
    # Check for overlapping active contracts
```

### real.estate.visit

**Purpose:** Property visit scheduling and tracking

**Integration:**
- Creates `calendar.event` for each visit
- Links to `crm.lead` (opportunity)
- Links to `real.estate.property`

**Key Methods:**
- `_create_calendar_event()`: Auto-create calendar entry
- `action_confirm()`: Confirm visit
- `action_done()`: Mark as completed, update opportunity

### real.estate.commission

**Purpose:** Track agent commissions

**Automatic Creation:**
- Sale: When `crm.lead` is marked as won
- Rental: When `rental.contract` is activated

**Calculation Methods:**
1. Percentage: `amount = base_amount * (rate / 100)`
2. Fixed: `amount = fixed_amount`

**State Flow:**
draft → confirmed → paid

## Extension Points

### Adding Custom Fields to Property

```python
# In your custom module
from system import fields, models

class RealEstatePropertyCustom(models.Model):
    _inherit = 'real.estate.property'
    
    custom_field = fields.Char(string='Custom Field')
```

### Adding Custom Commission Rules

```python
class RealEstateCommissionCustom(models.Model):
    _inherit = 'real.estate.commission'
    
    @api.depends('base_amount', 'rate', 'agent_id')
    def _compute_amount(self):
        for record in self:
            # Custom logic based on agent tier, property type, etc.
            if record.agent_id.commission_tier == 'gold':
                record.amount = record.base_amount * 0.05
            else:
                super()._compute_amount()
```

### Adding New Property States

```python
# Extend the state selection
state = fields.Selection(
    selection_add=[
        ('under_offer', 'Under Offer'),
        ('sold_stc', 'Sold STC'),
    ],
    ondelete={'under_offer': 'set default', 'sold_stc': 'set default'}
)
```

## Phase 2 Implementation Guide

### MLS Portal Integration

1. **Create Portal Configuration Model**

```python
class MLSPortalConfig(models.Model):
    _name = 'real.estate.mls.config'
    _description = 'MLS Portal Configuration'
    
    name = fields.Char(required=True)  # idealista, fotocasa, etc.
    api_url = fields.Char(required=True)
    api_key = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True)
```

2. **Implement Actual Export Logic**

```python
# In services/mls_exporter.py
def export_property(self, property_id, portal='idealista'):
    config = self.env['real.estate.mls.config'].search([
        ('name', '=', portal),
        ('company_id', '=', property_id.company_id.id),
    ], limit=1)
    
    if not config:
        return {'success': False, 'message': 'Portal not configured'}
    
    # Map fields according to portal requirements
    data = self._map_property_fields(property_id, portal)
    
    # Make API call
    response = requests.post(
        config.api_url + '/properties',
        headers={'Authorization': f'Bearer {config.api_key}'},
        json=data
    )
    
    if response.status_code == 200:
        external_id = response.json().get('id')
        property_id.write({
            'mls_external_id': external_id,
            'mls_status': 'exported',
            'mls_last_sync': fields.Datetime.now(),
        })
        return {'success': True, 'external_id': external_id}
    else:
        property_id.write({
            'mls_status': 'error',
            'mls_error_message': response.text,
        })
        return {'success': False, 'message': response.text}
```

3. **Add Queue Job Support**

```python
# Use queue_job for async processing
@job
def export_property_job(self, property_id, portal):
    return self.export_property(property_id, portal)
```

### Demand Management

1. **Create Demand Model**

```python
class RealEstateDemand(models.Model):
    _name = 'real.estate.demand'
    _description = 'Property Demand'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    partner_id = fields.Many2one('res.partner', required=True)
    property_type_id = fields.Many2one('real.estate.property.type')
    transaction_type = fields.Selection([('sale', 'Buy'), ('rent', 'Rent')])
    min_price = fields.Monetary()
    max_price = fields.Monetary()
    min_bedrooms = fields.Integer()
    city = fields.Char()
    # ... more criteria
```

2. **Implement Matching Algorithm**

```python
def find_matching_properties(self):
    """Find properties matching demand criteria"""
    domain = [
        ('transaction_type', 'in', [self.transaction_type, 'both']),
        ('state', '=', 'available'),
    ]
    
    if self.property_type_id:
        domain.append(('property_type_id', '=', self.property_type_id.id))
    
    if self.min_price:
        domain.append(('price', '>=', self.min_price))
    
    if self.max_price:
        domain.append(('price', '<=', self.max_price))
    
    # ... more filters
    
    return self.env['real.estate.property'].search(domain)
```

3. **Automated Alerts**

```python
@api.model
def cron_send_demand_alerts(self):
    """Send alerts for new matching properties"""
    demands = self.search([('active', '=', True)])
    
    for demand in demands:
        # Find properties added since last check
        new_properties = demand.find_matching_properties().filtered(
            lambda p: p.create_date >= demand.last_alert_date
        )
        
        if new_properties:
            demand._send_alert_email(new_properties)
            demand.last_alert_date = fields.Datetime.now()
```

### Digital Signatures

1. **Add Signature Provider**

```python
class RealEstateSignatureProvider(models.Model):
    _name = 'real.estate.signature.provider'
    
    name = fields.Selection([
        ('docusign', 'DocuSign'),
        ('adobesign', 'Adobe Sign'),
    ])
    api_key = fields.Char()
    # ... configuration
```

2. **Generate Documents**

```python
def generate_rental_contract_pdf(self):
    """Generate PDF from template"""
    return self.env.ref('real_estate_crm.rental_contract_template')._render_qweb_pdf(self.ids)[0]
```

3. **Request Signatures**

```python
def request_signatures(self):
    """Send document for signature"""
    pdf_content = self.generate_rental_contract_pdf()
    
    provider = self.env['real.estate.signature.provider'].search([], limit=1)
    
    # Call signature provider API
    # Store signature request ID
    # Track status
```

## Testing

### Unit Tests

```python
from system.tests.common import TransactionCase

class TestRealEstateProperty(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.PropertyType = self.env['real.estate.property.type']
        self.Property = self.env['real.estate.property']
        
        self.property_type = self.PropertyType.create({
            'name': 'Test Type',
            'code': 'TST',
        })
    
    def test_create_property(self):
        """Test property creation with sequence"""
        property = self.Property.create({
            'name': 'Test Property',
            'property_type_id': self.property_type.id,
            'transaction_type': 'sale',
            'price': 100000,
        })
        
        self.assertTrue(property.reference.startswith('PROP-'))
        self.assertEqual(property.state, 'available')
    
    def test_property_multi_company(self):
        """Test multi-company isolation"""
        company1 = self.env['res.company'].create({'name': 'Company 1'})
        company2 = self.env['res.company'].create({'name': 'Company 2'})
        
        property1 = self.Property.with_company(company1).create({
            'name': 'Property Company 1',
            'property_type_id': self.property_type.id,
            'transaction_type': 'sale',
            'price': 100000,
        })
        
        # User from company2 should not see property1
        properties_company2 = self.Property.with_company(company2).search([])
        self.assertNotIn(property1, properties_company2)
```

### Integration Tests

```python
class TestRentalInvoicing(TransactionCase):
    
    def test_recurring_invoice_generation(self):
        """Test automatic invoice generation"""
        contract = self.env['real.estate.rental.contract'].create({
            'property_id': self.property.id,
            'partner_id': self.partner.id,
            'recurring_amount': 1000,
            'recurring_unit': 'month',
            'start_date': fields.Date.today(),
            'next_invoice_date': fields.Date.today(),
        })
        
        contract.action_confirm()
        
        # Run cron
        self.env['real.estate.rental.contract'].cron_create_recurring_invoices()
        
        # Verify invoice created
        invoices = self.env['account.move'].search([
            ('rental_contract_id', '=', contract.id)
        ])
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].amount_total, 1000)
```

## Performance Optimization

### Database Indexes

```python
# Add index to frequently searched fields
_sql_constraints = [
    ('reference_unique', 'unique(reference)', 'Reference must be unique!'),
]

# Or in PostgreSQL directly
CREATE INDEX idx_property_agent ON real_estate_property(agent_id);
CREATE INDEX idx_property_city ON real_estate_property(city);
```

### Query Optimization

```python
# Bad: N+1 query problem
for property in properties:
    print(property.agent_id.name)  # Queries database for each property

# Good: Prefetch related records
properties = self.env['real.estate.property'].search([])
properties.mapped('agent_id')  # Single query to load all agents
for property in properties:
    print(property.agent_id.name)  # No additional queries
```

### Computed Fields

```python
# Store computed fields that are frequently accessed
lead_count = fields.Integer(
    compute='_compute_lead_count',
    store=True,  # Stored in database for fast access
)

@api.depends('lead_ids')
def _compute_lead_count(self):
    for record in self:
        record.lead_count = len(record.lead_ids)
```

## Security Best Practices

1. **Always validate company_id in domains**
2. **Use groups for access control**
3. **Validate user permissions before sensitive operations**
4. **Never trust user input - always validate**
5. **Use ORM methods instead of raw SQL**
6. **Log sensitive operations**

## Migration Guide

### From System 17 to 18

If migrating from odoo 17:

1. Update API calls (some changed in v18)
2. Test all cron jobs
3. Verify record rules
4. Update views for new widgets
5. Test reports

## Contributing

When adding new features:

1. Follow existing code structure
2. Add proper docstrings
3. Include unit tests
4. Update relevant documentation
5. Ensure multi-tenant compatibility
6. Test with multiple companies

## Support

For development support:
- Check System documentation: https://www.system.com/documentation/18.0/
- Review existing code in this module
- Contact the development team

## License

LGPL-3
