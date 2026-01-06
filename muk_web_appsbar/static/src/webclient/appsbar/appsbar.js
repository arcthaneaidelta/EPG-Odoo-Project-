import { url } from '@web/core/utils/urls';
import { useService } from '@web/core/utils/hooks';

import { Component, onWillUnmount, useState, onMounted, onWillStart } from '@odoo/owl';

export class AppsBar extends Component {
    static template = 'muk_web_appsbar.AppsBar';
    static props = {};
    
    setup() {
        this.companyService = useService('company');
        this.appMenuService = useService('app_menu');
        this.menuService = useService('menu');
        
        // State to manage navigation
        this.state = useState({
            currentView: 'apps', // 'apps' or 'children'
            selectedApp: null,
            childrenMenus: [],
            expandedMenus: {}, // Track which menus have their dropdowns open
            currentMenuId: null, // Track current active menu ID
            draggedItemId: null, // Track which item is being dragged
            dragOverItemId: null, // Track which item is being dragged over
        });
        
        if (this.companyService.currentCompany.has_appsbar_image) {
            this.sidebarImageUrl = url('/web/image', {
                model: 'res.company',
                field: 'appbar_image',
                id: this.companyService.currentCompany.id,
            });
        }
        
        const renderAfterMenuChange = () => {
            const currentApp = this.appMenuService.getCurrentApp();
            if (!currentApp) {
                return;
            }

            // Update Website / non‑Website body class
            this._updateWebsiteActiveClass(currentApp);

            const appChanged =
                !this.state.selectedApp ||
                this.state.selectedApp.id !== currentApp.id;

            if (appChanged) {
                // Get default children from menu tree
                const children = this._getChildrenMenus(currentApp).filter(m => m && m.id);

                if (children.length) {
                    // First set selectedApp so _loadMenuOrder can use it if needed
                    this.state.selectedApp = currentApp;

                    // Try to load saved order from localStorage
                    const savedOrder = this._loadMenuOrder(currentApp.id);

                    // Use saved order if available, otherwise default children order
                    this.state.childrenMenus = savedOrder || children;

                    this.state.expandedMenus = {};
                    this.state.currentView = 'children';
                } else {
                    // No children: fallback to apps view
                    this.state.currentView = 'apps';
                    this.state.selectedApp = null;
                    this.state.childrenMenus = [];
                    this.state.expandedMenus = {};
                }
            }

            this.state.currentMenuId = currentApp.id;
        };
            
        this.env.bus.addEventListener(
            'MENUS:APP-CHANGED', renderAfterMenuChange
        );
        
        onWillStart(() => {
            // Check on initial load
            const currentApp = this.appMenuService.getCurrentApp();
            if (currentApp) {
                this._updateWebsiteActiveClass(currentApp);
            }
        });
        
        onMounted(() => {
            // Check after mount
            const currentApp = this.appMenuService.getCurrentApp();
            if (currentApp) {
                this._updateWebsiteActiveClass(currentApp);
            }
        });
        
        onWillUnmount(() => {
            this.env.bus.removeEventListener(
                'MENUS:APP-CHANGED', renderAfterMenuChange
            );
            // Clean up body class
            document.body.classList.remove('mk_apps_website_active');
        });
    }
    
    _updateWebsiteActiveClass(app) {
        if (!app) {
            document.body.classList.remove('mk_apps_website_active');
            return;
        }

        const xmlid = app.xmlid || '';
        const label = (app.label || app.name || '').toLowerCase();

        const isWebsite =
            xmlid.includes('website') ||
            label.includes('website');

        if (isWebsite) {
            document.body.classList.add('mk_apps_website_active');
        } else {
            document.body.classList.remove('mk_apps_website_active');
        }
    }
    
    // Helper to get children from menu using multiple possible properties
    _getMenuChildren(menu) {
        if (!menu) return [];
        
        // Try different property names that Odoo might use
        if (menu.childrenTree && menu.childrenTree.length > 0) {
            return menu.childrenTree;
        }
        if (menu.children && menu.children.length > 0) {
            return menu.children;
        }
        if (menu.childMenu && menu.childMenu.length > 0) {
            return menu.childMenu;
        }
        if (menu.subMenus && menu.subMenus.length > 0) {
            return menu.subMenus;
        }
        
        // Try to get children from menu service directly
        try {
            const menuTree = this.menuService.getMenuAsTree(menu.id);
            if (menuTree && menuTree.childrenTree && menuTree.childrenTree.length > 0) {
                return menuTree.childrenTree;
            }
            if (menuTree && menuTree.children && menuTree.children.length > 0) {
                return menuTree.children;
            }
        } catch (e) {
            // Ignore errors
        }
        
        return [];
    }
        
    _onAppClick(app) {
        // Update website class
        this._updateWebsiteActiveClass(app);
        
        // Get the children of this app
        const children = this._getChildrenMenus(app);
        
        if (children && children.length > 0) {
            // Switch to children view
            this.state.currentView = 'children';
            this.state.selectedApp = app;
            
            // Load saved order from localStorage or use default
            const savedOrder = this._loadMenuOrder(app.id);
            this.state.childrenMenus = savedOrder || children;
            this.state.expandedMenus = {};
        }
        
        // Update current menu ID
        this.state.currentMenuId = app.id;
        
        // Always select the app
        return this.appMenuService.selectApp(app);
    }
    
    _onChildClick(child, event) {
        // If you don't want to treat technical menus differently, just remove this:
        // if (this._isTechnicalMenu(child)) {
        //     return;
        // }

        if (this._hasChildren(child)) {
            const wasExpanded = this.state.expandedMenus[child.id];

            this.state.childrenMenus.forEach(c => {
                if (c.id !== child.id) {
                    this.state.expandedMenus[c.id] = false;
                    this._closeAllGrandchildren(c);
                }
            });

            this.state.expandedMenus[child.id] = !wasExpanded;
            event.preventDefault();
            return;
        }

        this.state.currentMenuId = child.id;
        this.menuService.selectMenu(child);
    }
    
    _onGrandchildClick(grandchild, event) {
        // If this grandchild has children (great-grandchildren), toggle the dropdown
        if (this._hasChildren(grandchild)) {
            // Close all other grandchild menus at the same level (accordion behavior)
            const wasExpanded = this.state.expandedMenus[grandchild.id];
            
            // Find the parent child to get siblings
            const parentChild = this.state.childrenMenus.find(child => {
                const children = this._getMenuChildren(child);
                return children.some(gc => gc.id === grandchild.id);
            });
            
            if (parentChild) {
                const siblings = this._getMenuChildren(parentChild);
                siblings.forEach(gc => {
                    if (gc.id !== grandchild.id) {
                        this.state.expandedMenus[gc.id] = false;
                    }
                });
            }
            
            // Toggle the clicked grandchild
            this.state.expandedMenus[grandchild.id] = !wasExpanded;
            
            // Don't navigate and don't set currentMenuId if it has children - just toggle
            if (event) {
                event.preventDefault();
            }
            return false;
        }
        
        // Only set currentMenuId and navigate if it doesn't have children
        this.state.currentMenuId = grandchild.id;
        this.menuService.selectMenu(grandchild);
    }
    
    _onGreatGrandchildClick(greatGrandchild) {
        // Update current menu ID and navigate
        this.state.currentMenuId = greatGrandchild.id;
        this.menuService.selectMenu(greatGrandchild);
    }
    
    _onBackToApps() {
        this.state.currentView = 'apps';
        this.state.selectedApp = null;
        this.state.childrenMenus = [];
        this.state.expandedMenus = {};
    }
    
    // Drag and Drop handlers
    _onDragStart(event, item) {
        this.state.draggedItemId = item.id;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/html', event.target);
        event.target.style.opacity = '0.4';
    }
    
    _onDragEnd(event) {
        event.target.style.opacity = '1';
        this.state.draggedItemId = null;
        this.state.dragOverItemId = null;
        
        // Remove all drag-over classes
        document.querySelectorAll('.mk_apps_drag_over').forEach(el => {
            el.classList.remove('mk_apps_drag_over');
        });
    }
    
    _onDragOver(event, item) {
        if (event.preventDefault) {
            event.preventDefault();
        }
        
        event.dataTransfer.dropEffect = 'move';
        
        const target = event.currentTarget;
        if (!target.classList.contains('mk_apps_drag_over')) {
            target.classList.add('mk_apps_drag_over');
        }
        
        this.state.dragOverItemId = item.id;
        
        return false;
    }
    
    _onDragLeave(event) {
        event.currentTarget.classList.remove('mk_apps_drag_over');
    }
    
    _onDrop(event, targetItem) {
        if (event.stopPropagation) {
            event.stopPropagation();
        }
        
        event.currentTarget.classList.remove('mk_apps_drag_over');
        
        const draggedItemId = this.state.draggedItemId;
        
        if (draggedItemId !== targetItem.id) {
            // Find indexes
            const draggedIndex = this.state.childrenMenus.findIndex(m => m.id === draggedItemId);
            const targetIndex = this.state.childrenMenus.findIndex(m => m.id === targetItem.id);
            
            if (draggedIndex !== -1 && targetIndex !== -1) {
                // Create new array with reordered items
                const newMenus = [...this.state.childrenMenus];
                const [draggedItem] = newMenus.splice(draggedIndex, 1);
                newMenus.splice(targetIndex, 0, draggedItem);
                
                // Update state
                this.state.childrenMenus = newMenus;
                
                // Save order to localStorage
                this._saveMenuOrder(this.state.selectedApp.id, newMenus);
            }
        }
        
        return false;
    }

    _isTechnicalMenu(menu) {
        if (!menu) {
            return true;
        }
        // Only treat true technical/debug menus as special
        return (
            menu.isDebug ||
            menu.isTechnical ||
            menu.xmlid?.includes('debug')
        );
    }
    // Save and load menu order from localStorage
    _saveMenuOrder(appId, menus) {
        const orderKey = `appsbar_menu_order_${appId}`;
        const order = menus.map(m => m.id);
        localStorage.setItem(orderKey, JSON.stringify(order));
    }
    
    _loadMenuOrder(appId) {
        const orderKey = `appsbar_menu_order_${appId}`;
        const savedOrder = localStorage.getItem(orderKey);
        
        if (!savedOrder) {
            return null;
        }
        
        try {
            const order = JSON.parse(savedOrder);
            const children = this._getChildrenMenus(this.state.selectedApp || this.appMenuService.getAppsMenuItems().find(a => a.id === appId));
            
            // Reorder children based on saved order
            const orderedMenus = [];
            order.forEach(id => {
                const menu = children.find(m => m.id === id);
                if (menu) {
                    orderedMenus.push(menu);
                }
            });
            
            // Add any new menus that weren't in the saved order
            children.forEach(menu => {
                if (!orderedMenus.find(m => m.id === menu.id)) {
                    orderedMenus.push(menu);
                }
            });
            
            return orderedMenus;
        } catch (e) {
            console.error('Error loading menu order:', e);
            return null;
        }
    }
    
    _closeAllGrandchildren(child) {
        // Helper method to close all grandchildren under a child
        const grandchildren = this._getMenuChildren(child);
        grandchildren.forEach(grandchild => {
            this.state.expandedMenus[grandchild.id] = false;
        });
    }
    
    _toggleChildDropdown(childId) {
        // This method is no longer needed as we toggle on click
        // Keeping it for backwards compatibility
        this.state.expandedMenus[childId] = !this.state.expandedMenus[childId];
    }
    
    _getChildrenMenus(app) {
        // Get the full menu tree
        const menuTree = this.menuService.getMenuAsTree('root');
        
        // Find the app in the menu tree
        const appMenu = menuTree.childrenTree.find(menu => menu.id === app.id);
        
        if (appMenu) {
            return this._getMenuChildren(appMenu);
        }
        
        return [];
    }
    
    _getGrandchildrenMenus(child) {
        return this._getMenuChildren(child);
    }
    
    _getGreatGrandchildrenMenus(grandchild) {
        return this._getMenuChildren(grandchild);
    }
    
    _isMenuActive(menu) {
        // Check if this menu is the currently active one
        return this.state.currentMenuId === menu.id;
    }
    
    _hasChildren(menu) {
        const children = this._getMenuChildren(menu);
        return children.length > 0;
    }
}