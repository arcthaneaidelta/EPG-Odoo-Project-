/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";

const DEFAULT_DATA = {
    userName: "",
    userEmail: "",
    companyName: "",
    currency: {
        symbol: "",
        position: "before",
    },
    dateRange: {
        start: "",
        end: "",
    },
    quickStats: [],
    charts: {
        sales: {
            points: [],
            polyline: "",
            maxLabel: "0",
            midLabel: "0",
            peakValueLabel: "0",
            peakLabel: "",
        },
        leadsVsWon: {
            totalLeads: 0,
            totalWon: 0,
            wonRatio: 0,
            wonRateLabel: "0%",
        },
    },
    kpiGroups: [],
    topClients: [],
    incomeVsExpenses: {
        income: 0,
        expenses: 0,
        balance: 0,
        incomeLabel: "0",
        expensesLabel: "0",
        balanceLabel: "0",
    },
    recentActivity: [],
    alerts: [],
};
const FILTER_CACHE_KEY = "__dashboardFilterCacheV1";

export class Dashboard extends Component {
    setup() {
        this.actionService = useService("action");
        this.searchTimer = null;
        this.state = useState({
            loading: true,
            search: "",
            rangeStart: this.getMonthStartDate(),
            rangeEnd: this.getTodayDate(),
            requestToken: 0,
            data: { ...DEFAULT_DATA },
        });
        this.restoreFilters();

        onWillStart(async () => {
            await this.loadDashboard();
        });

        onWillUnmount(() => {
            if (this.searchTimer) {
                clearTimeout(this.searchTimer);
            }
        });
    }

    async loadDashboard() {
        const token = ++this.state.requestToken;
        this.state.loading = true;
        this.persistFilters();
        try {
            const data = await rpc("/dashboard/data", {
                search: this.state.search,
                range_start: this.state.rangeStart,
                range_end: this.state.rangeEnd,
            });
            if (token !== this.state.requestToken) {
                return;
            }
            const normalized = this.normalizeData(data || {});
            this.state.data = normalized;
            if (normalized.dateRange.start) {
                this.state.rangeStart = normalized.dateRange.start;
            }
            if (normalized.dateRange.end) {
                this.state.rangeEnd = normalized.dateRange.end;
            }
            this.persistFilters();
        } finally {
            if (token === this.state.requestToken) {
                this.state.loading = false;
            }
        }
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value || "";
        this.persistFilters();
        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }
        this.searchTimer = setTimeout(() => this.loadDashboard(), 320);
    }

    onSearchKeydown(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        ev.preventDefault();
        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }
        this.persistFilters();
        this.loadDashboard();
    }

    onRangeStartChange(ev) {
        const value = (ev.target.value || "").trim() || this.getMonthStartDate();
        this.state.rangeStart = value;
        if (this.state.rangeEnd && value > this.state.rangeEnd) {
            this.state.rangeEnd = value;
        }
        this.persistFilters();
        this.loadDashboard();
    }

    onRangeEndChange(ev) {
        const value = (ev.target.value || "").trim() || this.getTodayDate();
        this.state.rangeEnd = value;
        if (this.state.rangeStart && value < this.state.rangeStart) {
            this.state.rangeStart = value;
        }
        this.persistFilters();
        this.loadDashboard();
    }

    onMetricClick(metric) {
        if (!metric || !metric.model) {
            return;
        }
        this.persistFilters();
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: metric.label || "Records",
            res_model: metric.model,
            views: [
                [false, "list"],
                [false, "form"],
                [false, "kanban"],
                [false, "pivot"],
                [false, "graph"],
            ],
            view_mode: "list,form,kanban,pivot,graph",
            target: "current",
            domain: metric.domain || [],
        });
    }

    onTopClientClick(client) {
        if (!client || !client.model) {
            return;
        }
        this.persistFilters();
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: client.name || "Client Revenue",
            res_model: client.model,
            views: [
                [false, "list"],
                [false, "form"],
                [false, "pivot"],
                [false, "graph"],
            ],
            view_mode: "list,form,pivot,graph",
            target: "current",
            domain: client.domain || [],
        });
    }

    onAlertClick(alert) {
        if (!alert || !alert.model) {
            return;
        }
        this.persistFilters();
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: alert.label || "Alerts",
            res_model: alert.model,
            views: [
                [false, "list"],
                [false, "form"],
                [false, "kanban"],
                [false, "pivot"],
                [false, "graph"],
            ],
            view_mode: "list,form,kanban,pivot,graph",
            target: "current",
            domain: alert.domain || [],
        });
    }

    onActivityClick(item) {
        if (!item || !item.model || !item.resId) {
            return;
        }
        this.persistFilters();
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: item.title || "Activity",
            res_model: item.model,
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
            res_id: item.resId,
        });
    }

    onQuickStatClick(stat) {
        if (!stat || !stat.metric) {
            return;
        }
        this.onMetricClick(stat.metric);
    }

    onRefreshClick() {
        if (typeof window === "undefined") {
            this.loadDashboard();
            return;
        }
        const store = this.getFilterCacheStore();
        delete store[this.getFilterCacheKey()];
        window.location.reload();
    }

    onExportExcel() {
        const excelXml = this.buildExcelXml();
        this.downloadBlob(
            `\ufeff${excelXml}`,
            "application/vnd.ms-excel;charset=utf-8;",
            this.getExportFileName("xls")
        );
    }

    onExportPDF() {
        const popup = window.open("", "_blank", "width=1180,height=900");
        if (!popup) {
            return;
        }

        const html = this.buildPdfHtml();
        popup.document.open();
        popup.document.write(html);
        popup.document.close();

        const triggerPrint = () => {
            popup.focus();
            popup.print();
        };

        if (popup.document.readyState === "complete") {
            setTimeout(triggerPrint, 120);
            return;
        }

        popup.addEventListener(
            "load",
            () => {
                setTimeout(triggerPrint, 120);
            },
            { once: true }
        );
        // Fallback in case load event does not fire in some browsers.
        setTimeout(triggerPrint, 700);
    }

    getScrollContainer() {
        if (this.el && this.el.classList && this.el.classList.contains("dashboard_root")) {
            return this.el;
        }
        if (this.el) {
            const nestedRoot = this.el.querySelector(".dashboard_root");
            if (nestedRoot) {
                return nestedRoot;
            }
            const closestRoot = this.el.closest(".dashboard_root");
            if (closestRoot) {
                return closestRoot;
            }
        }
        return document.querySelector(".dashboard_root") || document.documentElement;
    }

    scrollToTop() {
        const container = this.getScrollContainer();
        if (!container) {
            return;
        }
        container.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    }

    scrollToBottom() {
        const container = this.getScrollContainer();
        if (!container) {
            return;
        }
        container.scrollTo({
            top: container.scrollHeight,
            behavior: "smooth",
        });
    }

    onSideNavClick(sectionId) {
        const targetId = (sectionId || "").trim();
        if (!targetId) {
            return;
        }
        const container = this.getScrollContainer();
        if (!container) {
            return;
        }
        const target =
            container.querySelector(`#${targetId}`) ||
            (this.el && this.el.querySelector ? this.el.querySelector(`#${targetId}`) : null) ||
            document.getElementById(targetId);
        if (!target) {
            return;
        }
        target.scrollIntoView({
            behavior: "smooth",
            block: "start",
            inline: "nearest",
        });
    }

    getFilterCacheKey() {
        const action = (this.props && this.props.action) || {};
        const actionKey = action.xml_id || action.id || action.name || "dashboard";
        return String(actionKey);
    }

    getFilterCacheStore() {
        if (typeof window === "undefined") {
            return {};
        }
        if (!window[FILTER_CACHE_KEY]) {
            window[FILTER_CACHE_KEY] = {};
        }
        return window[FILTER_CACHE_KEY];
    }

    persistFilters() {
        if (typeof window === "undefined") {
            return;
        }
        const payload = {
            search: this.state.search || "",
            rangeStart: this.state.rangeStart || this.getMonthStartDate(),
            rangeEnd: this.state.rangeEnd || this.getTodayDate(),
        };
        const store = this.getFilterCacheStore();
        store[this.getFilterCacheKey()] = payload;
    }

    restoreFilters() {
        if (typeof window === "undefined") {
            return;
        }
        const store = this.getFilterCacheStore();
        const saved = store[this.getFilterCacheKey()];
        if (!saved) {
            return;
        }
        try {
            if (saved.search !== undefined) {
                this.state.search = saved.search || "";
            }
            if (saved.rangeStart) {
                this.state.rangeStart = saved.rangeStart;
            }
            if (saved.rangeEnd) {
                this.state.rangeEnd = saved.rangeEnd;
            }
            if (this.state.rangeStart && this.state.rangeEnd && this.state.rangeStart > this.state.rangeEnd) {
                this.state.rangeEnd = this.state.rangeStart;
            }
        } catch (_error) {
            // Ignore broken cached value and continue with defaults.
        }
    }

    normalizeData(data) {
        const currency = this.normalizeCurrency(data.currency);

        const kpiGroups = (data.kpi_groups || []).map((group, groupIndex) => ({
            id: group.key || `group_${groupIndex}`,
            key: group.key || "",
            title: group.title || "",
            description: group.description || "",
            metrics: (group.metrics || []).map((metric, metricIndex) => {
                const trendClass = this.resolveMetricTrend(metric);
                return {
                    ...metric,
                    id: metric.key || `${group.key || groupIndex}_${metricIndex}`,
                    actionable: Boolean(metric && metric.model),
                    trendClass,
                    detailLabel: this.buildMetricDetail(metric, currency),
                    formattedValue: this.formatMetricValue(
                        metric.value_type,
                        metric.value,
                        currency,
                        metric
                    ),
                };
            }),
        }));

        const topClients = (data.top_clients || []).map((item, index) => ({
            ...item,
            id: item.id || index,
            rank: index + 1,
            revenueLabel: this.formatCurrency(item.revenue || 0, currency),
        }));

        const recentActivity = (data.recent_activity || []).map((item, index) => ({
            ...item,
            id: item.id || `activity_${index}`,
            resId: item.res_id,
            dateLabel: this.formatDateTime(item.datetime),
            subtitle: item.subtitle || "",
            client: item.client || "",
            department: item.department || "",
        }));

        const alerts = (data.alerts || []).map((item, index) => ({
            ...item,
            id: item.key || `alert_${index}`,
            valueLabel: this.formatCompact(item.value || 0),
            severityClass: this.getAlertClass(item.severity),
            actionable: Boolean(item && item.model),
        }));

        const incomeVsExpenses = data.income_vs_expenses || {};
        const income = Number(incomeVsExpenses.income || 0);
        const expenses = Number(incomeVsExpenses.expenses || 0);
        const balance = Number(incomeVsExpenses.balance || 0);

        const dateRange = data.date_range || {};
        const quickStats = this.buildQuickStats(kpiGroups);
        const charts = this.buildCharts(data.charts || {}, currency);

        return {
            userName: data.user_name || "",
            userEmail: data.user_email || "",
            companyName: data.company_name || "",
            currency,
            dateRange: {
                start: dateRange.start || this.state.rangeStart,
                end: dateRange.end || this.state.rangeEnd,
            },
            quickStats,
            charts,
            kpiGroups,
            topClients,
            recentActivity,
            alerts,
            incomeVsExpenses: {
                income,
                expenses,
                balance,
                incomeLabel: this.formatCurrency(income, currency),
                expensesLabel: this.formatCurrency(expenses, currency),
                balanceLabel: this.formatCurrency(balance, currency),
            },
        };
    }

    buildQuickStats(kpiGroups) {
        const metricIndex = new Map();
        for (const group of kpiGroups || []) {
            for (const metric of group.metrics || []) {
                if (metric && metric.key) {
                    metricIndex.set(metric.key, metric);
                }
            }
        }

        const pickMetric = (...keys) => {
            for (const key of keys) {
                if (metricIndex.has(key)) {
                    return metricIndex.get(key);
                }
            }
            return null;
        };

        const statBlueprints = [
            {
                key: "total_leads",
                label: "Total Leads",
                note: "Leads in selected range",
                accent: "leads",
                metric: pickMetric("new_leads", "pipeline_volume"),
            },
            {
                key: "total_sales",
                label: "Total Sales",
                note: "Revenue in selected range",
                accent: "sales",
                metric: pickMetric("range_invoicing", "monthly_invoicing", "total_income"),
            },
            {
                key: "total_invoices",
                label: "Total Invoices",
                note: "Issued invoice volume",
                accent: "invoices",
                metric: pickMetric("issued_invoices", "paid_invoices"),
            },
            {
                key: "total_won",
                label: "Total Won",
                note: "Closed sales outcomes",
                accent: "won",
                metric: pickMetric("closed_sales", "signed_clients", "signed_paid_clients"),
            },
        ];

        const sparklineByAccent = {
            leads: {
                path: "0,20 20,20 38,20 56,20 70,20 80,20 88,16 93,10 100,2",
                color: "#1f8ed9",
            },
            sales: {
                path: "0,20 22,20 40,20 56,19 68,17 78,15 86,12 94,7 100,2",
                color: "#875a7b",
            },
            invoices: {
                path: "0,20 26,20 44,20 62,20 74,20 84,18 90,13 96,7 100,3",
                color: "#f0ad4e",
            },
            won: {
                path: "0,20 18,20 36,20 54,20 68,20 80,19 88,15 95,9 100,2",
                color: "#198754",
            },
        };

        return statBlueprints
            .filter((item) => Boolean(item.metric))
            .map((item) => ({
                key: item.key,
                label: item.label,
                note: item.note,
                accent: item.accent,
                valueLabel: item.metric ? item.metric.formattedValue || "0" : "0",
                actionable: Boolean(item.metric && item.metric.model),
                metric: item.metric,
                sparklinePath: (sparklineByAccent[item.accent] || {}).path || "",
                sparklineColor: (sparklineByAccent[item.accent] || {}).color || "#112249",
            }));
    }

    buildCharts(rawCharts, currency) {
        const salesHistory = (rawCharts && rawCharts.sales_history) || [];
        const rawPoints = salesHistory.map((point, index) => ({
            id: index,
            label: point.label || "",
            value: Number(point.value || 0),
        }));

        const points = rawPoints.length
            ? rawPoints
            : [
                  { id: 0, label: "Jan", value: 0 },
                  { id: 1, label: "Feb", value: 0 },
                  { id: 2, label: "Mar", value: 0 },
                  { id: 3, label: "Apr", value: 0 },
                  { id: 4, label: "May", value: 0 },
                  { id: 5, label: "Jun", value: 0 },
              ];

        const maxValue = Math.max(...points.map((point) => point.value), 0);
        const safeMax = maxValue > 0 ? maxValue : 1;
        const chartTop = 8;
        const chartBottom = 92;
        const chartHeight = chartBottom - chartTop;

        const normalizedPoints = points.map((point, index, list) => {
            const x = list.length === 1 ? 50 : (index / (list.length - 1)) * 100;
            const y = chartBottom - (point.value / safeMax) * chartHeight;
            return {
                ...point,
                x: Number(x.toFixed(2)),
                y: Number(y.toFixed(2)),
                valueLabel: this.formatCompactCurrency(point.value, currency),
            };
        });

        const polyline = normalizedPoints.map((point) => `${point.x},${point.y}`).join(" ");
        const peakPoint = normalizedPoints.reduce(
            (best, point) => (point.value > best.value ? point : best),
            normalizedPoints[0] || { value: 0, label: "", valueLabel: "0" }
        );

        const leadsVsWon = (rawCharts && rawCharts.leads_vs_won) || {};
        const totalLeads = Number(leadsVsWon.total_leads || 0);
        const totalWon = Number(leadsVsWon.total_won || 0);
        const wonRatio = totalLeads ? Math.min(Math.max(totalWon / totalLeads, 0), 1) : 0;

        return {
            sales: {
                points: normalizedPoints,
                polyline,
                maxLabel: this.formatCompactCurrency(maxValue, currency),
                midLabel: this.formatCompactCurrency(maxValue / 2, currency),
                peakValueLabel: peakPoint.valueLabel || "0",
                peakLabel: peakPoint.label || "",
            },
            leadsVsWon: {
                totalLeads,
                totalWon,
                wonRatio,
                wonRateLabel: `${Math.round(wonRatio * 100)}%`,
            },
        };
    }

    escapeCsvCell(value) {
        const text = `${value ?? ""}`;
        if (text.includes(",") || text.includes('"') || text.includes("\n")) {
            return `"${text.replace(/"/g, '""')}"`;
        }
        return text;
    }

    escapeXml(value) {
        return `${value ?? ""}`
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&apos;");
    }

    getExportFileName(extension) {
        const start = this.state.rangeStart || "start";
        const end = this.state.rangeEnd || "end";
        const dateStamp = this.toDateInputValue(new Date());
        return `dashboard_${start}_${end}_${dateStamp}.${extension}`.replace(/[^\w.-]/g, "_");
    }

    downloadBlob(content, mimeType, fileName) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    escapeHtml(value) {
        return `${value ?? ""}`
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    buildPdfHtml() {
        const data = this.state.data || {};
        const groupTables = (data.kpiGroups || [])
            .map(
                (group) => `
                    <section class="pdf_section">
                        <h2>${this.escapeHtml(group.title || group.key || "KPIs")}</h2>
                        <table>
                            <thead>
                                <tr><th>Metric</th><th>Value</th></tr>
                            </thead>
                            <tbody>
                                ${(group.metrics || [])
                                    .map(
                                        (metric) => `
                                            <tr>
                                                <td>${this.escapeHtml(metric.label || "-")}</td>
                                                <td>${this.escapeHtml(metric.formattedValue || "0")}</td>
                                            </tr>
                                        `
                                    )
                                    .join("")}
                            </tbody>
                        </table>
                    </section>
                `
            )
            .join("");

        const topClientsRows = (data.topClients || [])
            .map(
                (client) => `
                    <tr>
                        <td>${this.escapeHtml(client.rank || "-")}</td>
                        <td>${this.escapeHtml(client.name || "-")}</td>
                        <td>${this.escapeHtml(client.revenueLabel || "0")}</td>
                    </tr>
                `
            )
            .join("");

        const alertsRows = (data.alerts || [])
            .map(
                (alert) => `
                    <tr>
                        <td>${this.escapeHtml(alert.label || "-")}</td>
                        <td>${this.escapeHtml(alert.valueLabel || "0")}</td>
                        <td>${this.escapeHtml((alert.severity || "info").toUpperCase())}</td>
                        <td>${this.escapeHtml(alert.note || "")}</td>
                    </tr>
                `
            )
            .join("");

        const topClientsSection = topClientsRows
            ? `
                <section class="pdf_section">
                    <h2>Top Clients</h2>
                    <table>
                        <thead>
                            <tr><th>#</th><th>Client</th><th>Revenue</th></tr>
                        </thead>
                        <tbody>${topClientsRows}</tbody>
                    </table>
                </section>
            `
            : "";

        const alertsSection = alertsRows
            ? `
                <section class="pdf_section">
                    <h2>Alerts</h2>
                    <table>
                        <thead>
                            <tr><th>Alert</th><th>Value</th><th>Severity</th><th>Note</th></tr>
                        </thead>
                        <tbody>${alertsRows}</tbody>
                    </table>
                </section>
            `
            : "";

        return `
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="utf-8"/>
                    <title>Dashboard Report</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            color: #0f172a;
                            margin: 22px;
                            font-size: 12px;
                        }
                        h1 {
                            margin: 0;
                            font-size: 26px;
                            text-align: center;
                        }
                        .pdf_header {
                            margin-bottom: 16px;
                        }
                        .pdf_date_range {
                            margin-top: 4px;
                            color: #334155;
                            text-align: center;
                            font-size: 13px;
                            font-weight: 600;
                        }
                        .pdf_section {
                            margin-bottom: 16px;
                        }
                        .pdf_section h2 {
                            margin: 0 0 6px;
                            font-size: 15px;
                        }
                        table {
                            width: 100%;
                            border-collapse: collapse;
                            margin-top: 4px;
                        }
                        th,
                        td {
                            border: 1px solid #cbd5e1;
                            padding: 6px 8px;
                            text-align: left;
                            vertical-align: top;
                        }
                        th {
                            background: #f1f5f9;
                            font-weight: 600;
                        }
                    </style>
                </head>
                <body>
                    <div class="pdf_header">
                        <h1>Dashboard</h1>
                        <div class="pdf_date_range">
                            Date Range: ${this.escapeHtml(this.state.rangeStart || "-")} to ${this.escapeHtml(this.state.rangeEnd || "-")}
                        </div>
                    </div>
                    ${groupTables}
                    ${topClientsSection}
                    ${alertsSection}
                </body>
            </html>
        `;
    }

    buildExcelXml() {
        const data = this.state.data || {};

        const buildCell = (value, style = "sCell", type = "String", mergeAcross = 0) => {
            const mergeAttr = mergeAcross ? ` ss:MergeAcross="${mergeAcross}"` : "";
            return `<Cell ss:StyleID="${style}"${mergeAttr}><Data ss:Type="${type}">${this.escapeXml(
                value
            )}</Data></Cell>`;
        };

        const buildRow = (cells) => `<Row>${cells.join("")}</Row>`;

        const rows = [];
        rows.push(buildRow([buildCell("Dashboard", "sTitle", "String", 3)]));
        rows.push(
            buildRow([
                buildCell(
                    `Date Range: ${this.state.rangeStart || "-"} to ${this.state.rangeEnd || "-"}`,
                    "sSubTitle",
                    "String",
                    3
                ),
            ])
        );
        rows.push(buildRow([buildCell("", "sSpacer", "String", 3)]));

        for (const group of data.kpiGroups || []) {
            rows.push(
                buildRow([
                    buildCell(group.title || group.key || "KPIs", "sSection", "String", 3),
                ])
            );
            rows.push(
                buildRow([
                    buildCell("Metric", "sHeader"),
                    buildCell("Value", "sHeader"),
                    buildCell("Type", "sHeader"),
                    buildCell("Description", "sHeader"),
                ])
            );

            for (const metric of group.metrics || []) {
                rows.push(
                    buildRow([
                        buildCell(metric.label || "-", "sCell"),
                        buildCell(metric.formattedValue || "0", "sValue"),
                        buildCell((metric.value_type || "value").toUpperCase(), "sCellCenter"),
                        buildCell(group.description || "-", "sCell"),
                    ])
                );
            }
            rows.push(buildRow([buildCell("", "sSpacer", "String", 3)]));
        }

        if ((data.topClients || []).length) {
            rows.push(buildRow([buildCell("Top Clients Ranking", "sSection", "String", 3)]));
            rows.push(
                buildRow([
                    buildCell("Rank", "sHeader"),
                    buildCell("Client", "sHeader"),
                    buildCell("Revenue", "sHeader"),
                    buildCell("", "sHeader"),
                ])
            );
            for (const client of data.topClients) {
                rows.push(
                    buildRow([
                        buildCell(client.rank || "-", "sCellCenter"),
                        buildCell(client.name || "-", "sCell"),
                        buildCell(client.revenueLabel || "0", "sValue"),
                        buildCell("", "sCell"),
                    ])
                );
            }
            rows.push(buildRow([buildCell("", "sSpacer", "String", 3)]));
        }

        if (data.incomeVsExpenses) {
            rows.push(buildRow([buildCell("Income vs Expenses", "sSection", "String", 3)]));
            rows.push(
                buildRow([
                    buildCell("Income", "sHeader"),
                    buildCell("Expenses", "sHeader"),
                    buildCell("Balance", "sHeader"),
                    buildCell("", "sHeader"),
                ])
            );
            rows.push(
                buildRow([
                    buildCell(data.incomeVsExpenses.incomeLabel || "0", "sValue"),
                    buildCell(data.incomeVsExpenses.expensesLabel || "0", "sValue"),
                    buildCell(data.incomeVsExpenses.balanceLabel || "0", "sValue"),
                    buildCell("", "sCell"),
                ])
            );
            rows.push(buildRow([buildCell("", "sSpacer", "String", 3)]));
        }

        if ((data.alerts || []).length) {
            rows.push(buildRow([buildCell("Alerts", "sSection", "String", 3)]));
            rows.push(
                buildRow([
                    buildCell("Alert", "sHeader"),
                    buildCell("Value", "sHeader"),
                    buildCell("Severity", "sHeader"),
                    buildCell("Note", "sHeader"),
                ])
            );
            for (const alert of data.alerts) {
                const severity = (alert.severity || "info").toUpperCase();
                rows.push(
                    buildRow([
                        buildCell(alert.label || "-", "sCell"),
                        buildCell(alert.valueLabel || "0", "sValue"),
                        buildCell(severity, "sCellCenter"),
                        buildCell(alert.note || "-", "sCellWrap"),
                    ])
                );
            }
        }

        return `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
    xmlns:o="urn:schemas-microsoft-com:office:office"
    xmlns:x="urn:schemas-microsoft-com:office:excel"
    xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
    xmlns:html="http://www.w3.org/TR/REC-html40">
    <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
        <Title>Dashboard Report</Title>
    </DocumentProperties>
    <Styles>
        <Style ss:ID="Default" ss:Name="Normal">
            <Alignment ss:Vertical="Center"/>
            <Font ss:FontName="Calibri" ss:Size="11" ss:Color="#0F172A"/>
        </Style>
        <Style ss:ID="sTitle">
            <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
            <Font ss:FontName="Calibri" ss:Bold="1" ss:Size="18" ss:Color="#FFFFFF"/>
            <Interior ss:Color="#0B356F" ss:Pattern="Solid"/>
        </Style>
        <Style ss:ID="sSubTitle">
            <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
            <Font ss:FontName="Calibri" ss:Bold="1" ss:Size="12" ss:Color="#0B356F"/>
            <Interior ss:Color="#DCEBFF" ss:Pattern="Solid"/>
        </Style>
        <Style ss:ID="sSection">
            <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
            <Font ss:FontName="Calibri" ss:Bold="1" ss:Size="12" ss:Color="#FFFFFF"/>
            <Interior ss:Color="#124C96" ss:Pattern="Solid"/>
        </Style>
        <Style ss:ID="sHeader">
            <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
            <Font ss:FontName="Calibri" ss:Bold="1" ss:Size="11" ss:Color="#0B356F"/>
            <Interior ss:Color="#E6F0FF" ss:Pattern="Solid"/>
            <Borders>
                <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#9FB7DA"/>
                <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#9FB7DA"/>
                <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#9FB7DA"/>
                <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#9FB7DA"/>
            </Borders>
        </Style>
        <Style ss:ID="sCell">
            <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
            <Borders>
                <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#C6D7EE"/>
                <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#C6D7EE"/>
                <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#C6D7EE"/>
                <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#C6D7EE"/>
            </Borders>
        </Style>
        <Style ss:ID="sCellCenter" ss:Parent="sCell">
            <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
        </Style>
        <Style ss:ID="sValue" ss:Parent="sCell">
            <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
            <Font ss:FontName="Calibri" ss:Bold="1" ss:Size="11" ss:Color="#0A3B76"/>
        </Style>
        <Style ss:ID="sCellWrap" ss:Parent="sCell">
            <Alignment ss:Horizontal="Left" ss:Vertical="Top" ss:WrapText="1"/>
        </Style>
        <Style ss:ID="sSpacer">
            <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
        </Style>
    </Styles>
    <Worksheet ss:Name="Dashboard Report">
        <Table>
            <Column ss:Width="280"/>
            <Column ss:Width="150"/>
            <Column ss:Width="120"/>
            <Column ss:Width="460"/>
            ${rows.join("")}
        </Table>
        <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
            <FreezePanes/>
            <FrozenNoSplit/>
            <SplitHorizontal>3</SplitHorizontal>
            <TopRowBottomPane>3</TopRowBottomPane>
            <ActivePane>2</ActivePane>
        </WorksheetOptions>
    </Worksheet>
</Workbook>`;
    }

    getAlertClass(severity) {
        if (severity === "high") {
            return "high";
        }
        if (severity === "medium") {
            return "medium";
        }
        return "info";
    }

    normalizeCurrency(currency) {
        const safe = currency || {};
        return {
            symbol: safe.symbol || "",
            position: safe.position === "after" ? "after" : "before",
        };
    }

    formatMetricValue(valueType, value, currency, metric = null) {
        if (valueType === "currency") {
            return this.formatCompactCurrency(value, currency);
        }
        if (valueType === "percent") {
            if (value === null || value === undefined || value === "") {
                return "N/A";
            }
            const num = Number(value || 0);
            if (Number.isNaN(num)) {
                return "N/A";
            }
            const formatted = num.toLocaleString(undefined, {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2,
            });
            const showSign = Boolean(metric && metric.key === "monthly_growth" && num > 0);
            const signPrefix = showSign ? "+" : "";
            return `${signPrefix}${formatted}%`;
        }
        return this.formatCompact(value || 0);
    }

    resolveMetricTrend(metric) {
        const trend = ((metric && metric.trend) || "").toLowerCase();
        if (trend === "up" || trend === "down" || trend === "flat") {
            return trend;
        }
        if (metric && metric.key === "monthly_growth") {
            const value = Number(metric.value || 0);
            if (value > 0) {
                return "up";
            }
            if (value < 0) {
                return "down";
            }
            return "flat";
        }
        return "";
    }

    buildMetricDetail(metric, currency) {
        if (!metric || metric.key !== "monthly_growth") {
            return "";
        }
        const meta = metric.meta || {};
        const periodLabel = meta.comparison_label || "vs previous month";
        const current = Number(meta.current_value || 0);
        const previous = Number(meta.previous_value || 0);
        const delta = current - previous;
        const baselineMissing = Boolean(meta.baseline_missing);

        if (baselineMissing) {
            if (current > 0) {
                return `${periodLabel}: current ${this.formatCurrency(
                    current,
                    currency
                )} vs previous ${this.formatCurrency(
                    previous,
                    currency
                )} (new growth)`;
            }
            if (current < 0) {
                return `${periodLabel}: current ${this.formatCurrency(
                    current,
                    currency
                )} vs previous ${this.formatCurrency(previous, currency)}`;
            }
            return `${periodLabel}: no revenue in both periods`;
        }

        if (delta > 0) {
            return `${periodLabel}: up ${this.formatCurrency(
                Math.abs(delta),
                currency
            )} (current ${this.formatCurrency(current, currency)} vs previous ${this.formatCurrency(previous, currency)})`;
        }
        if (delta < 0) {
            return `${periodLabel}: down ${this.formatCurrency(
                Math.abs(delta),
                currency
            )} (current ${this.formatCurrency(current, currency)} vs previous ${this.formatCurrency(previous, currency)})`;
        }
        return `${periodLabel}: no change (current ${this.formatCurrency(
            current,
            currency
        )} = previous ${this.formatCurrency(previous, currency)})`;
    }

    formatCompactCurrency(value, currency) {
        return this.applyCurrencySymbol(this.formatCompact(value), currency);
    }

    formatCurrency(value, currency = null) {
        const amount = Number(value) || 0;
        const formatted = amount.toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
        return this.applyCurrencySymbol(formatted, currency);
    }

    applyCurrencySymbol(amountLabel, currency) {
        const symbol = (currency && currency.symbol) || "";
        const label = amountLabel || "0";
        if (!symbol) {
            return label;
        }
        const needsSpace = /[A-Za-z0-9]/.test(symbol);
        if ((currency && currency.position) === "after") {
            return needsSpace ? `${label} ${symbol}` : `${label}${symbol}`;
        }
        return needsSpace ? `${symbol} ${label}` : `${symbol}${label}`;
    }

    formatCompact(value) {
        const num = Number(value) || 0;
        const absValue = Math.abs(num);
        if (absValue >= 1000000) {
            const scaled = num / 1000000;
            return absValue >= 10000000
                ? `${Math.round(scaled)}m`
                : `${scaled.toFixed(1).replace(/\.0$/, "")}m`;
        }
        if (absValue >= 1000) {
            const scaled = num / 1000;
            if (absValue >= 10000) {
                return `${Math.round(scaled)}k`;
            }
            return `${scaled.toFixed(1).replace(/\.0$/, "")}k`;
        }
        if (absValue >= 100) {
            return `${Math.round(num)}`;
        }
        return `${num.toFixed(1).replace(/\.0$/, "")}`;
    }

    formatDateTime(value) {
        if (!value) {
            return "-";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleString(undefined, {
            year: "numeric",
            month: "short",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    getTodayDate() {
        const now = new Date();
        return this.toDateInputValue(now);
    }

    getMonthStartDate() {
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        return this.toDateInputValue(start);
    }

    toDateInputValue(value) {
        const year = value.getFullYear();
        const month = String(value.getMonth() + 1).padStart(2, "0");
        const day = String(value.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    getDashboardTitle() {
        const company = (this.state.data.companyName || "").trim();
        if (!company) {
            return "Business Dashboard";
        }
        return `${company} Dashboard`;
    }

    getRangeSummary() {
        const start = this.state.rangeStart || "-";
        const end = this.state.rangeEnd || "-";
        return `Performance snapshot from ${start} to ${end}`;
    }

    getUserInitials() {
        const source = (this.state.data.userName || "").trim();
        if (!source) {
            return "DB";
        }
        const letters = source
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part[0].toUpperCase())
            .join("");
        return letters || "DB";
    }
}

Dashboard.template = "dashboard.DashboardTemplate";
Dashboard.props = { ...standardActionServiceProps };

registry.category("actions").add("dashboard.client_action", Dashboard);
