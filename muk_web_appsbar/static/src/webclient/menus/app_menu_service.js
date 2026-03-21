import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { computeAppsAndMenuItems, reorderApps } from "@web/webclient/menus/menu_helpers";

export const appMenuService = {
    dependencies: ["menu"],
    async start(env, { menu }) {
        return {
            getCurrentApp() {
                return menu.getCurrentApp();
            },
            getAppsMenuItems() {
                const menuItems = computeAppsAndMenuItems(
                    menu.getMenuAsTree('root')
                );
                let apps = menuItems.apps;
                const menuConfig = JSON.parse(
                    user.settings?.homemenu_config || 'null'
                );
                if (menuConfig) {
                    reorderApps(apps, menuConfig);
                }

                // Placeholder apps
                const placeholderApps = [
                    {
                        id: 'placeholder_documents',
                        label: 'Documents',
                        xmlid: 'placeholder.documents',
                        webIconData: '/base/static/description/icon.png',
                        href: '#',
                        actionID: null,
                        isPlaceholder: true,
                        order: 5
                    },
                    {
                        id: 'placeholder_training',
                        label: 'Training',
                        xmlid: 'placeholder.training',
                        webIconData: '/base/static/description/icon.png',
                        href: '#',
                        actionID: null,
                        isPlaceholder: true,
                        order: 6
                    }
                ];

                // ✅ xmlid based order — never changes with language
                const customOrderByXmlId = {
                    'dashboard.menu_dashboard_custom': 0,
                    'crm.crm_menu_root': 1,
                    'contacts.menu_contacts': 2,
                    'sale.sale_menu_root': 3,
                    'account.menu_finance': 4,
                    'placeholder.documents': 5,
                    'placeholder.training': 6,
                    'ai_assistant.menu_ai_assistant_root': 7,
                    'website.menu_website_configuration': 9,
                    'base.menu_administration': 10,
                    'base.menu_management': 11,
                };

                // Assign order using xmlid only
                apps = apps.map(app => {
                    const appXmlId = app.xmlid || '';
                    let order = customOrderByXmlId[appXmlId];

                    if (order === undefined) {
                        order = 999;
                    }

                    return { ...app, order };
                });

                // Combine and sort
                apps = [...placeholderApps, ...apps];
                apps.sort((a, b) => a.order - b.order);

                return apps;
            },
            selectApp(app) {
                if (app.isPlaceholder) {
                    return;
                }
                menu.selectMenu(app);
            }
        };
    },
};

registry.category("services").add("app_menu", appMenuService);