import { browser } from "@web/core/browser/browser";
import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.activeSection = null;
    },

    /**
     * Working of topbar
     * 1. If menu has no children -> Standard behavior (selectMenu).
     * 2. If menu has children -> Open our Card Dashboard.
     */
    async onSectionClick(section) {
        // Track the active section for highlight
        this.activeSection = section.id;
        this.render(true); // force re-render to apply active class

        // Check if the clicked section has children
        const menu = this.menuService.getMenu(section.id);
        
        if (menu.childrenTree && menu.childrenTree.length > 0) {
            // BUG FIX: Store the last used sub-menu for this APP to restore it on Back navigation
            const appId = menu.appID;
            browser.sessionStorage.setItem(`last_submenu_id_${appId}`, section.id);

            // It has submenus: Open the Dashboard
            await this.actionService.doAction({
                type: 'ir.actions.client',
                tag: 'submenu_dashboard_action', // This must match the registry key(submenu_dashboard.js file)
                name: menu.name,
                active_menu_id: section.id, // Top-level property
                params: {
                    active_menu_id: section.id, // For URL persistence
                },
                context: {
                    active_menu_id: section.id, // We need this ID to show the right cards
                },
                target: 'current',
            });
        } else {
            await this.menuService.selectMenu(section.id);
        }
    }
});