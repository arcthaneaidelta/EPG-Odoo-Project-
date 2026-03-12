import logging
from datetime import datetime, time

from dateutil.relativedelta import relativedelta

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CrmDashboardController(http.Controller):
    @http.route("/crm_dashboard/data", type="json", auth="user")
    def crm_dashboard_data(self, search="", period_month=""):
        lead_model = request.env["crm.lead"]
        sale_model = self._get_model("sale.order")
        invoice_model = self._get_model("account.move")
        search_term = (search or "").strip()
        selected_month_start = self._parse_month_start(period_month)

        search_domain = self._build_search_domain(search_term)
        total_lead_domain = search_domain + [("type", "in", ["lead", "opportunity"])]
        opportunity_domain = search_domain + [("type", "=", "opportunity")]
        won_domain = opportunity_domain + [("stage_id.is_won", "=", True)]

        month_windows = self._get_month_windows(
            month_count=7, end_month_start=selected_month_start
        )
        month_labels = [month_start.strftime("%b") for month_start, _month_end in month_windows]

        leads_series = self._count_series(
            lead_model, total_lead_domain, "create_date", month_windows
        )
        won_series = self._count_series(lead_model, won_domain, "date_closed", month_windows)

        sales_domain = []
        sales_series = [0.0] * len(month_windows)
        total_sales = 0.0
        sale_order_ids = []
        if sale_model is not None:
            sale_model = sale_model.sudo()
            # Sum every sales order/quotation except canceled ones.
            sales_domain = [
                ("state", "!=", "cancel"),
                ("company_id", "=", request.env.company.id),
            ]
            if search_term:
                sales_domain.extend(
                    [
                        "|",
                        "|",
                        "|",
                        ("name", "ilike", search_term),
                        ("partner_id.name", "ilike", search_term),
                        ("client_order_ref", "ilike", search_term),
                        ("origin", "ilike", search_term),
                    ]
                )
            sales_series = self._sum_series(
                sale_model, sales_domain, "date_order", "amount_total", month_windows
            )
            total_sales = self._sum_amount(sale_model, sales_domain, "amount_total")
            sale_order_ids = sale_model.search(sales_domain).ids

        invoice_domain = [("id", "=", 0)]
        invoice_ids = []
        invoice_series = [0.0] * len(month_windows)
        total_invoices = 0.0
        if invoice_model is not None:
            invoice_model = invoice_model.sudo()
            # Sum only customer invoices generated from non-cancel sales orders.
            if sale_order_ids:
                invoice_domain = [
                    ("move_type", "=", "out_invoice"),
                    ("state", "!=", "cancel"),
                    ("company_id", "=", request.env.company.id),
                    ("invoice_line_ids.sale_line_ids.order_id", "in", sale_order_ids),
                ]
            # Find IDs first to avoid duplicate totals caused by relational joins.
            invoice_ids = invoice_model.search(invoice_domain).ids
            amount_domain = [("id", "in", invoice_ids)] if invoice_ids else [("id", "=", 0)]
            invoice_series = self._sum_series(
                invoice_model,
                amount_domain,
                "invoice_date",
                "amount_total",
                month_windows,
                use_date=True,
            )
            total_invoices = self._sum_amount(invoice_model, amount_domain, "amount_total")
        self._log_sales_invoice_debug(
            sale_model=sale_model,
            invoice_model=invoice_model,
            sales_domain=sales_domain,
            sale_order_ids=sale_order_ids,
            total_sales=total_sales,
            invoice_domain=invoice_domain,
            invoice_ids=invoice_ids,
            total_invoices=total_invoices,
            search_term=search_term,
            selected_month_start=selected_month_start,
        )

        total_leads = lead_model.search_count(total_lead_domain)
        total_won = lead_model.search_count(won_domain)

        distribution = self._lead_vs_won_distribution(total_leads, total_won)
        table_rows = self._recent_crm_rows(lead_model, search_domain)
        company_currency = request.env.company.currency_id

        return {
            "user_name": request.env.user.name,
            "user_email": request.env.user.email or request.env.user.login or "",
            "company_name": request.env.company.name,
            "currency": {
                "symbol": company_currency.symbol or "",
                "position": company_currency.position or "before",
            },
            "kpis": [
                {
                    "key": "total_leads",
                    "label": "Total Leads",
                    "value": total_leads,
                    "series": leads_series,
                    "tone": "",
                },
                {
                    "key": "total_sales",
                    "label": "Total Sales",
                    "value": total_sales,
                    "series": sales_series,
                    "tone": "pink",
                },
                {
                    "key": "total_invoices",
                    "label": "Total Invoices",
                    "value": total_invoices,
                    "series": invoice_series,
                    "tone": "green",
                },
                {
                    "key": "total_won",
                    "label": "Total Won",
                    "value": total_won,
                    "series": won_series,
                    "tone": "",
                },
            ],
            "sales_chart": {
                "labels": month_labels,
                "values": sales_series,
                "period_label": selected_month_start.strftime("%b %Y"),
                "selected_month": selected_month_start.strftime("%Y-%m"),
            },
            "won_total": total_won,
            "won_distribution": distribution,
            "table_rows": table_rows,
        }

    def _build_search_domain(self, search_term):
        domain = []
        if search_term:
            domain.extend(
                [
                    "|",
                    "|",
                    "|",
                    ("name", "ilike", search_term),
                    ("partner_name", "ilike", search_term),
                    ("contact_name", "ilike", search_term),
                    ("email_from", "ilike", search_term),
                ]
            )
        return domain

    def _get_month_windows(self, month_count=6, end_month_start=None):
        current_month_start = end_month_start or fields.Date.context_today(
            request.env.user
        ).replace(day=1)
        first_month_start = current_month_start - relativedelta(months=month_count - 1)
        windows = []
        for month_offset in range(month_count):
            month_start = first_month_start + relativedelta(months=month_offset)
            month_end = month_start + relativedelta(months=1)
            windows.append((month_start, month_end))
        return windows

    def _parse_month_start(self, period_month):
        value = (period_month or "").strip()
        if value:
            try:
                parsed = datetime.strptime(value, "%Y-%m")
                return parsed.date().replace(day=1)
            except ValueError:
                pass
        return fields.Date.context_today(request.env.user).replace(day=1)

    def _count_series(self, model, base_domain, date_field, month_windows, use_date=False):
        values = []
        for month_start, month_end in month_windows:
            domain = list(base_domain)
            from_value = (
                fields.Date.to_string(month_start)
                if use_date
                else self._to_datetime_string(month_start)
            )
            to_value = (
                fields.Date.to_string(month_end)
                if use_date
                else self._to_datetime_string(month_end)
            )
            domain.extend(
                [
                    (date_field, ">=", from_value),
                    (date_field, "<", to_value),
                ]
            )
            values.append(model.search_count(domain))
        return values

    def _sum_series(
        self, model, base_domain, date_field, amount_field, month_windows, use_date=False
    ):
        values = []
        for month_start, month_end in month_windows:
            domain = list(base_domain)
            from_value = (
                fields.Date.to_string(month_start)
                if use_date
                else self._to_datetime_string(month_start)
            )
            to_value = (
                fields.Date.to_string(month_end)
                if use_date
                else self._to_datetime_string(month_end)
            )
            domain.extend(
                [
                    (date_field, ">=", from_value),
                    (date_field, "<", to_value),
                ]
            )
            values.append(self._sum_amount(model, domain, amount_field))
        return values

    def _sum_amount(self, model, domain, amount_field):
        group = model.read_group(domain, [f"{amount_field}:sum"], [])
        if not group:
            return 0.0
        row = group[0]
        # System may return aggregated sums either as "<field>_sum" or "<field>"
        # depending on version/context, so support both keys.
        value = row.get(f"{amount_field}_sum")
        if value is None:
            value = row.get(amount_field)
        return float(value or 0.0)

    def _log_sales_invoice_debug(
        self,
        sale_model,
        invoice_model,
        sales_domain,
        sale_order_ids,
        total_sales,
        invoice_domain,
        invoice_ids,
        total_invoices,
        search_term,
        selected_month_start,
    ):
        if total_sales and total_invoices:
            return

        company = request.env.company
        user = request.env.user
        sales_count = (
            sale_model.search_count(sales_domain)
            if sale_model is not None and sales_domain
            else 0
        )
        invoice_count = len(invoice_ids)
        company_sales_count = (
            sale_model.search_count(
                [("state", "!=", "cancel"), ("company_id", "=", company.id)]
            )
            if sale_model is not None
            else 0
        )
        company_invoice_count = (
            invoice_model.search_count(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "!=", "cancel"),
                    ("company_id", "=", company.id),
                ]
            )
            if invoice_model is not None
            else 0
        )

        _logger.warning(
            (
                "CRM Dashboard zero amounts debug | "
                "company_id=%s company_name=%s user_id=%s user_login=%s "
                "search_term=%r selected_month=%s "
                "sales_domain=%s sales_count=%s sale_order_ids_count=%s sale_order_ids_sample=%s total_sales=%s "
                "invoice_domain=%s invoice_count=%s invoice_ids_sample=%s total_invoices=%s "
                "company_sales_non_cancel_count=%s company_out_invoice_non_cancel_count=%s"
            ),
            company.id,
            company.name,
            user.id,
            user.login,
            search_term,
            selected_month_start,
            sales_domain,
            sales_count,
            len(sale_order_ids),
            sale_order_ids[:20],
            total_sales,
            invoice_domain,
            invoice_count,
            invoice_ids[:20],
            total_invoices,
            company_sales_count,
            company_invoice_count,
        )

    def _lead_vs_won_distribution(self, total_leads, total_won):
        leads_value = int(total_leads or 0)
        won_value = int(total_won or 0)
        percent_base = float(leads_value or 1)
        return [
            {
                "name": "Total Leads",
                "value": leads_value,
                "percent": round((leads_value * 100.0) / percent_base, 1)
                if leads_value
                else 0.0,
            },
            {
                "name": "Total Won",
                "value": won_value,
                "percent": round((won_value * 100.0) / percent_base, 1)
                if leads_value
                else 0.0,
            },
        ]

    def _recent_crm_rows(self, model, search_domain):
        records = model.search(
            search_domain + [("type", "in", ["lead", "opportunity"])],
            order="create_date desc, id desc",
            limit=10,
        )
        rows = []
        for record in records:
            rows.append(
                {
                    "name": record.name or "",
                    "type": "Lead" if record.type == "lead" else "Opportunity",
                    "stage": record.stage_id.name or "",
                    "revenue": record.expected_revenue or 0.0,
                    "probability": record.probability or 0.0,
                    "create_date": fields.Datetime.to_string(record.create_date)
                    if record.create_date
                    else "",
                }
            )
        return rows

    def _to_datetime_string(self, value_date):
        value_datetime = datetime.combine(value_date, time.min)
        return fields.Datetime.to_string(value_datetime)

    def _get_model(self, model_name):
        try:
            return request.env[model_name]
        except KeyError:
            return None
