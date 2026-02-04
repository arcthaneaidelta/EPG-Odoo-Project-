import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

import { computeAppsAndMenuItems, reorderApps } from "@web/webclient/menus/menu_helpers";

export const appMenuService = {
    dependencies: ["menu"],
    async start(env, { menu }) {
        return {
        	getCurrentApp () {
        		return menu.getCurrentApp();
        	},
        	getAppsMenuItems() {
				const menuItems = computeAppsAndMenuItems(
					menu.getMenuAsTree('root')
				)
				let apps = menuItems.apps;
				const menuConfig = JSON.parse(
					user.settings?.homemenu_config || 'null'
				);
				if (menuConfig) {
                    reorderApps(apps, menuConfig);
				}
				
				// Add placeholder apps for Dashboard, Documents and Training
				const placeholderApps = [
					{
						id: 'placeholder_dashboard',
						label: 'Dashboard',
						xmlid: 'placeholder.dashboard',
						webIconData: '/base/static/description/icon.png', // You can replace with custom icon
						href: '#',
						actionID: null,
						isPlaceholder: true,
						order: 0
					},
					{
						id: 'placeholder_documents',
						label: 'Documents',
						xmlid: 'placeholder.documents',
						webIconData: '/base/static/description/icon.png', // You can replace with custom icon
						href: '#',
						actionID: null,
						isPlaceholder: true,
						order: 5
					},
					{
						id: 'placeholder_training',
						label: 'Training',
						xmlid: 'placeholder.training',
						webIconData: '/base/static/description/icon.png', // You can replace with custom icon
						href: '#',
						actionID: null,
						isPlaceholder: true,
						order: 6
					}
				];
				
				// Define custom order mapping
				const customOrder = {
					'placeholder_dashboard': 0,
					'Contacts': 1,
					'contacts': 1, // lowercase variant
					'CRM': 2,
					'crm': 2, // lowercase variant
					'Sales': 3,
					'sales': 3, // lowercase variant
					'Accounting': 4,
					'accounting': 4, // lowercase variant
					'Invoicing': 4, // Alternative name for accounting
					'invoicing': 4,
					'placeholder_documents': 5,
					'placeholder_training': 6,
					'AI Assistant': 7,
					'ai_assistant': 7, // lowercase variant
					'Website': 8,
					'website': 8, // lowercase variant
					'Settings': 9,
					'settings': 9, // lowercase variant
					'Apps': 10,
					'apps': 10 // lowercase variant
				};
				
				// Assign order to existing apps
				apps = apps.map(app => {
					const appLabel = app.label || '';
					const appXmlId = app.xmlid || '';
					
					// Try to find order by label or xmlid
					let order = customOrder[appLabel] ?? customOrder[appLabel.toLowerCase()];
					
					// If not found by label, try xmlid
					if (order === undefined) {
						const xmlIdParts = appXmlId.split('.');
						const lastPart = xmlIdParts[xmlIdParts.length - 1];
						order = customOrder[lastPart] ?? customOrder[lastPart.toLowerCase()];
					}
					
					// Default order if not found
					if (order === undefined) {
						order = 999;
					}
					
					return { ...app, order };
				});
				
				// Combine placeholder apps with real apps
				apps = [...placeholderApps, ...apps];
				
				// Sort by order
				apps.sort((a, b) => a.order - b.order);
				
        		return apps;
			},
			selectApp(app) {
				// Don't select placeholder apps
				if (app.isPlaceholder) {
					return;
				}
				menu.selectMenu(app);
			}
        };
    },
};

registry.category("services").add("app_menu", appMenuService);