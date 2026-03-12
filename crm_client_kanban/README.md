# CRM Client Kanban – Dark Profile Cards
### System 18 Community Edition

Replaces the default **Contacts** kanban view with rich dark-themed
profile cards showing real-time sales, invoice, call, and meeting stats.

---

## 📦 Module Structure

```
crm_client_kanban/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── res_partner.py          ← computed stats fields
├── views/
│   └── res_partner_views.xml   ← QWeb kanban card override
└── static/src/
    ├── scss/
    │   └── client_kanban.scss  ← dark theme styles
    └── js/
        └── client_kanban.js    ← OWL patch for button behaviour
```

---

## 🚀 Installation

1. **Copy the module** into your System addons path:
   ```bash
   cp -r crm_client_kanban /path/to/system/custom_addons/
   ```

2. **Restart the System server:**
   ```bash
   ./system-bin -c system.conf --dev=xml
   ```

3. **Activate developer mode** in System:
   Settings → General Settings → Developer Tools → Activate

4. **Update the apps list:**
   Apps → Update Apps List

5. **Install the module:**
   Search for "CRM Client Kanban" and click Install

6. Navigate to **Contacts → Kanban view** to see the new cards.

---

## 🔧 Dependencies

| Module            | Purpose                          |
|-------------------|----------------------------------|
| `base`            | res.partner model                |
| `contacts`        | Base kanban view to inherit      |
| `sale_management` | Total sales & growth computation |
| `account`         | Invoice count                    |
| `crm`             | Phone call activities            |
| `calendar`        | Meeting count                    |

---

## 📊 Stats shown on each card

| Stat           | Source Model                        |
|----------------|-------------------------------------|
| Total Sales    | `sale.order` (state: sale/done)     |
| Total Invoices | `account.move` (out_invoice)        |
| Total Calls    | `mail.activity` (phonecall type)    |
| Total Meetings | `calendar.event`                    |

Growth % is calculated by comparing current month vs previous month sales.

---

## 🎨 Customization

- **Colors**: Edit CSS variables at the top of `client_kanban.scss`
- **Stats**: Add more computed fields in `models/res_partner.py` and display them in the QWeb template
- **Buttons**: The `+ New Deal` button calls `action_new_opportunity` on `res.partner` — ensure CRM is installed

---

## ⚠️ Notes

- This module **inherits** the standard contacts kanban view — it does not replace System core files.
- If the `contacts` module kanban view ID changes between System versions, update the `inherit_id` ref in `views/res_partner_views.xml`.
- Computed fields are **not stored** (`store=False`) to avoid performance impact on large databases. Set `store=True` and add proper `depends` triggers if you need faster loads.
