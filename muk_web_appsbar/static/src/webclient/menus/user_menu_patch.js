/** @odoo-module **/

import { registry } from "@web/core/registry";

const userMenuRegistry = registry.category("user_menuitems");

// Intercept future additions to ignore specific items
const originalAdd = userMenuRegistry.add.bind(userMenuRegistry);
userMenuRegistry.add = function (key, value, options) {
    if (['odoo_account', 'install_pwa', 'web_tour.tour_enabled', 'shortcuts', 'documentation', 'support'].includes(key)) {
        // Ignore these items
        return this;
    }
    return originalAdd(key, value, options);
};

// Remove them if they were already added before this script executes
userMenuRegistry.remove("odoo_account");
userMenuRegistry.remove("install_pwa");
userMenuRegistry.remove("web_tour.tour_enabled");
userMenuRegistry.remove("shortcuts");
userMenuRegistry.remove("documentation");
userMenuRegistry.remove("support");
