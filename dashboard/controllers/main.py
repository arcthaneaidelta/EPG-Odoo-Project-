from odoo import _
import logging
from datetime import datetime, time

from dateutil.relativedelta import relativedelta

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DashboardController(http.Controller):
    @http.route("/dashboard/data", type="json", auth="user")
    def dashboard_data(
        self,
        search="",
        range_start="",
        range_end="",
        activity_scope="system",
    ):
        company = request.env.company
        user = request.env.user
        today = fields.Date.context_today(user)
        search_term = (search or "").strip()
        activity_scope = (activity_scope or "system").strip().lower() or "system"

        date_start, date_end = self._parse_date_range(range_start, range_end, today)

        lead_model = request.env["crm.lead"].sudo()
        partner_model = request.env["res.partner"].sudo()
        sale_model = self._get_model("sale.order")
        invoice_model = self._get_model("account.move")

        revenue = self._build_revenue_kpis(
            invoice_model=invoice_model,
            company_id=company.id,
            search_term=search_term,
            today=today,
            date_start=date_start,
            date_end=date_end,
        )
        clients = self._build_client_kpis(
            sale_model=sale_model,
            invoice_model=invoice_model,
            partner_model=partner_model,
            company_id=company.id,
            search_term=search_term,
            today=today,
            date_start=date_start,
            date_end=date_end,
        )
        commercial = self._build_commercial_kpis(
            lead_model=lead_model,
            sale_model=sale_model,
            company_id=company.id,
            search_term=search_term,
            date_start=date_start,
            date_end=date_end,
        )
        financial = self._build_financial_kpis(
            invoice_model=invoice_model,
            company_id=company.id,
            search_term=search_term,
            today=today,
            date_start=date_start,
            date_end=date_end,
        )

        recent_activity = self._build_recent_activity(
            lead_model=lead_model,
            sale_model=sale_model,
            invoice_model=invoice_model,
            company_id=company.id,
            search_term=search_term,
            date_start=date_start,
            date_end=date_end,
            activity_scope=activity_scope,
            limit=12,
        )
        alerts = self._build_alerts(
            lead_model=lead_model,
            sale_model=sale_model,
            invoice_model=invoice_model,
            company_id=company.id,
            search_term=search_term,
            today=today,
            date_start=date_start,
            date_end=date_end,
        )
        charts = self._build_chart_data(
            lead_model=lead_model,
            invoice_model=invoice_model,
            company_id=company.id,
            search_term=search_term,
            date_start=date_start,
            date_end=date_end,
        )

        company_currency = company.currency_id

        return {
            "user_name": user.name,
            "user_email": user.email or user.login or "",
            "company_name": company.name,
            "currency": {
                "symbol": company_currency.symbol or "",
                "position": company_currency.position or "before",
            },
            "date_range": {
                "start": fields.Date.to_string(date_start),
                "end": fields.Date.to_string(date_end),
            },
            "activity_scope": activity_scope,
            "kpi_groups": [
                {
                    "key": "revenue",
                    "title": _("Revenue KPIs"),
                    "description": _("Daily, weekly, monthly, annual, range-based invoicing and growth."),
                    "metrics": revenue["metrics"],
                },
                {
                    "key": "clients",
                    "title": _("Client KPIs (CTA)"),
                    "description": _("Contract status, payment state, new clients and top client ranking."),
                    "metrics": clients["metrics"],
                },
                {
                    "key": "commercial",
                    "title": _("Commercial KPIs"),
                    "description": _("Leads, quotations, sales outcomes, conversion and active pipeline."),
                    "metrics": commercial["metrics"],
                },
                {
                    "key": "financial",
                    "title": _("Invoicing & Financial KPIs"),
                    "description": _("Invoice lifecycle, cash-flow and income versus expenses."),
                    "metrics": financial["metrics"],
                },
            ],
            "top_clients": clients["top_clients"],
            "income_vs_expenses": financial["income_vs_expenses"],
            "recent_activity": recent_activity,
            "alerts": alerts,
            "charts": charts,
        }

    def _build_revenue_kpis(
        self,
        invoice_model,
        company_id,
        search_term,
        today,
        date_start,
        date_end,
    ):
        reference_date = date_end or today
        month_start = reference_date.replace(day=1)
        month_end = month_start + relativedelta(months=1, days=-1)
        week_start = reference_date - relativedelta(days=reference_date.weekday())
        week_end = week_start + relativedelta(days=6)
        year_start = reference_date.replace(month=1, day=1)
        year_end = reference_date.replace(month=12, day=31)

        if invoice_model is None:
            return {
                "metrics": [
                    self._build_metric("daily_invoicing", _("Daily Invoicing"), 0.0, "currency"),
                    self._build_metric("weekly_invoicing", _("Weekly Invoicing"), 0.0, "currency"),
                    self._build_metric("monthly_invoicing", _("Monthly Invoicing"), 0.0, "currency"),
                    self._build_metric("annual_invoicing", _("Annual Invoicing"), 0.0, "currency"),
                    self._build_metric("range_invoicing", _("Configurable Range Invoicing"), 0.0, "currency"),
                    self._build_metric("total_income", _("Total Income"), 0.0, "currency"),
                    self._build_metric("estimated_profit", _("Estimated Profit"), 0.0, "currency"),
                    self._build_metric("monthly_growth", _("Monthly Growth"), 0.0, "percent"),
                ]
            }

        invoice_model = invoice_model.sudo()
        base_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        if search_term:
            base_domain += self._build_invoice_search_domain(search_term)

        expense_domain = [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        if search_term:
            expense_domain += self._build_invoice_search_domain(search_term)

        daily_domain = list(base_domain) + self._date_domain_within(
            "invoice_date", reference_date, reference_date, date_start, date_end
        )
        weekly_domain = list(base_domain) + self._date_domain_within(
            "invoice_date", week_start, week_end, date_start, date_end
        )
        monthly_domain = list(base_domain) + self._date_domain_within(
            "invoice_date", month_start, month_end, date_start, date_end
        )
        annual_domain = list(base_domain) + self._date_domain_within(
            "invoice_date", year_start, year_end, date_start, date_end
        )
        range_domain = list(base_domain) + self._date_domain("invoice_date", date_start, date_end)
        range_expense_domain = list(expense_domain) + self._date_domain(
            "invoice_date", date_start, date_end
        )
        growth_current_start = max(month_start, date_start)
        growth_current_end = min(month_end, date_end)
        prev_growth_start = None
        prev_growth_end = None
        if growth_current_start <= growth_current_end:
            # Compare month-to-date against the same day window in previous month.
            prev_growth_start = growth_current_start - relativedelta(months=1)
            prev_growth_end = growth_current_end - relativedelta(months=1)
            prev_month_domain = list(base_domain) + self._date_domain(
                "invoice_date", prev_growth_start, prev_growth_end
            )
        else:
            prev_month_domain = list(base_domain) + [("id", "=", 0)]

        daily = self._sum_amount(invoice_model, daily_domain, "amount_total_signed")
        weekly = self._sum_amount(invoice_model, weekly_domain, "amount_total_signed")
        monthly = self._sum_amount(invoice_model, monthly_domain, "amount_total_signed")
        annual = self._sum_amount(invoice_model, annual_domain, "amount_total_signed")
        range_invoicing = self._sum_amount(invoice_model, range_domain, "amount_total_signed")
        total_income = self._sum_amount(invoice_model, range_domain, "amount_total_signed")
        range_expenses = self._sum_amount(
            invoice_model, range_expense_domain, "amount_total_signed", absolute=True
        )
        estimated_profit = range_invoicing - range_expenses

        prev_month_amount = self._sum_amount(
            invoice_model, prev_month_domain, "amount_total_signed"
        )
        monthly_growth = self._calculate_growth_percent(monthly, prev_month_amount)
        growth_trend = "flat"
        if monthly > prev_month_amount:
            growth_trend = "up"
        elif monthly < prev_month_amount:
            growth_trend = "down"
        baseline_missing = abs(prev_month_amount) < 1e-9 and abs(monthly) > 1e-9

        growth_comparison_label = "vs previous month"
        if prev_growth_start and prev_growth_end:
            growth_comparison_label = "vs %s to %s" % (
                fields.Date.to_string(prev_growth_start),
                fields.Date.to_string(prev_growth_end),
            )

        metrics = [
            self._build_metric("daily_invoicing", _("Daily Invoicing"),
                daily,
                "currency",
                "account.move",
                daily_domain,
            ),
            self._build_metric("weekly_invoicing", _("Weekly Invoicing"),
                weekly,
                "currency",
                "account.move",
                weekly_domain,
            ),
            self._build_metric("monthly_invoicing", _("Monthly Invoicing"),
                monthly,
                "currency",
                "account.move",
                monthly_domain,
            ),
            self._build_metric("annual_invoicing", _("Annual Invoicing"),
                annual,
                "currency",
                "account.move",
                annual_domain,
            ),
            self._build_metric("range_invoicing", _("Configurable Range Invoicing"),
                range_invoicing,
                "currency",
                "account.move",
                range_domain,
            ),
            self._build_metric("total_income", _("Total Income"),
                total_income,
                "currency",
                "account.move",
                range_domain,
            ),
            self._build_metric("estimated_profit", _("Estimated Profit"),
                estimated_profit,
                "currency",
            ),
            self._build_metric("monthly_growth", _("Monthly Growth"),
                monthly_growth,
                "percent",
                trend=growth_trend,
                meta={
                    "comparison_label": growth_comparison_label,
                    "current_value": monthly,
                    "previous_value": prev_month_amount,
                    "delta_value": monthly - prev_month_amount,
                    "baseline_missing": baseline_missing,
                },
            ),
        ]
        return {"metrics": metrics}

    def _build_client_kpis(
        self,
        sale_model,
        invoice_model,
        partner_model,
        company_id,
        search_term,
        today,
        date_start,
        date_end,
    ):
        month_start = today.replace(day=1)
        month_end = month_start + relativedelta(months=1, days=-1)

        signed_partner_ids = set()
        unsigned_quote_partner_ids = set()

        signed_sale_domain = [
            ("state", "in", ["sale", "done"]),
            ("company_id", "=", company_id),
        ]
        signed_sale_domain += self._datetime_domain("date_order", date_start, date_end)
        unsigned_quote_domain = [
            ("state", "in", ["draft", "sent"]),
            ("company_id", "=", company_id),
        ]
        unsigned_quote_domain += self._datetime_domain("date_order", date_start, date_end)
        if search_term:
            signed_sale_domain += self._build_sale_search_domain(search_term)
            unsigned_quote_domain += self._build_sale_search_domain(search_term)

        if sale_model is not None:
            sale_model = sale_model.sudo()
            signed_partner_ids = set(
                sale_model.search(signed_sale_domain).mapped("partner_id").ids
            )
            unsigned_quote_partner_ids = set(
                sale_model.search(unsigned_quote_domain).mapped("partner_id").ids
            )

        paid_partner_ids = set()
        signed_paid_partner_ids = set()

        paid_invoice_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["paid", "in_payment"]),
            ("company_id", "=", company_id),
        ]
        paid_invoice_domain += self._date_domain("invoice_date", date_start, date_end)
        if search_term:
            paid_invoice_domain += self._build_invoice_search_domain(search_term)

        signed_paid_invoice_domain = list(paid_invoice_domain) + [
            ("invoice_line_ids.sale_line_ids.order_id.state", "in", ["sale", "done"]),
        ]

        unsigned_paid_invoice_domain = list(paid_invoice_domain) + [
            "|",
            ("invoice_line_ids.sale_line_ids.order_id", "=", False),
            (
                "invoice_line_ids.sale_line_ids.order_id.state",
                "not in",
                ["sale", "done"],
            ),
        ]

        top_clients = []
        if invoice_model is not None:
            invoice_model = invoice_model.sudo()
            paid_partner_ids = set(
                invoice_model.search(paid_invoice_domain).mapped("partner_id").ids
            )
            signed_paid_partner_ids = set(
                invoice_model.search(signed_paid_invoice_domain)
                .mapped("partner_id")
                .ids
            )

            top_client_domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("company_id", "=", company_id),
            ]
            if search_term:
                top_client_domain += self._build_invoice_search_domain(search_term)
            top_client_domain += self._date_domain("invoice_date", date_start, date_end)

            grouped = invoice_model.read_group(
                top_client_domain,
                ["partner_id", "amount_total_signed:sum"],
                ["partner_id"],
                lazy=False,
                orderby="amount_total_signed desc",
                limit=5,
            )
            for row in grouped:
                partner = row.get("partner_id")
                if not partner:
                    continue
                amount = row.get("amount_total_signed_sum")
                if amount is None:
                    amount = row.get("amount_total_signed")
                partner_id = int(partner[0])
                top_clients.append(
                    {
                        "id": partner_id,
                        "name": partner[1],
                        "revenue": float(amount or 0.0),
                        "model": "account.move",
                        "domain": list(top_client_domain)
                        + [("partner_id", "=", partner_id)],
                    }
                )

        new_clients_domain = [
            ("customer_rank", ">", 0),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", company_id),
        ]
        new_clients_domain += self._datetime_domain("create_date", month_start, month_end)
        if search_term:
            new_clients_domain += self._build_partner_search_domain(search_term)
        new_clients = partner_model.search_count(new_clients_domain)

        signed_clients = len(signed_partner_ids)
        signed_paid_clients = len(signed_paid_partner_ids)
        unsigned_paid_clients = len(paid_partner_ids - signed_partner_ids)
        unsigned_unpaid_clients = len(unsigned_quote_partner_ids - paid_partner_ids)

        metrics = [
            self._build_metric("signed_clients", _("Signed (Contract accepted)"),
                signed_clients,
                "number",
                "res.partner",
                self._ids_domain(signed_partner_ids),
            ),
            self._build_metric("signed_paid_clients", _("Signed & Paid"),
                signed_paid_clients,
                "number",
                "res.partner",
                self._ids_domain(signed_paid_partner_ids),
            ),
            self._build_metric("unsigned_paid_clients", _("Unsigned but Paid"),
                unsigned_paid_clients,
                "number",
                "res.partner",
                self._ids_domain(paid_partner_ids - signed_partner_ids),
            ),
            self._build_metric("unsigned_unpaid_clients", _("Unsigned & Unpaid"),
                unsigned_unpaid_clients,
                "number",
                "res.partner",
                self._ids_domain(unsigned_quote_partner_ids - paid_partner_ids),
            ),
            self._build_metric("new_clients_month", _("New Clients (Current Month)"),
                new_clients,
                "number",
                "res.partner",
                new_clients_domain,
            ),
        ]

        return {
            "metrics": metrics,
            "top_clients": top_clients,
        }

    def _build_commercial_kpis(
        self,
        lead_model,
        sale_model,
        company_id,
        search_term,
        date_start,
        date_end,
    ):
        lead_search_domain = self._build_lead_search_domain(search_term)

        new_leads_domain = [
            ("type", "in", ["lead", "opportunity"]),
            ("company_id", "=", company_id),
        ]
        new_leads_domain += lead_search_domain
        new_leads_domain += self._datetime_domain("create_date", date_start, date_end)
        new_leads = lead_model.search_count(new_leads_domain)

        lost_sales_domain = [
            ("type", "=", "opportunity"),
            ("company_id", "=", company_id),
            ("active", "=", False),
            ("stage_id.is_won", "=", False),
        ]
        lost_sales_domain += lead_search_domain
        lost_sales_domain += self._datetime_domain("write_date", date_start, date_end)
        lost_sales = lead_model.search_count(lost_sales_domain)

        opportunity_created_domain = [
            ("type", "=", "opportunity"),
            ("company_id", "=", company_id),
        ]
        opportunity_created_domain += lead_search_domain
        opportunity_created_domain += self._datetime_domain("create_date", date_start, date_end)
        won_opportunity_domain = list(opportunity_created_domain) + [
            ("stage_id.is_won", "=", True)
        ]

        total_opportunities = lead_model.search_count(opportunity_created_domain)
        won_opportunities = lead_model.search_count(won_opportunity_domain)
        conversion = (
            (won_opportunities / float(total_opportunities)) * 100.0
            if total_opportunities
            else 0.0
        )

        pipeline_domain = [
            ("type", "=", "opportunity"),
            ("company_id", "=", company_id),
            ("active", "=", True),
            ("stage_id.is_won", "=", False),
        ]
        pipeline_domain += lead_search_domain
        pipeline_domain += self._datetime_domain("create_date", date_start, date_end)
        pipeline_volume = lead_model.search_count(pipeline_domain)
        pipeline_value = self._sum_amount(lead_model, pipeline_domain, "expected_revenue")

        avg_days_to_close = self._calculate_avg_days_to_close(
            lead_model, company_id, date_start, date_end
        )
        weighted_forecast = self._calculate_weighted_forecast(
            lead_model, company_id, date_start, date_end
        )

        sent_quotes = 0
        pending_quotes = 0
        closed_sales = 0
        sent_quotes_domain = []
        pending_quotes_domain = []
        closed_sales_domain = []

        if sale_model is not None:
            sale_model = sale_model.sudo()
            sale_search_domain = self._build_sale_search_domain(search_term)

            sent_quotes_domain = [
                ("state", "=", "sent"),
                ("company_id", "=", company_id),
            ]
            sent_quotes_domain += sale_search_domain
            sent_quotes_domain += self._datetime_domain("date_order", date_start, date_end)

            pending_quotes_domain = [
                ("state", "in", ["draft", "sent"]),
                ("company_id", "=", company_id),
            ]
            pending_quotes_domain += sale_search_domain
            pending_quotes_domain += self._datetime_domain("date_order", date_start, date_end)

            closed_sales_domain = [
                ("state", "in", ["sale", "done"]),
                ("company_id", "=", company_id),
            ]
            closed_sales_domain += sale_search_domain
            closed_sales_domain += self._datetime_domain("date_order", date_start, date_end)

            sent_quotes = sale_model.search_count(sent_quotes_domain)
            pending_quotes = sale_model.search_count(pending_quotes_domain)
            closed_sales = sale_model.search_count(closed_sales_domain)

        metrics = [
            self._build_metric("new_leads", _("New Leads"),
                new_leads,
                "number",
                "crm.lead",
                new_leads_domain,
            ),
            self._build_metric("sent_quotes", _("Sent Quotes"),
                sent_quotes,
                "number",
                "sale.order" if sale_model is not None else "",
                sent_quotes_domain,
            ),
            self._build_metric("pending_quotes", _("Pending Quotes"),
                pending_quotes,
                "number",
                "sale.order" if sale_model is not None else "",
                pending_quotes_domain,
            ),
            self._build_metric("closed_sales", _("Closed Sales"),
                closed_sales,
                "number",
                "sale.order" if sale_model is not None else "",
                closed_sales_domain,
            ),
            self._build_metric("lost_sales", _("Lost Sales"),
                lost_sales,
                "number",
                "crm.lead",
                lost_sales_domain,
            ),
            self._build_metric("sales_conversion", _("Sales Conversion"),
                conversion,
                "percent",
                "crm.lead",
                won_opportunity_domain,
            ),
            self._build_metric("pipeline_value", _("Pipeline Value"),
                pipeline_value,
                "currency",
                "crm.lead",
                pipeline_domain,
            ),
            self._build_metric("avg_days_to_close", _("Avg Days to Close"),
                avg_days_to_close,
                "number",
                "crm.lead",
                won_opportunity_domain,
            ),
            self._build_metric("weighted_forecast", _("Weighted Forecast"),
                weighted_forecast,
                "currency",
                "crm.lead",
                pipeline_domain,
            ),
            self._build_metric("pipeline_volume", _("Pipeline Volume"),
                pipeline_volume,
                "number",
                "crm.lead",
                pipeline_domain,
            ),
        ]
        return {"metrics": metrics}

    def _build_financial_kpis(
        self,
        invoice_model,
        company_id,
        search_term,
        today,
        date_start,
        date_end,
    ):
        if invoice_model is None:
            empty_metrics = [
                self._build_metric("issued_invoices", _("Issued Invoices"), 0, "number"),
                self._build_metric("paid_invoices", _("Paid Invoices"), 0, "number"),
                self._build_metric("pending_invoices", _("Pending Invoices"), 0, "number"),
                self._build_metric("overdue_invoices", _("Overdue Invoices"), 0, "number"),
                self._build_metric("rectified_invoices", _("Rectified Invoices"), 0, "number"),
                self._build_metric("cash_flow", _("Cash Flow"), 0.0, "currency"),
            ]
            return {
                "metrics": empty_metrics,
                "income_vs_expenses": {
                    "income": 0.0,
                    "expenses": 0.0,
                    "balance": 0.0,
                },
            }

        invoice_model = invoice_model.sudo()
        invoice_search_domain = self._build_invoice_search_domain(search_term)

        issued_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        issued_domain += invoice_search_domain
        issued_domain += self._date_domain("invoice_date", date_start, date_end)

        paid_domain = list(issued_domain) + [
            ("payment_state", "in", ["paid", "in_payment"])
        ]

        pending_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("company_id", "=", company_id),
            ("invoice_date_due", ">=", fields.Date.to_string(today)),
        ]
        pending_domain += invoice_search_domain
        pending_domain += self._date_domain("invoice_date", date_start, date_end)

        overdue_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("company_id", "=", company_id),
            ("invoice_date_due", "<", fields.Date.to_string(today)),
        ]
        overdue_domain += invoice_search_domain
        overdue_domain += self._date_domain("invoice_date", date_start, date_end)

        rectified_domain = [
            ("move_type", "=", "out_refund"),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        rectified_domain += invoice_search_domain
        rectified_domain += self._date_domain("invoice_date", date_start, date_end)

        income_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        income_domain += invoice_search_domain
        income_domain += self._date_domain("invoice_date", date_start, date_end)

        expense_domain = [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        expense_domain += invoice_search_domain
        expense_domain += self._date_domain("invoice_date", date_start, date_end)

        paid_income_domain = list(income_domain) + [
            ("payment_state", "in", ["paid", "in_payment"])
        ]
        paid_expense_domain = list(expense_domain) + [
            ("payment_state", "in", ["paid", "in_payment"])
        ]

        issued = invoice_model.search_count(issued_domain)
        paid = invoice_model.search_count(paid_domain)
        pending = invoice_model.search_count(pending_domain)
        overdue = invoice_model.search_count(overdue_domain)
        rectified = invoice_model.search_count(rectified_domain)

        income = self._sum_amount(invoice_model, income_domain, "amount_total_signed")
        expenses = self._sum_amount(
            invoice_model, expense_domain, "amount_total_signed", absolute=True
        )
        paid_income = self._sum_amount(
            invoice_model, paid_income_domain, "amount_total_signed"
        )
        paid_expenses = self._sum_amount(
            invoice_model, paid_expense_domain, "amount_total_signed", absolute=True
        )

        cash_flow = paid_income - paid_expenses
        balance = income - expenses

        metrics = [
            self._build_metric("issued_invoices", _("Issued Invoices"),
                issued,
                "number",
                "account.move",
                issued_domain,
            ),
            self._build_metric("paid_invoices", _("Paid Invoices"),
                paid,
                "number",
                "account.move",
                paid_domain,
            ),
            self._build_metric("pending_invoices", _("Pending Invoices"),
                pending,
                "number",
                "account.move",
                pending_domain,
            ),
            self._build_metric("overdue_invoices", _("Overdue Invoices"),
                overdue,
                "number",
                "account.move",
                overdue_domain,
            ),
            self._build_metric("rectified_invoices", _("Rectified Invoices"),
                rectified,
                "number",
                "account.move",
                rectified_domain,
            ),
            self._build_metric("cash_flow", _("Cash Flow (Real-time liquidity)"),
                cash_flow,
                "currency",
            ),
        ]

        return {
            "metrics": metrics,
            "income_vs_expenses": {
                "income": income,
                "expenses": expenses,
                "balance": balance,
            },
        }

    def _build_recent_activity(
        self,
        lead_model,
        sale_model,
        invoice_model,
        company_id,
        search_term,
        date_start,
        date_end,
        activity_scope,
        limit=12,
    ):
        activities = []

        lead_domain = [("company_id", "=", company_id), ("type", "in", ["lead", "opportunity"])]
        lead_domain += self._build_lead_search_domain(search_term)
        lead_domain += self._datetime_domain("write_date", date_start, date_end)
        lead_records = lead_model.search(lead_domain, order="write_date desc, id desc", limit=12)
        for lead in lead_records:
            timestamp = lead.write_date or lead.create_date
            activities.append(
                {
                    "id": f"lead_{lead.id}",
                    "model": "crm.lead",
                    "res_id": lead.id,
                    "domain": [("id", "=", lead.id)],
                    "title": lead.name or "Lead",
                    "subtitle": lead.stage_id.name or ("Lead" if lead.type == "lead" else "Opportunity"),
                    "client": lead.partner_name or lead.partner_id.name or "",
                    "department": lead.team_id.name or "",
                    "datetime": fields.Datetime.to_string(timestamp) if timestamp else "",
                }
            )

        if sale_model is not None:
            sale_model = sale_model.sudo()
            sale_domain = [("company_id", "=", company_id)]
            sale_domain += self._build_sale_search_domain(search_term)
            sale_domain += self._datetime_domain("write_date", date_start, date_end)
            sale_records = sale_model.search(
                sale_domain,
                order="write_date desc, id desc",
                limit=12,
            )
            for order in sale_records:
                timestamp = order.write_date or order.date_order
                activities.append(
                    {
                        "id": f"sale_{order.id}",
                        "model": "sale.order",
                        "res_id": order.id,
                        "domain": [("id", "=", order.id)],
                        "title": order.name or "Quotation",
                        "subtitle": self._sale_state_label(order.state),
                        "client": order.partner_id.name or "",
                        "department": order.team_id.name or "",
                        "datetime": fields.Datetime.to_string(timestamp) if timestamp else "",
                    }
                )

        if invoice_model is not None:
            invoice_model = invoice_model.sudo()
            invoice_domain = [
                ("company_id", "=", company_id),
                ("move_type", "in", ["out_invoice", "out_refund", "in_invoice", "in_refund"]),
                ("state", "!=", "cancel"),
            ]
            invoice_domain += self._build_invoice_search_domain(search_term)
            invoice_domain += self._datetime_domain("write_date", date_start, date_end)
            invoice_records = invoice_model.search(
                invoice_domain,
                order="write_date desc, id desc",
                limit=12,
            )
            for invoice in invoice_records:
                timestamp = invoice.write_date or invoice.invoice_date
                activities.append(
                    {
                        "id": f"invoice_{invoice.id}",
                        "model": "account.move",
                        "res_id": invoice.id,
                        "domain": [("id", "=", invoice.id)],
                        "title": invoice.name or invoice.ref or "Invoice",
                        "subtitle": self._invoice_state_label(invoice.state, invoice.payment_state),
                        "client": invoice.partner_id.name or "",
                        "department": invoice.journal_id.name or "",
                        "datetime": fields.Datetime.to_string(timestamp) if timestamp else "",
                    }
                )

        if activity_scope == "client":
            activities = [item for item in activities if item.get("client")]
        elif activity_scope == "department":
            activities = [item for item in activities if item.get("department")]

        activities.sort(key=lambda row: row.get("datetime") or "", reverse=True)
        return activities[:limit]

    def _build_alerts(
        self,
        lead_model,
        sale_model,
        invoice_model,
        company_id,
        search_term,
        today,
        date_start,
        date_end,
    ):
        alerts = []

        overdue_count = 0
        overdue_domain = []
        if invoice_model is not None:
            invoice_model = invoice_model.sudo()
            overdue_domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ["not_paid", "partial"]),
                ("company_id", "=", company_id),
                ("invoice_date_due", "<", fields.Date.to_string(today)),
            ]
            overdue_domain += self._build_invoice_search_domain(search_term)
            overdue_domain += self._date_domain("invoice_date", date_start, date_end)
            overdue_count = invoice_model.search_count(overdue_domain)

        unresponsive_quotes = 0
        unresponsive_domain = []
        if sale_model is not None:
            sale_model = sale_model.sudo()
            stale_quote_date = today - relativedelta(days=10)
            unresponsive_domain = [
                ("state", "=", "sent"),
                ("company_id", "=", company_id),
                ("date_order", "<", self._to_datetime_string(stale_quote_date)),
            ]
            unresponsive_domain += self._build_sale_search_domain(search_term)
            unresponsive_domain += self._datetime_domain("date_order", date_start, date_end)
            unresponsive_quotes = sale_model.search_count(unresponsive_domain)

        unattended_leads_domain = [
            ("type", "in", ["lead", "opportunity"]),
            ("company_id", "=", company_id),
            ("active", "=", True),
            ("stage_id.is_won", "=", False),
            ("write_date", "<", self._to_datetime_string(today - relativedelta(days=7))),
        ]
        unattended_leads_domain += self._build_lead_search_domain(search_term)
        unattended_leads_domain += self._datetime_domain("write_date", date_start, date_end)
        unattended_leads = lead_model.search_count(unattended_leads_domain)

        quarter_end = self._quarter_end_date(today)
        days_to_quarter_end = (quarter_end - today).days
        quarter_end_domain = [
            ("type", "=", "opportunity"),
            ("company_id", "=", company_id),
            ("active", "=", True),
            ("stage_id.is_won", "=", False),
        ]
        quarter_end_domain += self._build_lead_search_domain(search_term)
        quarter_end_domain += self._datetime_domain("create_date", date_start, date_end)
        quarter_end_open = lead_model.search_count(quarter_end_domain)

        quarter_reminder_value = quarter_end_open if days_to_quarter_end <= 15 else 0

        if overdue_count > 0:
            alerts.append(
                {
                    "key": "overdue_invoices",
                    "label": _("Overdue invoices"),
                    "value": overdue_count,
                    "severity": "high",
                    "model": "account.move" if invoice_model is not None else "",
                    "domain": overdue_domain,
                    "note": _("Customer invoices with passed due dates."),
                }
            )
            
        if unresponsive_quotes > 0:
            alerts.append(
                {
                    "key": "unresponsive_quotes",
                    "label": _("Unresponsive quotes"),
                    "value": unresponsive_quotes,
                    "severity": "medium",
                    "model": "sale.order" if sale_model is not None else "",
                    "domain": unresponsive_domain,
                    "note": _("Quotations sent more than 10 days ago."),
                }
            )
            
        if unattended_leads > 0:
            alerts.append(
                {
                    "key": "unattended_leads",
                    "label": _("Unattended leads"),
                    "value": unattended_leads,
                    "severity": "medium",
                    "model": "crm.lead",
                    "domain": unattended_leads_domain,
                    "note": _("No updates in the last 7 days."),
                }
            )
            
        if quarter_reminder_value > 0:
            alerts.append(
                {
                    "key": "quarter_end",
                    "label": _("Quarter-end reminders"),
                    "value": quarter_reminder_value,
                    "severity": "high",
                    "model": "crm.lead",
                    "domain": quarter_end_domain,
                    "note": _("{days_to_quarter_end} days remaining to close the quarter ({quarter_end})."),
                }
            )

        return alerts

    def _build_chart_data(
        self,
        lead_model,
        invoice_model,
        company_id,
        search_term,
        date_start,
        date_end,
    ):
        sales_history = self._build_sales_history(
            invoice_model=invoice_model,
            lead_model=lead_model,
            company_id=company_id,
            search_term=search_term,
            date_start=date_start,
            date_end=date_end,
        )
        leads_vs_won = self._build_leads_vs_won(
            lead_model=lead_model,
            company_id=company_id,
            search_term=search_term,
            date_start=date_start,
            date_end=date_end,
        )
        pipeline_velocity = self._calculate_pipeline_velocity(
            lead_model=lead_model,
            company_id=company_id,
            date_start=date_start,
            date_end=date_end,
        )
        conversion_by_origin = self._build_conversion_by_origin(
            lead_model=lead_model,
            company_id=company_id,
            date_start=date_start,
            date_end=date_end,
        )
        return {
            "sales_history": sales_history,
            "leads_vs_won": leads_vs_won,
            "pipeline_velocity": pipeline_velocity,
            "conversion_by_origin": conversion_by_origin,
        }

    def _build_sales_history(
        self, invoice_model, lead_model, company_id, search_term, date_start, date_end
    ):
        current_month_start = date_end.replace(day=1)
        month_starts = [
            current_month_start - relativedelta(months=offset)
            for offset in range(5, -1, -1)
        ]

        if invoice_model is None:
            return [
                {
                    "label": month_start.strftime("%b"),
                    "value": 0.0,
                    "forecast": 0.0,
                }
                for month_start in month_starts
            ]

        invoice_model = invoice_model.sudo()
        base_domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        if search_term:
            base_domain += self._build_invoice_search_domain(search_term)

        points = []
        for month_start in month_starts:
            month_end = month_start + relativedelta(months=1, days=-1)
            month_domain = list(base_domain) + self._date_domain_within(
                "invoice_date", month_start, month_end, date_start, date_end
            )
            amount = self._sum_amount(invoice_model, month_domain, "amount_total_signed")
            
            # Forecast logic: simple weighted forecast for open opportunities closing this month
            forecast_domain = [
                ('type', '=', 'opportunity'),
                ('company_id', '=', company_id),
                ('active', '=', True),
                ('stage_id.is_won', '=', False),
                ('date_deadline', '>=', fields.Date.to_string(month_start)),
                ('date_deadline', '<=', fields.Date.to_string(month_end))
            ]
            forecast_amount = sum(l.expected_revenue * (l.probability / 100.0) for l in lead_model.search(forecast_domain))

            points.append(
                {
                    "label": month_start.strftime("%b"),
                    "value": amount,
                    "forecast": amount + forecast_amount, # Show accumulated potential
                }
            )

        return points

    def _calculate_avg_days_to_close(self, lead_model, company_id, date_start, date_end):
        domain = [
            ('type', '=', 'opportunity'),
            ('company_id', '=', company_id),
            ('stage_id.is_won', '=', True),
            ('date_closed', '>=', fields.Datetime.to_string(datetime.combine(date_start, time.min))),
            ('date_closed', '<=', fields.Datetime.to_string(datetime.combine(date_end, time.max))),
        ]
        leads = lead_model.search(domain)
        if not leads:
            return 0.0
        total_days = sum((l.date_closed.date() - l.create_date.date()).days for l in leads)
        return round(total_days / len(leads), 1)

    def _calculate_weighted_forecast(self, lead_model, company_id, date_start, date_end):
        domain = [
            ('type', '=', 'opportunity'),
            ('company_id', '=', company_id),
            ('active', '=', True),
            ('stage_id.is_won', '=', False),
        ]
        leads = lead_model.search(domain)
        forecast = sum((l.expected_revenue * (l.probability / 100.0)) for l in leads)
        return forecast

    def _calculate_pipeline_velocity(self, lead_model, company_id, date_start, date_end):
        # Calculate average time spent in each stage for opportunities won in the period
        # Only include stages requested by the user to avoid clutter from other modules/teams
        all_stages = request.env["crm.stage"].sudo().search(
            [("team_id", "=", False)], 
            order="sequence"
        )
        requested_names = {'new', 'qualified', 'proposition', 'won', 'lost'}
        stages = all_stages.filtered(lambda s: s.name.lower() in requested_names)
        
        # If the specific stages weren't found, fallback to active ones to avoid an empty chart
        if not stages:
            stages = all_stages.filtered(lambda s: not s.is_won)[:5]

        won_domain = [
            ("type", "=", "opportunity"),
            ("company_id", "=", company_id),
            ("stage_id.is_won", "=", True),
            ("date_closed", ">=", fields.Datetime.to_string(datetime.combine(date_start, time.min))),
            ("date_closed", "<=", fields.Datetime.to_string(datetime.combine(date_end, time.max))),
        ]
        won_leads = lead_model.search(won_domain)

        if not won_leads:
            return [{"label": s.name, "days": 0.0} for s in stages]

        # Get tracking data for these leads for stage changes
        tracking_values = request.env["mail.tracking.value"].search(
            [
                ("mail_message_id.model", "=", "crm.lead"),
                ("mail_message_id.res_id", "in", won_leads.ids),
                ("field_id.name", "=", "stage_id"),
            ],
            order="create_date asc",
        )

        # Map tracking history to leads
        lead_history = {}
        for track in tracking_values:
            lead_id = track.mail_message_id.res_id
            if lead_id not in lead_history:
                lead_history[lead_id] = []
            lead_history[lead_id].append(
                {
                    "date": track.create_date,
                    "old_stage": track.old_value_integer,
                    "new_stage": track.new_value_integer,
                }
            )

        # Calculate durations spent in each stage
        stage_durations = {s.id: [] for s in stages}
        for lead in won_leads:
            history = lead_history.get(lead.id, [])
            last_dt = lead.create_date

            # Process transitions to calculate time spent in the 'old' stage
            for transition in history:
                old_stage_id = transition["old_stage"]
                trans_date = transition["date"]
                delta = (trans_date - last_dt).total_seconds() / 86400.0
                
                # Help Pyre2 understand that this is a list
                durations_list = stage_durations.get(old_stage_id)
                if durations_list is not None:
                    durations_list.append(max(0.0, delta))
                last_dt = trans_date

            # After all transitions, calculate time spent in the CURRENT stage (important for Won/Lost)
            current_stage_id = lead.stage_id.id
            now_dt = datetime.now()
            current_delta = (now_dt - last_dt).total_seconds() / 86400.0
            
            current_durations_list = stage_durations.get(current_stage_id)
            if current_durations_list is not None:
                current_durations_list.append(max(0.0, current_delta))

        velocity_points = []
        for stage in stages:
            durations = stage_durations.get(stage.id, [])
            avg_days = sum(durations) / len(durations) if durations else 0.0
            velocity_points.append(
                {
                    "label": stage.name,
                    "days": round(avg_days, 1),
                }
            )

        return velocity_points

    def _build_conversion_by_origin(self, lead_model, company_id, date_start, date_end):
        # Group by source_type from crm_base. We use a broader range for 'Won' to show real-time performance.
        domain = [
            ('company_id', '=', company_id),
            ('type', 'in', ['lead', 'opportunity']),
        ]
        # Only filter by date for the initial lead creation if we want 'This Period's Leads'
        # But for 'Real Time' conversion, we should show all relevant data.
        # Let's keep the filter but ensure we use the correct count key.
        domain += self._datetime_domain("create_date", date_start, date_end)
        
        groups = lead_model.read_group(domain, ['source_type', 'stage_id'], ['source_type', 'stage_id'], lazy=False)
        
        origin_data = {}
        for row in groups:
            origin_key = row.get('source_type') or 'Other'
            # Convert selection key to label if possible, though keys are fine for now.
            origin = origin_key.capitalize() if isinstance(origin_key, str) else 'Other'
            
            if origin not in origin_data:
                origin_data[origin] = {'total': 0, 'won': 0}
            
            # Robust count extraction from read_group
            count = row.get('__count') or row.get('id_count') or row.get('source_type_count') or 0
            origin_data[origin]['total'] += count
            
            stage_id = row.get('stage_id')
            if stage_id:
                stage = request.env['crm.stage'].browse(stage_id[0])
                if stage.is_won:
                    origin_data[origin]['won'] += count
        
        result = []
        for origin, vals in origin_data.items():
            rate = (vals['won'] / vals['total'] * 100.0) if vals['total'] else 0.0
            result.append({
                'origin': origin,
                'total': vals['total'],
                'won': vals['won'],
                'rate': round(rate, 1)
            })
        return sorted(result, key=lambda x: x['total'], reverse=True)

    def _build_leads_vs_won(
        self,
        lead_model,
        company_id,
        search_term,
        date_start,
        date_end,
    ):
        search_domain = self._build_lead_search_domain(search_term)

        total_leads_domain = [
            ("type", "in", ["lead", "opportunity"]),
            ("company_id", "=", company_id),
        ]
        total_leads_domain += search_domain
        total_leads_domain += self._datetime_domain("create_date", date_start, date_end)

        total_won_domain = [
            ("type", "=", "opportunity"),
            ("company_id", "=", company_id),
            ("stage_id.is_won", "=", True),
        ]
        total_won_domain += search_domain
        total_won_domain += self._datetime_domain("create_date", date_start, date_end)

        return {
            "total_leads": lead_model.search_count(total_leads_domain),
            "total_won": lead_model.search_count(total_won_domain),
        }

    def _build_metric(
        self, key, label, value, value_type, model="", domain=None, trend="", meta=None
    ):
        return {
            "key": key,
            "label": label,
            "value": value,
            "value_type": value_type,
            "model": model,
            "domain": domain or [],
            "trend": trend or "",
            "meta": meta or {},
        }

    def _ids_domain(self, ids):
        values = list(ids or [])
        return [("id", "in", values)] if values else [("id", "=", 0)]

    def _build_lead_search_domain(self, search_term):
        term = (search_term or "").strip()
        if not term:
            return []
        return [
            "|",
            "|",
            "|",
            ("name", "ilike", term),
            ("partner_name", "ilike", term),
            ("contact_name", "ilike", term),
            ("email_from", "ilike", term),
        ]

    def _build_sale_search_domain(self, search_term):
        term = (search_term or "").strip()
        if not term:
            return []
        return [
            "|",
            "|",
            "|",
            ("name", "ilike", term),
            ("partner_id.name", "ilike", term),
            ("client_order_ref", "ilike", term),
            ("origin", "ilike", term),
        ]

    def _build_invoice_search_domain(self, search_term):
        term = (search_term or "").strip()
        if not term:
            return []
        return [
            "|",
            "|",
            "|",
            ("name", "ilike", term),
            ("partner_id.name", "ilike", term),
            ("invoice_origin", "ilike", term),
            ("ref", "ilike", term),
        ]

    def _build_partner_search_domain(self, search_term):
        term = (search_term or "").strip()
        if not term:
            return []
        return [
            "|",
            "|",
            ("name", "ilike", term),
            ("email", "ilike", term),
            ("phone", "ilike", term),
        ]

    def _date_domain(self, field_name, start_date, end_date):
        return [
            (field_name, ">=", fields.Date.to_string(start_date)),
            (field_name, "<=", fields.Date.to_string(end_date)),
        ]

    def _date_domain_within(
        self, field_name, period_start, period_end, filter_start, filter_end
    ):
        start = max(period_start, filter_start)
        end = min(period_end, filter_end)
        if start > end:
            return [("id", "=", 0)]
        return self._date_domain(field_name, start, end)

    def _datetime_domain(self, field_name, start_date, end_date):
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date + relativedelta(days=1), time.min)
        return [
            (field_name, ">=", fields.Datetime.to_string(start_dt)),
            (field_name, "<", fields.Datetime.to_string(end_dt)),
        ]

    def _parse_date_range(self, range_start, range_end, today):
        default_start = today.replace(day=1)
        start_date = self._parse_date(range_start) or default_start
        end_date = self._parse_date(range_end) or today
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        return start_date, end_date

    def _parse_date(self, value):
        raw_value = (value or "").strip()
        if not raw_value:
            return None
        try:
            return datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _sum_amount(self, model, domain, amount_field, absolute=False):
        group = model.read_group(domain, [f"{amount_field}:sum"], [])
        if not group:
            return 0.0
        row = group[0]
        value = row.get(f"{amount_field}_sum")
        if value is None:
            value = row.get(amount_field)
        amount = float(value or 0.0)
        return abs(amount) if absolute else amount

    def _calculate_growth_percent(self, current_value, previous_value):
        current = float(current_value or 0.0)
        previous = float(previous_value or 0.0)

        if abs(previous) < 1e-9:
            if current > 0:
                # New growth versus zero baseline.
                return 100.0
            if current < 0:
                return -100.0
            return 0.0

        growth = ((current - previous) / abs(previous)) * 100.0
        # Keep growth readable for dashboard KPI cards.
        return max(min(growth, 100.0), -100.0)

    def _quarter_end_date(self, value_date):
        quarter = ((value_date.month - 1) // 3) + 1
        quarter_end_month = quarter * 3
        quarter_end = value_date.replace(month=quarter_end_month, day=1)
        return quarter_end + relativedelta(months=1, days=-1)

    def _to_datetime_string(self, value_date):
        return fields.Datetime.to_string(datetime.combine(value_date, time.min))

    def _sale_state_label(self, state):
        labels = {
            "draft": "Draft Quotation",
            "sent": "Quotation Sent",
            "sale": "Sales Order",
            "done": "Done",
            "cancel": "Cancelled",
        }
        return labels.get(state, state or "Sale")

    def _invoice_state_label(self, state, payment_state):
        if state == "draft":
            return "Draft Invoice"
        if state == "posted":
            if payment_state in ["paid", "in_payment"]:
                return "Posted - Paid"
            if payment_state in ["partial", "not_paid"]:
                return "Posted - Pending"
            return "Posted"
        if state == "cancel":
            return "Cancelled"
        return state or "Invoice"

    def _get_model(self, model_name):
        try:
            return request.env[model_name]
        except KeyError:
            _logger.info("CRM dashboard model not installed: %s", model_name)
            return None
