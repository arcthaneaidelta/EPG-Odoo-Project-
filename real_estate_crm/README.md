# Real Estate CRM Module for System 18

## Overview

This is a comprehensive Real Estate Management module designed for **multi-tenant SaaS** deployment on System 18 Community Edition.

## Phase 1 Features (Implemented)

### ✅ Property Management
- Complete property lifecycle management (sale & rental)
- Property types and categorization
- Detailed property information (location, features, pricing)
- Property status tracking (available, reserved, sold, rented)
- Image management
- Full company isolation for multi-tenancy

### ✅ CRM Integration
- Seamless integration with System CRM (no parallel CRM)
- Property-linked opportunities
- Real Estate specific sales pipeline with stages:
  - Captación (Lead Capture)
  - Visita (Visit)
  - Oferta (Offer)
  - Negociación (Negotiation)
  - Cerrado Ganado/Perdido (Won/Lost)

### ✅ Visit Management
- Schedule and track property visits
- Calendar integration
- Visit feedback tracking
- Automatic calendar event creation
- Link visits to opportunities

### ✅ Rental Management
- Rental contract creation and management
- Contract lifecycle (draft, active, closed, cancelled)
- Security deposit tracking
- Monthly/yearly billing periods
- Property availability validation

### ✅ Automatic Recurring Invoicing
- Automatic invoice generation for active rentals
- Daily cron job for invoice creation
- Idempotent design (no duplicate invoices)
- Standard System accounting integration

### ✅ Commission Management
- Automatic commission calculation
- Percentage or fixed amount commissions
- Sale and rental commissions
- Commission lifecycle (draft, confirmed, paid)
- Agent commission tracking

### ✅ MLS Portal Preparation
- Technical structure for portal integration
- Fields for external IDs and sync status
- Placeholder service for Phase 2 implementation
- Prepared for: Idealista, Fotocasa, Habitaclia, pisos.com, yaencontre

## Multi-Tenant SaaS Features

### Complete Isolation
- All models include `company_id` field
- Record rules enforce company-based access
- Each tenant operates in their own database
- No data leakage between tenants

### Security
- Role-based access control (User/Manager)
- Company-specific record rules on all models
- Proper access rights configuration

## Installation

### Requirements
- System 18.0 Community Edition
- Python 3.10+
- PostgreSQL 12+

### Installation Steps

1. **Copy the module to your System addons directory:**
   ```bash
   cp -r real_estate_crm /path/to/system/addons/
   ```

2. **Update the addons list:**
   - Go to Apps menu
   - Click "Update Apps List"

3. **Install the module:**
   - Search for "Real Estate CRM"
   - Click Install

4. **Initial Setup:**
   - The module will automatically create:
     - Real Estate CRM team
     - Default property types
     - CRM stages for real estate pipeline

## Usage

### Property Management
1. Go to Real Estate > Properties > All Properties
2. Click "Create" to add a new property
3. Fill in property details (type, price, location, features)
4. Assign an agent and owner
5. Set transaction type (sale/rent/both)

### Creating Opportunities
1. From a property, click "Create Opportunity"
2. Or link an existing CRM opportunity to a property
3. Track through the real estate pipeline
4. Schedule visits directly from the opportunity

### Rental Contracts
1. Go to Real Estate > Rentals > Rental Contracts
2. Create a new contract selecting property and tenant
3. Set rental amount and billing period
4. Confirm the contract to activate
5. Invoices will be generated automatically

### Commissions
Commissions are created automatically:
- **Sale**: When an opportunity is marked as "Won"
- **Rental**: When a rental contract is activated

View and manage commissions in Real Estate > Finance > Commissions

## Technical Details

### Models

#### Core Models
- `real.estate.property` - Property management
- `real.estate.property.type` - Property categorization
- `real.estate.rental.contract` - Rental contracts
- `real.estate.visit` - Property visits
- `real.estate.commission` - Commission tracking

#### Model Extensions
- `crm.lead` - Added property_id field and visit/commission tracking
- `res.partner` - Added property ownership and rental tracking
- `account.move` - Added rental_contract_id for invoice linking

#### Services
- `real.estate.mls.exporter` - MLS portal integration placeholder

### Key Features for SaaS

#### Database Per Tenant
Each paying subscriber gets their own database instance with:
- Complete data isolation
- Independent configuration
- Own users and permissions

#### Company-Based Security
```python
# All models include:
company_id = fields.Many2one(
    'res.company',
    required=True,
    default=lambda self: self.env.company,
    index=True
)

# Record rules enforce:
domain_force="[('company_id', 'in', company_ids)]"
```

#### Cron Jobs
- **Daily Invoice Generation**: Automatically creates rental invoices
- Configurable timing and frequency
- Logs all activities in chatter

## Phase 2 Features (Planned)

### 🔜 MLS Portal Integration
- Real connectors to Idealista, Fotocasa, Habitaclia, pisos.com, yaencontre
- Automatic property publication
- Bi-directional synchronization
- Error handling and retry logic

### 🔜 Demand Management
- Buyer/tenant demand registration
- Automatic matching with properties
- Alert system for compatible properties

### 🔜 Digital Signatures
- Contract signing (rental, sales, agency agreements)
- Integration with e-signature providers

### 🔜 Advanced Document Management
- Document types and expiration tracking
- Automated alerts for document renewals

### 🔜 Advanced Reporting
- Property profitability analysis
- Cash flow projections
- Downloadable reports for owners/investors

### 🔜 Advanced Automation
- Automated follow-ups for stale opportunities
- Property visit alerts
- Advanced commission rules (splits, collaborations)

## Support

For support and customization requests, please contact your system administrator.

## License

LGPL-3

## Author

Developed for Multi-Tenant Real Estate SaaS Platform

## Version

18.0.1.0.0
