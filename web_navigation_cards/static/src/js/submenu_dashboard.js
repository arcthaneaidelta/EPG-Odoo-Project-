/** @odoo-module **/
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

// 🗂️ Keys are xmlids — unique and stable, no path collision possible
const MENU_ICONS = {
	//Contacts
	"contacts.menu_partner_category_form": "/web_navigation_cards/static/src/img/icons/Contacts/etiquetas_contacto.svg",
	"contacts.menu_country_group": "/web_navigation_cards/static/src/img/icons/Contacts/grupo_paises.svg",
	"contacts.menu_country_partner": "/web_navigation_cards/static/src/img/icons/Contacts/paises.svg",
	"contacts.menu_country_state_partner": "/web_navigation_cards/static/src/img/icons/Contacts/provincias.svg",
	"contacts.res_partner_industry_menu": "/web_navigation_cards/static/src/img/icons/Contacts/sectores.svg",
	"contacts.menu_partner_title_contact": "/web_navigation_cards/static/src/img/icons/Contacts/titulos_contacto.svg",

	// Sales
	"sale.menu_sale_order": "/web_navigation_cards/static/src/img/icons/Sales/pedidos.svg",
	"sale.menu_sale_order_invoice": "/web_navigation_cards/static/src/img/icons/Sales/pedidos_a_facturar.svg",
	"sale.sales_team_config": "/web_navigation_cards/static/src/img/icons/Sales/equipos_de_ventas.svg",
	"sale.sale_menu_config_activity_plan": "/web_navigation_cards/static/src/img/icons/Sales/planes_de_actividad.svg",
	"sale.menu_product_template_action": "/web_navigation_cards/static/src/img/icons/Sales/productos.svg",
	"sale.menu_product_categories": "/web_navigation_cards/static/src/img/icons/Sales/categorías de producto.svg",
	"sale.menu_product_tags": "/web_navigation_cards/static/src/img/icons/Sales/etiquetas de producto.svg",
	"sale.menu_reporting_sales": "/web_navigation_cards/static/src/img/icons/Sales/ventas.svg",
	"sale.menu_reporting_salespeople": "/web_navigation_cards/static/src/img/icons/Sales/comerciales.svg",
	"sale.menu_reporting_customer": "/web_navigation_cards/static/src/img/icons/Sales/clientes.svg",
	"sale.menu_reporting_product": "/web_navigation_cards/static/src/img/icons/Sales/reportsproductos.svg",

	//CRM Pipeline
	"crm.crm_menu_forecast": "/web_navigation_cards/static/src/img/icons/CRM/pronostico.svg",
	"crm.crm_opportunity_report_menu": "/web_navigation_cards/static/src/img/icons/CRM/flujo.svg",
	"crm.crm_opportunity_report_menu_lead": "/web_navigation_cards/static/src/img/icons/CRM/leads.svg",
	"crm.crm_activity_report_menu": "/web_navigation_cards/static/src/img/icons/CRM/actividades.svg",
	"crm.res_partner_menu_customer": "/web_navigation_cards/static/src/img/icons/CRM/clientes.svg",
	"crm.crm_lead_menu_my_activities": "/web_navigation_cards/static/src/img/icons/CRM/mis_actividades.svg",
	"crm.menu_crm_opportunities": "/web_navigation_cards/static/src/img/icons/CRM/mi_flujo.svg",
	"crm.sales_team_menu_team_pipeline": "/web_navigation_cards/static/src/img/icons/CRM/equipos.svg",
	"sale_crm.sale_order_menu_quotations_crm": "/web_navigation_cards/static/src/img/icons/CRM/mis_presupuestos.svg",
	"crm.crm_config_settings_menu": "/web_navigation_cards/static/src/img/icons/CRM/ajustes.svg",
	"crm.crm_team_config": "/web_navigation_cards/static/src/img/icons/CRM/equipos_ventas.svg",

	//Accounting/Assets
	"account_asset_management.account_asset_menu": "/web_navigation_cards/static/src/img/icons/Accounting/ACTIVOS/activos.svg",
	"om_account_asset.menu_action_account_asset_asset_list_normal_purchase": "/web_navigation_cards/static/src/img/icons/Accounting/ACTIVOS/asset_category.svg",
	"account_asset_management.wiz_account_asset_report_menu": "/web_navigation_cards/static/src/img/icons/Accounting/ACTIVOS/calcular_amortizaciones.svg",
	"account_asset_management.account_asset_group_menu": "/web_navigation_cards/static/src/img/icons/Accounting/ACTIVOS/grupos_activo.svg",

	//Accounting/Budgets
	"om_account_budget.menu_budget_post_form": "/web_navigation_cards/static/src/img/icons/Accounting/ANALYTICS AND BUDGET/budgetary_positions.svg",
	"om_account_budget.menu_act_crossovered_budget_view": "/web_navigation_cards/static/src/img/icons/Accounting/ANALYTICS AND BUDGET/budgets.svg",
	"account.account_analytic_def_account": "/web_navigation_cards/static/src/img/icons/Accounting/ANALYTICS AND BUDGET/cuentas_analiticas.svg",
	"hr_expense.menu_hr_expense_my_expenses_all": "/web_navigation_cards/static/src/img/icons/Accounting/ANALYTICS AND BUDGET/mis_gastos.svg",
	"account.menu_analytic__distribution_model": "/web_navigation_cards/static/src/img/icons/Accounting/ANALYTICS AND BUDGET/modelos_distribucion_analitica.svg",
	"account.account_analytic_plan_menu": "/web_navigation_cards/static/src/img/icons/Accounting/ANALYTICS AND BUDGET/planes_analiticos.svg",

	//Accounting/Invoices
	"account.menu_action_account_invoice_report_all": "/web_navigation_cards/static/src/img/icons/Accounting/CLIENTES/analisis de facturas.svg",
	"account.menu_action_move_out_invoice_type": "/web_navigation_cards/static/src/img/icons/Accounting/CLIENTES/facturas de clientes.svg",
	"account.menu_action_move_in_invoice_type": "/web_navigation_cards/static/src/img/icons/Accounting/CLIENTES/facturas de proveedores.svg",
	"account.menu_action_move_out_refund_type": "/web_navigation_cards/static/src/img/icons/Accounting/CLIENTES/facturas rectificativas.svg",
	"account.menu_action_move_in_refund_type": "/web_navigation_cards/static/src/img/icons/Accounting/CLIENTES/reembolsos.svg",

	//Accounting/Accounting
	"om_account_accountant.menu_account_group": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/account_groups.svg",
	"account.menu_action_analytic_lines_tree": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/apuntes_analiticos.svg",
	"account.menu_action_account_moves_all": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/apuntes_contables.svg",
	"account.menu_action_move_journal_line_form": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/asientos_contables.svg",
	"accounting_pdf_reports.menu_print_journal": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/auditoria_libros.svg",
	"accounting_pdf_reports.menu_general_balance_report": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/balance_comprobacion.svg",
	"accounting_pdf_reports.menu_action_account_moves_ledger_general": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/general_ledger.svg",
	"om_fiscal_year.menu_action_change_lock_date": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/lock_dates.svg",
	"account.menu_action_currency_form": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/monedas.svg",
	"accounting_pdf_reports.menu_action_account_moves_ledger_partner": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/partner_ledger.svg",
	"account.menu_action_account_form": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/plan_contable.svg",
	"accounting_pdf_reports.menu_account_reports": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/reportes_cuenta.svg",
	"account_reconcile_oca.account_account_reconcile_menu": "/web_navigation_cards/static/src/img/icons/Accounting/CONTABILIDAD/conciliar.svg",

	//Accounting/Taxes
	"l10n_es_edi_facturae.menu_l10n_es_edi_facturae_root_certificates": "/web_navigation_cards/static/src/img/icons/Accounting/TAXES/certificados.svg",
	"account.menu_action_tax_form": "/web_navigation_cards/static/src/img/icons/Accounting/TAXES/impuestos.svg",
	"account.menu_action_account_fiscal_position_form": "/web_navigation_cards/static/src/img/icons/Accounting/TAXES/posiciones_fiscales.svg",
	"accounting_pdf_reports.menu_account_report": "/web_navigation_cards/static/src/img/icons/Accounting/TAXES/reporte_impuestos.svg",

	//Accounting/Reports
	"accounting_pdf_reports.menu_partner_ledger": "/web_navigation_cards/static/src/img/icons/Accounting/INFORMES/activos_financieros.svg",
	"accounting_pdf_reports.menu_account_report_pl": "/web_navigation_cards/static/src/img/icons/Accounting/INFORMES/ganancia_perdida.svg",
	"accounting_pdf_reports.menu_account_report_bs": "/web_navigation_cards/static/src/img/icons/Accounting/INFORMES/hoja_balance.svg",
	"account.menu_action_analytic_reporting": "/web_navigation_cards/static/src/img/icons/Accounting/INFORMES/informe_analitico.svg",
	"accounting_pdf_reports.menu_general_ledger": "/web_navigation_cards/static/src/img/icons/Accounting/INFORMES/libro_mayor.svg",

	//Accounting/Banks and Payment
	"contacts.menu_action_res_bank_form": "/web_navigation_cards/static/src/img/icons/Accounting/PROVEEDORES/bancos.svg",
	"contacts.menu_action_res_partner_bank_form": "/web_navigation_cards/static/src/img/icons/Accounting/PROVEEDORES/cuentas bancarias.svg",
	"hr_expense.menu_hr_expense_account_employee_expenses": "/web_navigation_cards/static/src/img/icons/Accounting/PROVEEDORES/gastos_empleado.svg",
	"account_statement_import_file.account_statement_import_menu": "/web_navigation_cards/static/src/img/icons/Accounting/PROVEEDORES/importar_extracto.svg",
	"account_payment.payment_method_menu": "/web_navigation_cards/static/src/img/icons/Accounting/PROVEEDORES/metodos_pago.svg",
	"account.menu_action_account_payments_payable": "/web_navigation_cards/static/src/img/icons/Accounting/PROVEEDORES/pagos.svg",
	"account_payment.payment_provider_menu": "/web_navigation_cards/static/src/img/icons/Accounting/PROVEEDORES/proveedores de pago.svg",
	"account.action_account_reconcile_model_menu": "/web_navigation_cards/static/src/img/icons/Accounting/PROVEEDORES/modelos_conciliacion.svg",

	// Add more xmlids here...
};

export class SubmenuDashboard extends Component {
	static template = "web_navigation_cards.SubmenuDashboard";
	static props = ["*"];

	setup() {
		this.menuService = useService("menu");
		this.actionService = useService("action");

		const action = this.props.action || {};
		const context = action.context || {};
		const params = action.params || {};

		// BUG FIX: Look in action.active_menu_id, then params, then context
		this.parentMenuId = action.active_menu_id || params.active_menu_id || context.active_menu_id || null;
		this.submenus = [];

		onWillStart(async () => {
			let menuId = this.parentMenuId;
			
			// RESTORE LOGIC: If missing, try sessionStorage for this app
			if (!menuId) {
				const currentApp = this.menuService.getCurrentApp();
				if (currentApp) {
					const savedId = browser.sessionStorage.getItem(`last_submenu_id_${currentApp.id}`);
					if (savedId) {
						console.log("SubmenuDashboard: Restoring category from session storage:", savedId);
						menuId = parseInt(savedId);
						this.parentMenuId = menuId;
					} else {
						console.log("SubmenuDashboard: Falling back to app root:", currentApp.id);
						menuId = currentApp.id;
						this.parentMenuId = menuId;
					}
				}
			}

			if (menuId && this.menuService.getMenu(menuId)) {
				const menu = this.menuService.getMenu(menuId);
				if (menu.childrenTree) {
					this.submenus = menu.childrenTree;
				}
			} else if (this.parentMenuId) {
				console.warn("SubmenuDashboard: Menu not found in service:", menuId);
				await this.menuService.reload();
				const menu = this.menuService.getMenu(menuId);
				if (menu && menu.childrenTree) {
					this.submenus = menu.childrenTree;
				}
			}
			
			// Note: We avoid doAction redirects here to maintain router stability during popstate
		});
	}

	getMenuIcon(menuId) {
		const menu = this.menuService.getMenu(menuId);
		const xmlid = menu?.xmlid || null;
		console.log("xmlid:", xmlid); // 👈 Remove once all icons are mapped
		return (xmlid && MENU_ICONS[xmlid]) ? MENU_ICONS[xmlid] : null;
	}

	async onCardClick(menuId) {
		await this.menuService.selectMenu(menuId);
	}
}

registry.category("actions").add("submenu_dashboard_action", SubmenuDashboard);