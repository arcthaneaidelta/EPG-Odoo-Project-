/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class SubmenuDashboard extends Component {
    static template = "web_navigation_cards.SubmenuDashboard";
    static props = ["*"];

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        
        // Context safety
        const context = this.props.action.context || {};
        this.parentMenuId = context.active_menu_id || null;
        
        this.submenus = [];

        onWillStart(async () => {
            // Check if we have a valid menu ID
            if (this.parentMenuId && this.menuService.getMenu(this.parentMenuId)) {
                const menu = this.menuService.getMenu(this.parentMenuId);
                if (menu.childrenTree) {
                    this.submenus = menu.childrenTree;
                }
            } else {
                // FALLBACK LOGIC:
                // If no menu ID is found (e.g. on refresh), redirect to CRM Lead model.
                // We use the standard XML ID for the CRM Pipeline.
                console.log("No parent menu found, redirecting to CRM...");
                
                // 'crm.crm_lead_action_pipeline' is the standard action for "My Pipeline"
                // You can change this to 'crm.crm_lead_all_leads' if you want the list view of all leads.
                await this.actionService.doAction("crm.crm_lead_action_pipeline", {
                    clear_breadcrumbs: true, 
                });
            }
        });
    }

    async onCardClick(menuId) {
        await this.menuService.selectMenu(menuId);
    }
}

registry.category("actions").add("submenu_dashboard_action", SubmenuDashboard);