# Real Estate CRM - Installation & Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation Steps](#installation-steps)
3. [Multi-Tenant SaaS Setup](#multi-tenant-saas-setup)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **System Version**: 18.0 Community Edition
- **Python**: 3.10 or higher
- **PostgreSQL**: 12 or higher
- **RAM**: Minimum 4GB (8GB recommended for production)
- **Disk Space**: Minimum 10GB

### Python Dependencies
All dependencies are included in System 18. No additional Python packages required.

### System Modules Dependencies
- `base` (System Core)
- `mail` (Messaging & Activities)
- `crm` (Customer Relationship Management)
- `sale_management` (Sales)
- `account` (Accounting & Invoicing)
- `calendar` (Calendar Events)

## Installation Steps

### Step 1: Copy Module to Addons Directory

```bash
# Navigate to your System addons directory
cd /path/to/system/addons

# Copy the real_estate_crm module
cp -r /path/to/real_estate_crm ./

# Set proper ownership (replace system with your System user)
chown -R system:system real_estate_crm

# Set proper permissions
chmod -R 755 real_estate_crm
```

### Step 2: Update System Apps List

**Method 1: Via UI (Recommended for single installation)**
1. Login to System as Administrator
2. Go to `Apps` menu
3. Click on the menu icon (☰) in the search bar
4. Select `Update Apps List`
5. Confirm the update

**Method 2: Via Command Line (Recommended for automated deployment)**
```bash
# Restart System with update flag
./system-bin -c /path/to/system.conf -d your_database -u all --stop-after-init

# Or update apps list only
./system-bin -c /path/to/system.conf -d your_database --update-apps-list --stop-after-init
```

### Step 3: Install the Module

**Method 1: Via UI**
1. Go to `Apps`
2. Remove the "Apps" filter from the search
3. Search for "Real Estate CRM"
4. Click `Install`

**Method 2: Via Command Line**
```bash
./system-bin -c /path/to/system.conf -d your_database -i real_estate_crm --stop-after-init
```

### Step 4: Verify Installation

1. Check that the "Real Estate" menu appears in the main menu bar
2. Navigate to Real Estate > Properties
3. Verify that default property types exist
4. Check that the Real Estate CRM team is created

## Multi-Tenant SaaS Setup

### Architecture Overview

```
SaaS Platform
├── Main Database (template)
│   └── real_estate_crm module installed
│
├── Tenant Database 1
│   ├── Copy of template
│   └── Isolated company data
│
├── Tenant Database 2
│   ├── Copy of template
│   └── Isolated company data
│
└── Tenant Database N
    ├── Copy of template
    └── Isolated company data
```

### Setting Up the Template Database

1. **Create Template Database**
```bash
# Create a clean System database
./system-bin -c /path/to/system.conf -d real_estate_template --db-filter=real_estate_template -i real_estate_crm --stop-after-init
```

2. **Configure Template**
- Install only essential modules
- Set up default property types
- Configure CRM stages
- Set up email templates (optional)
- DO NOT add any real data

3. **Create Database Snapshot**
```sql
-- Create template from existing database
CREATE DATABASE real_estate_template_backup WITH TEMPLATE real_estate_template;
```

### Creating New Tenant Databases

#### Option 1: PostgreSQL Template

```sql
-- Create new tenant database from template
CREATE DATABASE tenant_company_name WITH TEMPLATE real_estate_template OWNER system;
```

#### Option 2: System Database Manager

1. Access System Database Manager: `http://your-domain/web/database/manager`
2. Use "Duplicate Database" function
3. Name: `tenant_company_name`
4. Source: `real_estate_template`

#### Option 3: Python Script (Automated SaaS Provisioning)

```python
import psycopg2
from system import api, SUPERUSER_ID

def create_tenant_database(template_db, new_db_name, company_name):
    """
    Create a new tenant database from template
    """
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname='postgres',
        user='system',
        password='your_password',
        host='localhost'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Create database from template
    cursor.execute(f"CREATE DATABASE {new_db_name} WITH TEMPLATE {template_db}")
    
    # Update company information in new database
    tenant_conn = psycopg2.connect(
        dbname=new_db_name,
        user='system',
        password='your_password',
        host='localhost'
    )
    tenant_cursor = tenant_conn.cursor()
    
    # Update company name
    tenant_cursor.execute(
        "UPDATE res_company SET name = %s WHERE id = 1",
        (company_name,)
    )
    tenant_conn.commit()
    
    cursor.close()
    conn.close()
    tenant_cursor.close()
    tenant_conn.close()
    
    return True
```

### Database Isolation Verification

Run this SQL query on each tenant database to verify isolation:

```sql
-- Check that company_id exists on all critical tables
SELECT 
    table_name, 
    column_name 
FROM 
    information_schema.columns 
WHERE 
    table_name IN (
        'real_estate_property',
        'real_estate_rental_contract',
        'real_estate_visit',
        'real_estate_commission'
    ) 
    AND column_name = 'company_id';
```

Expected result: All 4 tables should have company_id column.

## Configuration

### Initial Configuration

1. **Create Sales Team**
   - Go to: Real Estate > Configuration > Sales Teams
   - A "Real Estate" team is created automatically
   - Assign team members

2. **Configure Property Types**
   - Go to: Real Estate > Properties > Property Types
   - Default types are created automatically:
     - Apartment (APT)
     - House (HSE)
     - Commercial (COM)
     - Land (LND)
     - Office (OFF)
   - Add more types as needed

3. **Set Up CRM Stages**
   - Stages are created automatically for Real Estate team:
     - Captación
     - Visita
     - Oferta
     - Negociación
     - Cerrado Ganado
     - Cerrado Perdido

4. **Configure Users**
   - Settings > Users & Companies > Users
   - Assign users to "Real Estate / User" or "Real Estate / Manager" groups

5. **Set Up Cron Job**
   - Go to: Settings > Technical > Automation > Scheduled Actions
   - Verify "Real Estate: Generate Recurring Rental Invoices" is active
   - Default: Runs daily at midnight
   - Modify schedule if needed

### Commission Configuration

Default commission rates can be set by modifying the default value in the model:

```python
# In models/real_estate_commission.py
rate = fields.Float(
    string='Commission Rate (%)',
    default=3.0,  # Change this value
    tracking=True
)
```

Or create a configuration model (Phase 2 enhancement).

## Testing

### Functional Testing Checklist

#### Property Management
- [ ] Create a new property
- [ ] Edit property details
- [ ] Upload property images
- [ ] Archive/unarchive a property
- [ ] Change property status (available, reserved, sold, rented)
- [ ] Filter properties by type, city, agent
- [ ] Search properties by name and reference

#### CRM Integration
- [ ] Create opportunity from property
- [ ] Link existing opportunity to property
- [ ] Move opportunity through pipeline stages
- [ ] Mark opportunity as won
- [ ] Verify commission created on won opportunity

#### Visit Management
- [ ] Schedule a visit from property
- [ ] Schedule a visit from opportunity
- [ ] View visits in calendar
- [ ] Confirm a visit
- [ ] Mark visit as done
- [ ] Add visitor feedback
- [ ] Check calendar event created

#### Rental Management
- [ ] Create rental contract
- [ ] Confirm rental contract
- [ ] Verify property status changes to "rented"
- [ ] Verify commission created on contract activation
- [ ] Close rental contract
- [ ] Cancel rental contract

#### Recurring Invoicing
- [ ] Create active rental contract with start date today or earlier
- [ ] Run cron job manually: Settings > Technical > Automation > Scheduled Actions
- [ ] Find "Real Estate: Generate Recurring Rental Invoices"
- [ ] Click "Run Manually"
- [ ] Verify invoice created
- [ ] Verify next_invoice_date updated
- [ ] Run again to verify no duplicate invoice

#### Commission Tracking
- [ ] Verify sale commission created on won opportunity
- [ ] Verify rental commission created on active contract
- [ ] Confirm commission
- [ ] Mark commission as paid
- [ ] Cancel commission

### Multi-Tenant Testing

1. **Create Test Tenants**
```bash
# Create tenant 1
CREATE DATABASE tenant1 WITH TEMPLATE real_estate_template;

# Create tenant 2
CREATE DATABASE tenant2 WITH TEMPLATE real_estate_template;
```

2. **Test Data Isolation**
   - Login to tenant1
   - Create properties, contracts, visits
   - Login to tenant2
   - Verify NO data from tenant1 is visible
   - Create different properties
   - Verify complete isolation

3. **Test Company Rules**
   - Create a property in tenant1
   - Note the company_id
   - Verify record rule prevents access from other companies

### Performance Testing

For SaaS environments, test with realistic data volumes:

```python
# Script to generate test data
def generate_test_properties(count=1000):
    Property = env['real.estate.property']
    for i in range(count):
        Property.create({
            'name': f'Test Property {i}',
            'property_type_id': # cycle through types,
            'transaction_type': # random choice,
            'price': # random price,
        })
```

## Troubleshooting

### Common Issues

#### Issue 1: Module Not Appearing in Apps List

**Solution:**
```bash
# Update apps list
./system-bin -c /path/to/system.conf -d your_database --update-apps-list --stop-after-init

# Or clear cache
rm -rf ~/.local/share/System/filestore/your_database
```

#### Issue 2: Import Errors

**Symptoms:** Module fails to install with ImportError

**Solution:**
- Verify all dependency modules are installed
- Check Python version compatibility
- Restart System service

```bash
sudo systemctl restart system
# Or
sudo service system restart
```

#### Issue 3: Recurring Invoices Not Generated

**Symptoms:** Cron job runs but no invoices created

**Debugging Steps:**

1. Check cron job is active:
```sql
SELECT * FROM ir_cron WHERE name LIKE '%Real Estate%';
```

2. Run manually and check logs:
```bash
# In System shell
./system-bin shell -c /path/to/system.conf -d your_database

>>> env = api.Environment(cr, SUPERUSER_ID, {})
>>> contracts = env['real.estate.rental.contract'].cron_create_recurring_invoices()
>>> print(contracts)
```

3. Verify contract conditions:
   - state = 'active'
   - next_invoice_date <= today
   - No existing invoice for the period

#### Issue 4: Commission Not Created Automatically

**Solution:**
- Verify opportunity is marked as "Won" (not just closed)
- Check property has a price set
- Verify user has permission to create commissions
- Check logs for errors

#### Issue 5: Multi-Tenant Data Leakage

**Emergency Response:**
```sql
-- Verify record rules are active
SELECT * FROM ir_rule WHERE model_id IN (
    SELECT id FROM ir_model WHERE model LIKE 'real.estate.%'
);

-- Check for records without company_id
SELECT COUNT(*) FROM real_estate_property WHERE company_id IS NULL;
SELECT COUNT(*) FROM real_estate_rental_contract WHERE company_id IS NULL;
```

**Prevention:**
- Always use default company in model definitions
- Test with multiple companies
- Regular audits of record rules

### Getting Support

1. **Check Logs:**
```bash
# System log file
tail -f /var/log/system/system.log

# Or if running manually
./system-bin -c /path/to/system.conf -d your_database --log-level=debug
```

2. **Enable Developer Mode:**
   - Settings > Activate the developer mode
   - Provides more detailed error messages

3. **Database Debugging:**
```bash
# Connect to PostgreSQL
psql -U system -d your_database

# Check table structure
\d real_estate_property

# Check data
SELECT * FROM real_estate_property LIMIT 10;
```

## Production Deployment Checklist

- [ ] All tests pass
- [ ] Multi-tenant isolation verified
- [ ] Backup strategy in place
- [ ] Monitoring configured
- [ ] Log rotation set up
- [ ] Cron jobs verified
- [ ] Security groups configured
- [ ] Email server configured (for notifications)
- [ ] Performance tested with production data volume
- [ ] Disaster recovery plan documented
- [ ] User training completed
- [ ] Documentation provided to administrators

## Backup and Recovery

### Backup Template Database

```bash
# Backup template database
pg_dump -U system -d real_estate_template -f real_estate_template_backup.sql

# Backup with compression
pg_dump -U system -d real_estate_template | gzip > real_estate_template_backup.sql.gz
```

### Restore Template Database

```bash
# Restore from backup
psql -U system -d real_estate_template < real_estate_template_backup.sql

# Restore from compressed backup
gunzip < real_estate_template_backup.sql.gz | psql -U system -d real_estate_template
```

### Automated Backup Script

```bash
#!/bin/bash
# /usr/local/bin/backup_system_tenants.sh

BACKUP_DIR="/var/backups/system"
DATE=$(date +%Y%m%d_%H%M%S)

# Get list of all tenant databases
DATABASES=$(psql -U postgres -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'tenant_%'")

for DB in $DATABASES; do
    echo "Backing up $DB..."
    pg_dump -U system -d $DB | gzip > "$BACKUP_DIR/${DB}_${DATE}.sql.gz"
done

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed"
```

Add to crontab:
```bash
# Run daily at 2 AM
0 2 * * * /usr/local/bin/backup_system_tenants.sh
```

## Next Steps

After successful installation:
1. Review the README.md for feature overview
2. Configure initial settings
3. Train users
4. Import initial data (if any)
5. Plan for Phase 2 features

For Phase 2 implementation (MLS integration, advanced features), contact your development team.
