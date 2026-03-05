/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";

export class ThemeToggle extends Component {
    static template = "muk_web_appsbar.ThemeToggle";

    setup() {
        const currentScheme = cookie.get("color_scheme") || "light";

        this.state = useState({
            isDark: currentScheme === "dark",
        });

        // On mount: apply the data-bs-theme attribute so SCSS selectors work.
        // Odoo already served the correct CSS bundle based on the cookie —
        // we just need to sync the DOM attribute to match.
        this._applyDomTheme(currentScheme);
    }

    toggleTheme() {
        this.state.isDark = !this.state.isDark;
        const scheme = this.state.isDark ? "dark" : "light";

        // 1. Save preference BEFORE reload so Odoo's server reads it
        //    and serves the correct CSS bundle (web.assets_web_dark etc.)
        cookie.set("color_scheme", scheme, {
            path: "/",
            expires: 365 * 24 * 60 * 60, // seconds — 1 year
        });

        // 2. Let Odoo's server do all the heavy lifting.
        //    A clean reload is the ONLY safe way to swap Odoo's compiled
        //    SCSS bundles. Never disable/swap <link> tags manually —
        //    it breaks Odoo's asset pipeline and causes the layout to collapse.
        window.location.reload();
    }

    /**
     * Sync data-bs-theme on <html> and .o_dark on <body>.
     * Called on mount only — after a reload Odoo has served the right bundle,
     * and we just need the DOM attribute so SCSS selectors fire correctly.
     */
    _applyDomTheme(scheme) {
        document.documentElement.setAttribute("data-bs-theme", scheme);
        document.body.classList.toggle("o_dark", scheme === "dark");
    }
}

registry.category("systray").add("muk_web_appsbar.ThemeToggle", {
    Component: ThemeToggle,
    sequence: 100,
});