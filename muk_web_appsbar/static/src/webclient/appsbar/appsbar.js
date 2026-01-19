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
        
        this.state = useState({
            currentView: 'apps',
            selectedApp: null,
            flattenedMenus: [],
            currentMenuId: null,
            draggedItemId: null,
            dragOverItemId: null,
        });
        
        if (this.companyService.currentCompany.id) {
            this.sidebarImageUrl = url('/web/image', {
                model: 'res.company',
                field: 'logo',
                id: this.companyService.currentCompany.id,
            });
        }
                
        const renderAfterMenuChange = () => {
            const currentApp = this.appMenuService.getCurrentApp();
            if (!currentApp) {
                return;
            }

            this._updateWebsiteActiveClass(currentApp);

            const appChanged =
                !this.state.selectedApp ||
                this.state.selectedApp.id !== currentApp.id;

            if (appChanged) {
                this.state.selectedApp = currentApp;
                
                const flattenedMenus = this._getFlattenedActionableMenus(currentApp);
                
                if (flattenedMenus.length) {
                    const savedOrder = this._loadMenuOrder(currentApp.id);
                    this.state.flattenedMenus = savedOrder || flattenedMenus;
                    this.state.currentView = 'children';
                } else {
                    this.state.currentView = 'apps';
                    this.state.selectedApp = null;
                    this.state.flattenedMenus = [];
                }
            }

            this.state.currentMenuId = currentApp.id;
        };
            
        this.env.bus.addEventListener(
            'MENUS:APP-CHANGED', renderAfterMenuChange
        );
        
        onWillStart(() => {
            const currentApp = this.appMenuService.getCurrentApp();
            if (currentApp) {
                this._updateWebsiteActiveClass(currentApp);
            }
        });
        
        onMounted(() => {
            const currentApp = this.appMenuService.getCurrentApp();
            if (currentApp) {
                this._updateWebsiteActiveClass(currentApp);
            }
            
            // Inject logo into navbar
            this._injectNavbarLogo();
        });
        
        onWillUnmount(() => {
            this.env.bus.removeEventListener(
                'MENUS:APP-CHANGED', renderAfterMenuChange
            );
            document.body.classList.remove('mk_apps_website_active');
            
            // Remove injected logo
            this._removeNavbarLogo();
        });
    }
    
    // Inject company logo into the navbar
    _injectNavbarLogo() {
        if (!this.sidebarImageUrl) return;
        
        // Check if logo already exists
        if (document.querySelector('.mk_navbar_logo_container')) return;
        
        const navbar = document.querySelector('.o_main_navbar');
        if (!navbar) return;
        
        // Create logo container
        const logoContainer = document.createElement('div');
        logoContainer.className = 'mk_navbar_logo_container';
        
        const logoImg = document.createElement('img');
        logoImg.src = this.sidebarImageUrl;
        logoImg.alt = 'Company Logo';
        logoImg.className = 'mk_navbar_logo';
        
        logoContainer.appendChild(logoImg);
        
        // Insert at the beginning of navbar
        navbar.insertBefore(logoContainer, navbar.firstChild);
    }
    
    // Remove logo from navbar
    _removeNavbarLogo() {
        const logoContainer = document.querySelector('.mk_navbar_logo_container');
        if (logoContainer) {
            logoContainer.remove();
        }
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
    
    _getMenuChildren(menu) {
        if (!menu) return [];
        
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
        
        try {
            const menuTree = this.menuService.getMenuAsTree(menu.id);
            if (menuTree && menuTree.childrenTree && menuTree.childrenTree.length > 0) {
                return menuTree.childrenTree;
            }
            if (menuTree && menuTree.children && menuTree.children.length > 0) {
                return menuTree.children;
            }
        } catch (e) {}
        
        return [];
    }
    
    _menuHasAction(menu) {
        if (!menu) return false;
        if (menu.action) return true;
        if (menu.actionID) return true;
        if (menu.actionId) return true;
        if (menu.href && menu.href !== '#' && menu.href !== '') {
            return true;
        }
        return false;
    }
    
    _getFlattenedActionableMenus(app) {
        const menuTree = this.menuService.getMenuAsTree('root');
        const appMenu = menuTree.childrenTree.find(menu => menu.id === app.id);
        
        if (!appMenu) return [];
        
        const result = [];
        
        const processMenu = (menu, depth = 0, groupPath = []) => {
            const children = this._getMenuChildren(menu);
            const hasChildren = children.length > 0;
            const hasAction = this._menuHasAction(menu);
            
            if (hasChildren) {
                const newGroupPath = [...groupPath, menu.name];
                children.forEach(child => processMenu(child, depth, newGroupPath));
            } else if (hasAction) {
                result.push({
                    ...menu,
                    displayDepth: depth,
                    groupPath: [...groupPath],
                    groupName: groupPath.join(' / '),
                    isGroupHeader: false,
                });
            }
        };
        
        const appChildren = this._getMenuChildren(appMenu);
        appChildren.forEach(child => processMenu(child, 0, []));
        
        return result;
    }
    
    _getMenusWithGroups() {
        const menus = this.state.flattenedMenus;
        const result = [];
        let currentGroup = '';
        let groupCounter = 0; // ← ADD THIS COUNTER
        
        menus.forEach(menu => {
            const groupName = menu.groupName || '';
            
            if (groupName !== currentGroup) {
                if (groupName) {
                    result.push({
                        isGroupHeader: true,
                        groupName: groupName,
                        id: `group_${groupCounter++}`, // ← USE COUNTER FOR UNIQUE IDs
                    });
                }
                currentGroup = groupName;
            }
            
            result.push(menu);
        });
        
        return result;
    }
        
    _onAppClick(app) {
        this._updateWebsiteActiveClass(app);
        
        const flattenedMenus = this._getFlattenedActionableMenus(app);
        
        if (flattenedMenus && flattenedMenus.length > 0) {
            this.state.currentView = 'children';
            this.state.selectedApp = app;
            
            const savedOrder = this._loadMenuOrder(app.id);
            this.state.flattenedMenus = savedOrder || flattenedMenus;
        }
        
        this.state.currentMenuId = app.id;
        return this.appMenuService.selectApp(app);
    }
    
    _onMenuClick(menu, event) {
        if (menu.isGroupHeader) {
            event.preventDefault();
            return;
        }
        
        this.state.currentMenuId = menu.id;
        this.menuService.selectMenu(menu);
    }
    
    _onBackToApps() {
        this.state.currentView = 'apps';
        this.state.selectedApp = null;
        this.state.flattenedMenus = [];
    }
    
    _onDragStart(event, item) {
        if (item.isGroupHeader) {
            event.preventDefault();
            return;
        }
        this.state.draggedItemId = item.id;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/html', event.target);
        event.target.style.opacity = '0.4';
    }
    
    _onDragEnd(event) {
        event.target.style.opacity = '1';
        this.state.draggedItemId = null;
        this.state.dragOverItemId = null;
        
        document.querySelectorAll('.mk_apps_drag_over').forEach(el => {
            el.classList.remove('mk_apps_drag_over');
        });
    }
    
    _onDragOver(event, item) {
        if (item.isGroupHeader) return false;
        
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
        if (targetItem.isGroupHeader) return false;
        
        if (event.stopPropagation) {
            event.stopPropagation();
        }
        
        event.currentTarget.classList.remove('mk_apps_drag_over');
        
        const draggedItemId = this.state.draggedItemId;
        
        if (draggedItemId !== targetItem.id) {
            const draggedIndex = this.state.flattenedMenus.findIndex(m => m.id === draggedItemId);
            const targetIndex = this.state.flattenedMenus.findIndex(m => m.id === targetItem.id);
            
            if (draggedIndex !== -1 && targetIndex !== -1) {
                const newMenus = [...this.state.flattenedMenus];
                const [draggedItem] = newMenus.splice(draggedIndex, 1);
                newMenus.splice(targetIndex, 0, draggedItem);
                
                this.state.flattenedMenus = newMenus;
                this._saveMenuOrder(this.state.selectedApp.id, newMenus);
            }
        }
        
        return false;
    }

    _saveMenuOrder(appId, menus) {
        const orderKey = `appsbar_menu_order_${appId}`;
        const order = menus.filter(m => !m.isGroupHeader).map(m => m.id);
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
            const currentMenus = this._getFlattenedActionableMenus(
                this.state.selectedApp || 
                this.appMenuService.getAppsMenuItems().find(a => a.id === appId)
            );
            
            const orderedMenus = [];
            order.forEach(id => {
                const menu = currentMenus.find(m => m.id === id);
                if (menu) {
                    orderedMenus.push(menu);
                }
            });
            
            currentMenus.forEach(menu => {
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
    
    _isMenuActive(menu) {
        return this.state.currentMenuId === menu.id;
    }
}