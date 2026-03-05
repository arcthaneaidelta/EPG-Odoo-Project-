/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";

const DEFAULT_DATA = {
    userName: "",
    userEmail: "",
    companyName: "",
    currency: {
        symbol: "",
        position: "before",
    },
    kpis: [],
    salesChart: {
        labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
        values: [0, 0, 0, 0, 0, 0, 0],
        path: "",
        areaPath: "",
        markerX: 24,
        markerY: 120,
        markerLabel: "0",
        yTicks: [],
        xTicks: [],
        periodLabel: "",
        currentLabel: "",
    },
    wonTotal: 0,
    wonTotalLabel: "0 / 0",
    donutCenterLabel: "Won / Leads",
    wonDistribution: [],
    donutSegments: [],
    donutStyle: "",
    tableRows: [],
};

export class CrmDashboard extends Component {
    setup() {
        this.actionService = useService("action");
        this.periodInputRef = useRef("periodInput");
        this.state = useState({
            loading: true,
            search: "",
            periodMonth: this.getCurrentMonthValue(),
            requestToken: 0,
            donutHoverValue: "",
            data: { ...DEFAULT_DATA },
        });
        this.searchTimer = null;

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
        try {
            const data = await rpc("/crm_dashboard/data", {
                search: this.state.search,
                period_month: this.state.periodMonth,
            });
            if (token !== this.state.requestToken) {
                return;
            }
            const normalized = this.normalizeData(data || {});
            this.state.data = normalized;
            this.state.donutHoverValue = "";
            if (normalized.salesChart.selectedMonth) {
                this.state.periodMonth = normalized.salesChart.selectedMonth;
            }
        } finally {
            if (token === this.state.requestToken) {
                this.state.loading = false;
            }
        }
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value || "";
        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }
        this.searchTimer = setTimeout(() => this.loadDashboard(), 350);
    }

    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            if (this.searchTimer) {
                clearTimeout(this.searchTimer);
            }
            this.loadDashboard();
        }
    }

    onPeriodChange(ev) {
        const value = (ev.target.value || "").trim();
        this.state.periodMonth = value || this.getCurrentMonthValue();
        this.loadDashboard();
    }

    onPeriodPickerClick(ev) {
        ev.preventDefault();
        const input = this.periodInputRef?.el;
        if (!input) {
            return;
        }
        input.focus();
        if (typeof input.showPicker === "function") {
            input.showPicker();
        } else {
            input.click();
        }
    }

    onDonutItemEnter(item) {
        this.state.donutHoverValue = (item && item.formattedValue) || "";
    }

    onDonutItemLeave() {
        this.state.donutHoverValue = "";
    }

    onDonutMouseMove(ev) {
        const segments = this.state.data.donutSegments || [];
        if (!segments.length) {
            this.state.donutHoverValue = "";
            return;
        }

        const target = ev.currentTarget;
        if (!target) {
            return;
        }
        const rect = target.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const dx = ev.clientX - centerX;
        const dy = ev.clientY - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const outerRadius = Math.min(rect.width, rect.height) / 2;
        const innerRadius = Math.max(0, outerRadius - 26);

        if (distance < innerRadius || distance > outerRadius) {
            this.state.donutHoverValue = "";
            return;
        }

        const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
        const normalizedAngle = (angle + 90 + 360) % 360;
        const segment =
            segments.find(
                (item) =>
                    normalizedAngle >= item.startAngle &&
                    normalizedAngle < item.endAngle
            ) || null;
        this.state.donutHoverValue = segment ? segment.formattedValue : "";
    }

    onKpiClick(kpi) {
        const key = (kpi && kpi.key) || "";
        if (!key) {
            return;
        }
        if (key === "total_sales") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: kpi?.label || "Sales Orders",
                res_model: "sale.order",
                views: [
                    [false, "list"],
                    [false, "form"],
                    [false, "kanban"],
                    [false, "pivot"],
                    [false, "graph"],
                ],
                view_mode: "list,form,kanban,pivot,graph",
                target: "current",
                domain: this.getSalesDomain(),
            });
            return;
        }
        if (key === "total_invoices") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: kpi?.label || "Customer Invoices",
                res_model: "account.move",
                views: [
                    [false, "list"],
                    [false, "form"],
                    [false, "pivot"],
                    [false, "graph"],
                ],
                view_mode: "list,form,pivot,graph",
                target: "current",
                domain: this.getInvoiceDomain(),
            });
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: kpi?.label || "CRM Data",
            res_model: "crm.lead",
            views: [
                [false, "list"],
                [false, "form"],
                [false, "kanban"],
                [false, "pivot"],
                [false, "graph"],
            ],
            view_mode: "list,form,kanban,pivot,graph",
            target: "current",
            domain: this.getDomainForKpi(key),
        });
    }

    getDomainForKpi(key) {
        const searchDomain = this.getSearchDomain();
        const extraDomain = [];
        if (key === "total_won") {
            extraDomain.push(["type", "=", "opportunity"]);
            extraDomain.push(["stage_id.is_won", "=", true]);
        } else {
            extraDomain.push(["type", "in", ["lead", "opportunity"]]);
        }
        return [...searchDomain, ...extraDomain];
    }

    getSalesDomain() {
        const domain = [["state", "!=", "cancel"]];
        const term = (this.state.search || "").trim();
        if (!term) {
            return domain;
        }
        return [
            ...domain,
            "|",
            "|",
            "|",
            ["name", "ilike", term],
            ["partner_id.name", "ilike", term],
            ["client_order_ref", "ilike", term],
            ["origin", "ilike", term],
        ];
    }

    getInvoiceDomain() {
        const domain = [
            ["move_type", "=", "out_invoice"],
            ["state", "!=", "cancel"],
            ["invoice_line_ids.sale_line_ids", "!=", false],
        ];
        const term = (this.state.search || "").trim();
        if (!term) {
            return domain;
        }
        return [
            ...domain,
            "|",
            "|",
            "|",
            ["name", "ilike", term],
            ["partner_id.name", "ilike", term],
            ["invoice_origin", "ilike", term],
            ["ref", "ilike", term],
        ];
    }

    getSearchDomain() {
        const term = (this.state.search || "").trim();
        if (!term) {
            return [];
        }
        return [
            "|",
            "|",
            "|",
            ["name", "ilike", term],
            ["partner_name", "ilike", term],
            ["contact_name", "ilike", term],
            ["email_from", "ilike", term],
        ];
    }

    getCurrentMonthValue() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        return `${year}-${month}`;
    }

    normalizeData(data) {
        const currency = this.normalizeCurrency(data.currency);
        const kpis = (data.kpis || []).map((item, idx) => {
            const safeItem = item || {};
            return {
                ...safeItem,
                id: safeItem.key || `kpi_${idx}`,
                formattedValue: this.formatKpiValue(
                    safeItem.key,
                    safeItem.value || 0,
                    currency
                ),
                ...this.computeTrendInfo(safeItem.series || []),
                ...this.getToneColors(safeItem.tone || ""),
                ...this.buildGeometry(safeItem.series || [], {
                    left: 0,
                    right: 140,
                    top: 6,
                    bottom: 50,
                    smooth: true,
                }),
            };
        });

        const salesValues = (data.sales_chart && data.sales_chart.values) || [0, 0, 0, 0, 0, 0, 0];
        const salesLabels = (data.sales_chart && data.sales_chart.labels) || ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
        const salesGeometry = this.buildGeometry(salesValues, {
            left: 12,
            right: 590,
            top: 24,
            bottom: 232,
            smooth: true,
        });

        const markerIndex = salesGeometry.points.length ? salesGeometry.points.length - 1 : 0;
        const markerPoint = salesGeometry.points[markerIndex] || { x: 12, y: 120 };
        const markerValue = salesValues[markerIndex] || 0;

        const wonDistribution = (data.won_distribution || []).map((item, idx) => ({
            ...item,
            color: this.getPaletteColor(idx),
            formattedValue: this.formatCompact(item.value || 0),
        }));
        const donutSegments = this.buildDonutSegments(wonDistribution);

        const wonTotal = data.won_total || 0;
        const totalLeads = kpis.find((item) => item.key === "total_leads")?.value || 0;
        const tableRows = (data.table_rows || []).map((row, index) => ({
            id: `${row.name || "row"}_${index}`,
            name: row.name || "-",
            type: row.type || "-",
            stage: row.stage || "-",
            revenueLabel: this.formatCurrency(row.revenue || 0, currency),
            probabilityLabel: `${Math.round(row.probability || 0)}%`,
            createDateLabel: this.formatDate(row.create_date),
        }));
        return {
            userName: data.user_name || "",
            userEmail: data.user_email || "",
            companyName: data.company_name || "",
            currency,
            kpis,
            salesChart: {
                labels: salesLabels,
                values: salesValues,
                path: salesGeometry.linePath,
                areaPath: salesGeometry.areaPath,
                markerX: markerPoint.x,
                markerY: markerPoint.y,
                markerLabel: this.formatCompact(markerValue),
                yTicks: this.buildYAxisTicks(salesValues, 24, 232, 4),
                xTicks: salesGeometry.points.map((point, index) => ({
                    leftPercent: (point.x / 610) * 100,
                    label: salesLabels[index] || "",
                })),
                periodLabel: (data.sales_chart && data.sales_chart.period_label) || "",
                selectedMonth: (data.sales_chart && data.sales_chart.selected_month) || "",
                currentLabel: salesLabels[salesLabels.length - 1] || "",
            },
            wonTotal,
            wonTotalLabel: `${this.formatCompact(wonTotal)} / ${this.formatCompact(totalLeads)}`,
            donutCenterLabel: "Won / Leads",
            wonDistribution,
            donutSegments,
            donutStyle: this.buildDonutStyle(wonDistribution),
            tableRows,
        };
    }

    buildGeometry(values, config) {
        const list = values && values.length ? values : [0, 0];
        const { left, right, top, bottom, smooth } = config;
        const maxValue = Math.max(...list);
        const minValue = Math.min(...list);
        const span = maxValue - minValue;
        const step = list.length > 1 ? (right - left) / (list.length - 1) : 0;

        const points = list.map((value, index) => {
            const ratio = span === 0 ? 0.12 : (value - minValue) / span;
            const x = left + step * index;
            const y = bottom - ratio * (bottom - top);
            return { x, y };
        });

        const linePath = smooth
            ? this.buildSmoothPath(points)
            : this.buildStraightPath(points);
        const firstPoint = points[0] || { x: left, y: bottom };
        const lastPoint = points[points.length - 1] || { x: right, y: bottom };
        const areaPath = `${linePath} L ${lastPoint.x.toFixed(2)} ${bottom.toFixed(
            2
        )} L ${firstPoint.x.toFixed(2)} ${bottom.toFixed(2)} Z`;

        return {
            points,
            linePath,
            areaPath,
            sparkLinePath: linePath,
            sparkAreaPath: areaPath,
        };
    }

    buildStraightPath(points) {
        if (!points.length) {
            return "";
        }
        return points
            .map((point, index) =>
                `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`
            )
            .join(" ");
    }

    buildSmoothPath(points) {
        if (!points.length) {
            return "";
        }
        if (points.length === 1) {
            return `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
        }
        let path = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
        for (let index = 1; index < points.length - 1; index += 1) {
            const current = points[index];
            const next = points[index + 1];
            const midX = (current.x + next.x) / 2;
            const midY = (current.y + next.y) / 2;
            path += ` Q ${current.x.toFixed(2)} ${current.y.toFixed(
                2
            )} ${midX.toFixed(2)} ${midY.toFixed(2)}`;
        }
        const beforeLast = points[points.length - 2];
        const last = points[points.length - 1];
        path += ` Q ${beforeLast.x.toFixed(2)} ${beforeLast.y.toFixed(
            2
        )} ${last.x.toFixed(2)} ${last.y.toFixed(2)}`;
        return path;
    }

    buildYAxisTicks(values, top, bottom, count) {
        const list = values && values.length ? values : [0];
        const maxValue = Math.max(...list, 0);
        const step = this.getAxisStep(maxValue, count);
        const topValue = count > 1 ? step * (count - 1) : step;

        return Array.from({ length: count }).map((_, index) => {
            const ratio = count === 1 ? 0 : index / (count - 1);
            const value = topValue - step * index;
            const y = top + (bottom - top) * ratio;
            return {
                y,
                topPercent: (y / 260) * 100,
                label: this.formatAxis(value),
            };
        });
    }

    getAxisStep(maxValue, count) {
        const divisions = Math.max(1, (count || 2) - 1);
        if (maxValue <= 0) {
            return 1;
        }
        const rawStep = maxValue / divisions;
        const magnitude = 10 ** Math.floor(Math.log10(rawStep));
        const normalized = rawStep / magnitude;
        let niceNormalized = 10;
        if (normalized <= 1) {
            niceNormalized = 1;
        } else if (normalized <= 2) {
            niceNormalized = 2;
        } else if (normalized <= 5) {
            niceNormalized = 5;
        }
        return niceNormalized * magnitude;
    }

    normalizeCurrency(currency) {
        const safeCurrency = currency || {};
        return {
            symbol: safeCurrency.symbol || "",
            position: safeCurrency.position === "after" ? "after" : "before",
        };
    }

    isMonetaryKpi(kpiKey) {
        return kpiKey === "total_sales" || kpiKey === "total_invoices";
    }

    formatKpiValue(kpiKey, value, currency) {
        if (!this.isMonetaryKpi(kpiKey)) {
            return this.formatCompact(value);
        }
        return this.formatCompactCurrency(value, currency);
    }

    formatCompactCurrency(value, currency) {
        return this.applyCurrencySymbol(this.formatCompact(value), currency);
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
            if (absValue < 2000) {
                return `${scaled.toFixed(1)}k`;
            }
            return `${scaled.toFixed(1).replace(/\.0$/, "")}k`;
        }
        if (absValue >= 100) {
            return `${Math.round(num)}`;
        }
        return `${num.toFixed(1).replace(/\.0$/, "")}`;
    }

    formatAxis(value) {
        const absValue = Math.abs(value);
        if (absValue >= 1000000) {
            const scaled = value / 1000000;
            return `${scaled.toFixed(absValue >= 10000000 ? 0 : 1).replace(/\.0$/, "")}M`;
        }
        if (absValue >= 1000) {
            const scaled = value / 1000;
            return `${scaled.toFixed(absValue >= 10000 ? 0 : 1).replace(/\.0$/, "")}K`;
        }
        if (absValue >= 10) {
            return `${Math.round(value)}`;
        }
        if (absValue >= 1) {
            return `${value.toFixed(1).replace(/\.0$/, "")}`;
        }
        return `${value.toFixed(2).replace(/\.?0+$/, "")}`;
    }

    formatCurrency(value, currency = null) {
        const amount = Number(value) || 0;
        const formatted = amount.toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
        return this.applyCurrencySymbol(formatted, currency);
    }

    formatDate(value) {
        if (!value) {
            return "-";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "2-digit",
        });
    }

    computeTrendInfo(series) {
        if (!series || series.length < 2) {
            return {
                trendLabel: "",
                trendClass: "neutral",
            };
        }
        const current = Number(series[series.length - 1] || 0);
        const previous = Number(series[series.length - 2] || 0);
        if (!previous) {
            return {
                trendLabel: "",
                trendClass: "neutral",
            };
        }
        const percent = ((current - previous) / Math.abs(previous)) * 100.0;
        if (!Number.isFinite(percent)) {
            return {
                trendLabel: "",
                trendClass: "neutral",
            };
        }
        const trendClass =
            percent > 0 ? "positive" : percent < 0 ? "negative" : "neutral";
        const sign = percent > 0 ? "+" : "";
        return {
            trendLabel: `${sign}${percent.toFixed(2)}%`,
            trendClass,
        };
    }

    getToneColors(tone) {
        if (tone === "pink") {
            return {
                sparkLineColor: "#ff7f95",
                sparkAreaColor: "rgba(255, 127, 149, 0.30)",
            };
        }
        if (tone === "green") {
            return {
                sparkLineColor: "#28cb41",
                sparkAreaColor: "rgba(40, 203, 65, 0.28)",
            };
        }
        return {
            sparkLineColor: "#40d2ff",
            sparkAreaColor: "rgba(64, 210, 255, 0.30)",
        };
    }

    getPaletteColor(index) {
        const colors = ["#22e9f7", "#1ca9d4", "#226fc8", "#1f4ea7"];
        return colors[index % colors.length];
    }

    buildDonutStyle(distribution) {
        if (!distribution || !distribution.length) {
            return "background: conic-gradient(#1d64da 0deg 360deg);";
        }

        const total = distribution.reduce((acc, item) => acc + (item.value || 0), 0) || 1;
        let currentDegree = 0.0;
        const gap = 2.4;
        const stops = [];

        distribution.forEach((item, idx) => {
            const slice = ((item.value || 0) / total) * 360;
            const colorStart = currentDegree + gap / 2;
            const colorEnd = currentDegree + Math.max(gap / 2, slice - gap / 2);
            const color = this.getPaletteColor(idx);
            stops.push(`${color} ${colorStart.toFixed(2)}deg ${colorEnd.toFixed(2)}deg`);
            if (colorEnd < currentDegree + slice) {
                stops.push(
                    `rgba(15, 56, 122, 0.96) ${colorEnd.toFixed(2)}deg ${(currentDegree + slice).toFixed(2)}deg`
                );
            }
            currentDegree += slice;
        });

        if (currentDegree < 360) {
            stops.push(
                `rgba(15, 56, 122, 0.96) ${currentDegree.toFixed(2)}deg 360deg`
            );
        }

        return `background: conic-gradient(${stops.join(", ")});`;
    }

    buildDonutSegments(distribution) {
        if (!distribution || !distribution.length) {
            return [];
        }
        const total = distribution.reduce((acc, item) => acc + (item.value || 0), 0);
        if (!total) {
            return [];
        }
        let currentDegree = 0.0;
        return distribution
            .map((item) => {
                const slice = ((item.value || 0) / total) * 360;
                const segment = {
                    name: item.name || "",
                    formattedValue: item.formattedValue || this.formatCompact(item.value || 0),
                    startAngle: currentDegree,
                    endAngle: currentDegree + slice,
                };
                currentDegree += slice;
                return segment;
            })
            .filter((item) => item.endAngle > item.startAngle);
    }
}

CrmDashboard.template = "crm_dashboard.CrmDashboardTemplate";
CrmDashboard.props = { ...standardActionServiceProps };

registry.category("actions").add("crm_dashboard.client_action", CrmDashboard);
